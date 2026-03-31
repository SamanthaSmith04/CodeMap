import os
import json
import asyncio
import uuid
import shutil
from elasticsearch import AsyncElasticsearch, Elasticsearch
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext
from llama_index.core.ingestion import IngestionPipeline
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from github_api_calls import set_up_github_connection, get_repo_contents, get_commit_history, get_issue_history

ES_URL = "http://127.0.0.1:9201"
INDEX_PREFIX = "github_rag_index"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
PROMPTS_FILE = "CodeMap-prompts/prompt_templates.json"

Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
Settings.llm = Ollama(model="llama3.1", request_timeout=360.0)
Settings.chunk_size = 512
Settings.chunk_overlap = 50

def download_github_repo(owner: str, repo: str, temp_dir: str) -> str:
    print(f"Downloading GitHub repository: {owner}/{repo} into {temp_dir}")
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        headers, url = set_up_github_connection(owner, repo)
        get_repo_contents(headers, url, save_path=temp_dir) 
        get_commit_history(headers, url, save_path=temp_dir)
        get_issue_history(headers, url, save_path=temp_dir)
        return temp_dir
        
    except Exception as e:
        print(f"Error downloading repository: {e}")
        raise

def setup_fresh_index(index_name: str):
    sync_es = Elasticsearch(ES_URL)
    
    if sync_es.indices.exists(index=index_name):
        print(f"Cleaning up old index: {index_name}...")
        sync_es.indices.delete(index=index_name)
    
    print(f"Creating fresh index: {index_name}...")
    sync_es.indices.create(
        index=index_name,
        body={
            "mappings": {
                # This template ensures metadata strings are aggregatable
                "dynamic_templates": [
                    {
                        "metadata_as_keywords": {
                            "path_match": "metadata.*",
                            "match_mapping_type": "string",
                            "mapping": {"type": "keyword"}
                        }
                    }
                ],
                "properties": {
                    "embedding": {
                        "type": "dense_vector", 
                        "dims": 384, 
                        "index": True, 
                        "similarity": "cosine"
                    }
                }
            }
        }
    )

def index_exists(index_name: str) -> bool:
    sync_es = Elasticsearch(ES_URL)
    return sync_es.indices.exists(index=index_name)

async def get_indexed_files(async_es_client, index_name: str):
    query = {
        "size": 1000,
        "_source": ["metadata.file_name", "metadata.file_path"]
    }
    response = await async_es_client.search(index=index_name, body=query)

    seen = set()
    files = []
    for hit in response["hits"]["hits"]:
        md = hit["_source"].get("metadata", {})
        file_name = md.get("file_name")
        file_path = md.get("file_path")
        if file_name and file_path and file_path not in seen:
            seen.add(file_path)
            files.append({"value": file_name, "path": file_path})

    files.sort(key=lambda x: x["value"].lower())
    return files

def load_file_text(file_path: str, max_chars: int = 12000) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return text[:max_chars]
    except Exception as e:
        return f"[Could not read file: {e}]"
    
async def maybe_select_file(async_es_client, index_name, selected_template, current_prompt):
    selected_file = None

    if selected_template['id'] in ["C1", "C2", "C3", "D2"]:
        files = await get_indexed_files(async_es_client, index_name)

        if not files:
            print("No files found in index.")
            return None, None

        print("\n--- Files in Index ---")
        for f_idx, file_info in enumerate(files, 1):
            print(f"[{f_idx}] {file_info['value']}")

        f_choice = int(input("Select a file number: "))
        chosen = files[f_choice - 1]

        selected_file = chosen["value"]
        file_path = chosen["path"]

        file_text = load_file_text(file_path)

        current_prompt = f"""
            You are answering a question about this file.

            FILE: {selected_file}

            CONTENT:
            ```text
            {file_text}

            QUESTION:
            {current_prompt}
            """.strip()

        return current_prompt, selected_file

def load_prompt_templates():
    if not os.path.exists(PROMPTS_FILE):
        print(f"Error: '{PROMPTS_FILE}' not found.")
        return None
    with open(PROMPTS_FILE, "r") as f:
        return json.load(f)

