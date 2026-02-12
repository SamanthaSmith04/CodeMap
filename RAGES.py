import os
import asyncio
import nest_asyncio
from elasticsearch import AsyncElasticsearch, Elasticsearch
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

# 1. Patch the event loop for macOS/Python 3.14 compatibility
nest_asyncio.apply()

# CONFIGURATION
ES_URL = "http://127.0.0.1:9201"
INDEX_NAME = "github_rag_index"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Global Settings
Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
Settings.llm = Ollama(model="llama3.1", request_timeout=120.0)
Settings.chunk_size = 512
Settings.chunk_overlap = 50

def create_index_if_missing():
    """Synchronous check to ensure index exists with correct 384-dim mapping."""
    # We use a sync client here just for the setup check
    sync_es = Elasticsearch(ES_URL)
    if not sync_es.indices.exists(index=INDEX_NAME):
        print(f"Index {INDEX_NAME} not found. Creating it...")
        sync_es.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 384, # Matches all-MiniLM-L6-v2
                            "index": True,
                            "similarity": "cosine"
                        }
                    }
                }
            }
        )
    else:
        print(f"Index {INDEX_NAME} already exists.")

def index_repository(repo_path: str):
    print(f"--- Indexing Repository: {repo_path} ---")
    create_index_if_missing()

    # Load documents from the test folder
    reader = SimpleDirectoryReader(input_dir=repo_path, recursive=True)
    documents = reader.load_data()
    print(f"Loaded {len(documents)} documents.")

    # USE ASYNC CLIENT to prevent 'HeadApiResponse' errors
    async_es_client = AsyncElasticsearch(ES_URL)
    
    vector_store = ElasticsearchStore(
        index_name=INDEX_NAME,
        es_client=async_es_client # This must be the async version
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # This call is sync but uses nest_asyncio to handle the async store internally
    index = VectorStoreIndex.from_documents(
        documents, 
        storage_context=storage_context,
        show_progress=True
    )
    print("Indexing complete.")
    return index

def run_query(query_text: str):
    """Retrieves context and generates an answer."""
    async_es_client = AsyncElasticsearch(ES_URL)
    vector_store = ElasticsearchStore(index_name=INDEX_NAME, es_client=async_es_client)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    
    query_engine = index.as_query_engine()
    response = query_engine.query(query_text)
    return response

if __name__ == "__main__":
    repo_to_index = "./test" 
    if os.path.exists(repo_to_index):
        # 1. Index the repo
        index_repository(repo_to_index)
        
        # 2. Run a test query
        user_query = "Summarize the files in this repository."
        answer = run_query(user_query)
        
        print("\n--- RAG ANSWER ---")
        print(answer)
    else:
        print(f"Error: Directory {repo_to_index} not found.")