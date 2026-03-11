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
    """
    Download a GitHub repository into a specific unique directory.
    """
    print(f"Downloading GitHub repository: {owner}/{repo} into {temp_dir}")
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        
        # Set up GitHub connection
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
    
    # Check if this specific session index already exists
    if sync_es.indices.exists(index=index_name):
        print(f"Cleaning up old index: {index_name}...")
        sync_es.indices.delete(index=index_name)
    
    print(f"Creating fresh index: {index_name}...")
    sync_es.indices.create(
        index=index_name,
        body={
            "mappings": {
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
    print(f"\n--- Loading Repository: {repo_path} ---")
    reader = SimpleDirectoryReader(
        input_dir=repo_path, 
        recursive=True,
        required_exts=[".py", ".md", ".txt", ".js", ".json", ".ts", ".go"] 
    )
    documents = reader.load_data()
    print(f"Loaded {len(documents)} documents.")

    # 3. Setup Vector Store with the unique index name
    async_es_client = AsyncElasticsearch(ES_URL)
    vector_store = ElasticsearchStore(
        index_name=index_name, 
        es_client=async_es_client
    )

    # 4. Ingestion
    print(f"Embedding and indexing into {index_name}...")
    pipeline = IngestionPipeline(
        transformations=[Settings.node_parser, Settings.embed_model],
        vector_store=vector_store,
    )
    await pipeline.arun(documents=documents, show_progress=True)

    return vector_store, async_es_client


async def run_query(vector_store, async_es_client, user_prompt: str):
    # 5. Query
    index = VectorStoreIndex.from_vector_store(vector_store)
    query_engine = index.as_query_engine()
    
    print("\n--- Generating Response via Ollama ---")
    response = await query_engine.aquery(user_prompt)
    
    await async_es_client.close()
    return response

async def main():
    print("\n=== RAGES - Elasticsearch RAG System ===")
    print("1. Index a local directory (New Session)")
    print("2. Download & Index GitHub (New Session)")
    print("3. Resume an existing session (Enter Session ID)")
    
    choice = input("\nSelect an option (1-3): ").strip()
    
    session_id = None
    repo_path = None
    is_resume = False

    if choice == "3":
        session_id = input("Enter your Session ID (e.g., a1b2c3d4): ").strip()
        unique_index_name = f"{INDEX_PREFIX}_{session_id}"
        
        if index_exists(unique_index_name):
            print(f"✔ Found existing index: {unique_index_name}. Resuming...")
            is_resume = True
            # Create the client and store directly
            async_es_client = AsyncElasticsearch(ES_URL)
            vector_store = ElasticsearchStore(index_name=unique_index_name, es_client=async_es_client)
        else:
            print(f"✗ Session ID '{session_id}' not found in Elasticsearch.")
            return
    else:
        session_id = uuid.uuid4().hex[:8]
        unique_index_name = f"{INDEX_PREFIX}_{session_id}"
        temp_repo_path = os.path.join(os.getcwd(), f"repo_{session_id}")

        if choice == "1":
            repo_path = input("Enter path to code repository: ").strip()
        elif choice == "2":
            owner = input("Enter GitHub owner: ").strip()
            repo = input("Enter GitHub repo: ").strip()
            repo_path = download_github_repo(owner, repo, temp_repo_path)
        else:
            print("Invalid choice.")
            return

    try:
        # Only run the pipeline if new session
        if not is_resume:
            vector_store, async_es_client = await set_up_pipeline(repo_path, unique_index_name)
        
        print(f"\n🚀 Session Active: {session_id}")
        
        templates = load_prompt_templates()
        if not templates: return

        # --- Query Loop ---
        while True:
            print("\n--- Available Analysis Templates (Type 'exit' to quit) ---")
            template_keys = list(templates.keys())
            for idx, key in enumerate(template_keys, 1):
                print(f"[{idx}] {templates[key]['description']}")

            user_input = input("\nSelect a template number: ").strip()
            if user_input.lower() == 'exit': break
                
            try:
                idx = int(user_input)
                if 1 <= idx <= len(template_keys):
                    selected = templates[template_keys[idx - 1]]
                    answer = await run_query(vector_store, async_es_client, selected['prompt'])
                    print(f"\n{'='*20} RESPONSE {'='*20}\n{answer}\n{'='*50}")
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Please enter a number.")

    finally:    
        print(f"Session {session_id} closed. You can resume this later using the ID.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        loop.stop()
        print("Done.")