async def set_up_pipeline(repo_path: str, index_name: str):
    # 1. Start Fresh with the unique index name
    setup_fresh_index(index_name)

    # 2. Load Repository
    reader = SimpleDirectoryReader(
        input_dir=repo_path, 
        recursive=True,
        required_exts=[".py", ".md", ".txt", ".js", ".json", ".ts", ".go", ".c", ".cpp", ".h", ".hpp", ".java"] 
    )
    documents = reader.load_data()

    # 3. Setup Vector Store with the unique index name
    async_es_client = AsyncElasticsearch(ES_URL)
    vector_store = ElasticsearchStore(
        index_name=index_name, 
        es_client=async_es_client,
    )

    # 4. Ingestion
    pipeline = IngestionPipeline(
        transformations=[Settings.node_parser, Settings.embed_model],
        vector_store = ElasticsearchStore(
            index_name=index_name,
            es_client=async_es_client
        ),
    )
    await pipeline.arun(documents=documents, show_progress=True)

    return vector_store, async_es_client

async def run_query(vector_store, async_es_client, user_prompt: str):
    index = VectorStoreIndex.from_vector_store(vector_store)
    query_engine = index.as_query_engine()

    print("\n--- Generating Response via Ollama ---")
    response = await query_engine.aquery(user_prompt)
    return response

async def query_session(session: dict, template_key: str) -> dict:
    """
    Runs a named template query against an active session.
    Returns a dict with 'description' and 'answer' for the frontend to display.
    Raises KeyError if the template key is not found.
    Raises RuntimeError if prompt templates cannot be loaded.
    """
    templates = load_prompt_templates()
    if not templates:
        raise RuntimeError(f"Could not load prompt templates from '{PROMPTS_FILE}'.")
    if template_key not in templates:
        raise KeyError(f"Template '{template_key}' not found. Available: {list(templates.keys())}")

    selected = templates[template_key]
    answer = await run_query(session["vector_store"], session["client"], selected["prompt"])

    return {
        "description": selected["description"],
        "answer": answer,
    }

async def main():
    # ... (Setup logic same as your original)
    print("\n=== RAGES - Elasticsearch RAG System ===")
    print("1. Index a local directory")
    print("2. Download & Index GitHub")
    print("3. Resume an existing session")
    choice = input("\nSelect (1-3): ").strip()
    
    session_id = uuid.uuid4().hex[:8] if choice != "3" else input("Session ID: ").strip()
    unique_index_name = f"{INDEX_PREFIX}_{session_id}"
    
    if choice == "3":
        async_es_client = AsyncElasticsearch(ES_URL)
        vector_store = ElasticsearchStore(index_name=unique_index_name, es_client=async_es_client)
    else:
        repo_path = input("Path: ") if choice == "1" else download_github_repo(input("Owner: "), input("Repo: "), os.path.join(os.getcwd(), f"repo_{session_id}"))
        vector_store, async_es_client = await set_up_pipeline(repo_path, unique_index_name)

    try:
        templates = json.load(open(PROMPTS_FILE))
        
        while True:
            print(f"\nSession: {session_id} \n| --- Templates ---")
            template_keys = list(templates.keys())
            for idx, key in enumerate(template_keys, 1):
                print(f"[{idx}] {templates[key]['description']}")

            user_input = input("\nSelect template (or 'exit'): ").strip()
            if user_input.lower() == 'exit': break
                
            try:
                selected = templates[template_keys[int(user_input) - 1]]
                current_prompt = selected["prompt"]

                current_prompt, selected_file = await maybe_select_file(
                    async_es_client,
                    unique_index_name,
                    selected,
                    current_prompt
                )

                if current_prompt is None:
                    continue

                answer = await run_query(vector_store, async_es_client, current_prompt)
                print(f"\n{'='*20} RESPONSE {'='*20}\n{answer}\n{'='*50}")

            except (ValueError, IndexError):
                print("Invalid selection.")

    finally:    
        await async_es_client.close() 
        print(f"Session {session_id} closed.")

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        loop.close()