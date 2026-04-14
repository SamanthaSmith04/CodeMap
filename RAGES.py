import os
import json
import asyncio
import uuid
import shutil
import tempfile

from elasticsearch import AsyncElasticsearch, Elasticsearch
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.ingestion import IngestionPipeline
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from github_api_calls import set_up_github_connection, get_repo_contents, get_commit_history, get_issue_history
from flask import Flask, request, jsonify
import requests

from flask_cors import CORS


app = Flask(__name__)
CORS(app)

ACTIVE_SESSIONS = {}

@app.after_request
async def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
  return response

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
        repo_path = os.path.join("/tmp/CodeMap", temp_dir['sessionId'])
        os.makedirs(repo_path, exist_ok=True)
        # repo_path = os.path.join(os.getcwd(), "temp_repos/"+temp_dir['sessionId'])
        # os.makedirs(repo_path, exist_ok=True)
        print(f"Repository downloaded successfully to {repo_path}")
        headers, url = set_up_github_connection(owner, repo)
        get_repo_contents(headers, url, save_path=repo_path) 
        get_commit_history(headers, url, save_path=repo_path)
        get_issue_history(headers, url, save_path=repo_path)

        return repo_path
        
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
    
async def apply_file_to_prompt(async_es_client, index_name, selected_template, current_prompt, file_index=None):
    selected_file = None

    if selected_template["id"] in ["C1", "C2", "C3", "D2"]:
        files = await get_indexed_files(async_es_client, index_name)
        if not files:
            raise RuntimeError("No files found in index.")

        if file_index is None:
            raise ValueError("This template requires a file selection.")
        if file_index < 0 or file_index >= len(files):
            raise ValueError("Selected file is out of range.")

        chosen = files[file_index]
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
    # 4. Ingestion
    pipeline = IngestionPipeline(
        transformations=[Settings.node_parser, Settings.embed_model],
        vector_store = ElasticsearchStore(
            index_name=index_name,
            es_client=async_es_client
        ),
    )
    await pipeline.arun(documents=documents, show_progress=True)

    await async_es_client.close()

def build_session_resources(index_name: str):
    async_es_client = AsyncElasticsearch(ES_URL)
    vector_store = ElasticsearchStore(
        index_name=index_name,
        es_client=async_es_client,
    )
    return vector_store, async_es_client

async def run_query(vector_store, async_es_client, user_prompt: str):
    index = VectorStoreIndex.from_vector_store(vector_store)
    query_engine = index.as_query_engine()

    print("\n--- Generating Response via Ollama ---")
    response = await query_engine.aquery(user_prompt)
    return response

async def query_session(session: dict, template_key: str, file_index: int | None = None) -> dict:
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
    current_prompt = selected["prompt"]

    vector_store, async_es_client = build_session_resources(session["index_name"])

    try:
        current_prompt, selected_file = await apply_file_to_prompt(
            async_es_client,
            session["index_name"],
            selected,
            current_prompt,
            file_index=file_index,
        )

        answer = await run_query(vector_store, async_es_client, current_prompt)

        return {
            "description": selected["description"],
            "answer": str(answer),
            "selected_file": selected_file,
        }
    finally:
        await async_es_client.close()

@app.route('/api/query_session', methods=['POST'])
async def handle_query_session():
    # 1. Get the JSON data from the request
    data = request.get_json()
    
    # 2. Extract parameters (ensure they exist or provide defaults)
    session_id = data.get("session_id")
    template_key = data.get("template_key")
    file_index = data.get("file_index") # Can be None

    if not session_id or not template_key:
        return jsonify({"error": "Missing session_id or template_key"}), 400

    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found. Please reload the repository."}), 404

    try:
        result = await query_session(
            session=session,
            template_key=template_key, 
            file_index=file_index
        )
        
        # 4. Return the dictionary as JSON
        return jsonify(result), 200

    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/api/download_github_repo', methods=['POST'])
def handle_download_github_repo():
    data = request.get_json(force=True)

    repo_owner = data.get("repo_owner")
    repo_name = data.get("repo_name")
    temp_dir = data.get("temp_dir")

    if not repo_owner:
        return jsonify({"error": "Missing repo owner"})
    if not repo_name:
        return jsonify({"error": "Missing repo name"})
    if not temp_dir:
        return jsonify({"error": "Missing save location"})

    try:
        result = download_github_repo(repo_owner, repo_name, temp_dir)
        session_id = temp_dir["sessionId"]
        index_name = f"{INDEX_PREFIX}_{session_id}"
        asyncio.run(set_up_pipeline(result, index_name))

        ACTIVE_SESSIONS[session_id] = {
            "repo_path": result,
            "index_name": index_name,
        }

        return jsonify({"path": result, "session_id": session_id}), 200
    
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/api/session_files', methods=['POST'])
async def handle_session_files():
    data = request.get_json()
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found. Please reload the repository."}), 404

    try:
        _, async_es_client = build_session_resources(session["index_name"])
        try:
            files = await get_indexed_files(async_es_client, session["index_name"])
            return jsonify({"files": files}), 200
        finally:
            await async_es_client.close()
    except Exception:
        return jsonify({"error": "Unable to fetch indexed files"}), 500


@app.route('/api/repo_exists', methods=['POST'])
async def check_repo_exists():
    data = request.get_json()
    
    repo_url = data.get("url")
    if not repo_url:
        return jsonify({"error": "Missing repo URL"}), 400

    # try:
    repo_names = "/".join(repo_url.rstrip(".git").split("/")[-2:])
    github_url = f"https://api.github.com/repos/{repo_names}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = requests.get(github_url, headers=headers)

    if response.status_code == 200:
        return jsonify({"exists": True}), 200
    elif response.status_code == 404:
        return jsonify({"exists": False}), 404
    else:
        return jsonify({"error": response.json().get("message", "Unknown error")}), 501

    # except Exception as e:
    #     return jsonify({"error": "An unexpected error occurred"}), 500

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
    # try:  
    app.run(debug=True, port=5000, use_reloader=False) 
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #     loop.run_until_complete(main())
    # except KeyboardInterrupt:
    #     print("\nStopped by user.")
    # finally:
    #     loop.close()
