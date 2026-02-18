import os
import asyncio
from elasticsearch import AsyncElasticsearch, Elasticsearch
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext
from llama_index.core.ingestion import IngestionPipeline
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from github_api_calls import set_up_github_connection, get_repo_contents

# --- CONFIGURATION ---
ES_URL = "http://127.0.0.1:9201"
INDEX_NAME = "github_rag_index"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Initialize Settings
Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
Settings.llm = Ollama(model="llama3.1", request_timeout=120.0)
Settings.chunk_size = 512
Settings.chunk_overlap = 50

def download_github_repo(owner: str, repo: str) -> str:
    """
    Download a GitHub repository and save files locally using GitHub API calls.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        
    Returns:
        Path to the local directory containing downloaded files
    """
    print(f"Downloading GitHub repository: {owner}/{repo}")
    
    try:
        # Set up GitHub connection
        headers, url = set_up_github_connection(owner, repo)
        
        # Download repository contents
        get_repo_contents(headers, url)
        
        # Return the temp directory path where files are saved
        temp_dir = "temp_files"
        print(f"Repository downloaded to: {temp_dir}")
        return temp_dir
        
    except Exception as e:
        print(f"Error downloading repository: {e}")
        raise

def setup_index(delete_existing=False):
    sync_es = Elasticsearch(ES_URL)
    
    if delete_existing and sync_es.indices.exists(index=INDEX_NAME):
        print(f"Deleting existing index {INDEX_NAME} for a fresh start...")
        sync_es.indices.delete(index=INDEX_NAME)

    if not sync_es.indices.exists(index=INDEX_NAME):
        print(f"Creating index {INDEX_NAME}...")
        sync_es.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "embedding": {"type": "dense_vector", "dims": 384, "index": True, "similarity": "cosine"}
                    }
                }
            }
        )

async def run_pipeline(repo_path: str, user_query: str):
    setup_index()

    # 1. LOAD ONLY RELEVANT FILES (Avoids the 'garbled text' issue)
    print(f"--- Loading Repository: {repo_path} ---")
    reader = SimpleDirectoryReader(
        input_dir=repo_path, 
        recursive=True,
        required_exts=[".py", ".md", ".txt", ".js", ".json"] # Only read these
    )
    documents = reader.load_data()
    print(f"Loaded {len(documents)} text-based documents.")

    # 2. ASYNC SETUP
    async_es_client = AsyncElasticsearch(ES_URL)
    vector_store = ElasticsearchStore(index_name=INDEX_NAME, es_client=async_es_client)

    # 3. INDEXING
    print("Embedding and indexing...")
    pipeline = IngestionPipeline(
        transformations=[Settings.node_parser, Settings.embed_model],
        vector_store=vector_store,
    )
    await pipeline.arun(documents=documents, show_progress=True)
    
    # 4. QUERY
    index = VectorStoreIndex.from_vector_store(vector_store)
    print(f"\n--- Running Query: {user_query} ---")
    query_engine = index.as_query_engine()
    response = await query_engine.aquery(user_query)
    
    await async_es_client.close()
    return response

async def main():
    print("\n=== RAGES - Elasticsearch RAG System ===")
    print("1. Index a local directory")
    print("2. Download and index a GitHub repository")
    
    choice = input("\nSelect source type (1-2): ").strip()
    
    if choice == "1":
        # Local directory
        repo_path = input("Enter path to local directory: ").strip()
        if not os.path.exists(repo_path):
            print(f"✗ Directory not found: {repo_path}")
            return
    elif choice == "2":
        # GitHub repository
        owner = input("Enter GitHub repository owner: ").strip()
        repo = input("Enter GitHub repository name: ").strip()
        
        try:
            repo_path = download_github_repo(owner, repo)
        except Exception as e:
            print(f"✗ Failed to download repository: {e}")
            return
    else:
        print("✗ Invalid choice.")
        return
    
    # Get user query
    query = input("Enter your query (default: 'Summarize the purpose of these files and their contents.'): ").strip()
    if not query:
        query = "Summarize the purpose of these files and their contents."
    
    # Run the pipeline
    try:
        answer = await run_pipeline(repo_path, query)
        print("\n--- RAG ANSWER ---")
        print(answer)
    except Exception as e:
        print(f"✗ Error running pipeline: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # This catches the Python 3.14 specific shutdown noise if it persists
        pass