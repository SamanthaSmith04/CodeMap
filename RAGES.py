import os
import json
import asyncio
from elasticsearch import AsyncElasticsearch, Elasticsearch
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext
from llama_index.core.ingestion import IngestionPipeline
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

ES_URL = "http://127.0.0.1:9201"
INDEX_NAME = "github_rag_index"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
PROMPTS_FILE = "CodeMap-prompts/prompt_templates.json"

Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
Settings.llm = Ollama(model="llama3.1", request_timeout=120.0)
Settings.chunk_size = 512
Settings.chunk_overlap = 50

def setup_fresh_index():
    """Wipes the existing index and creates a clean one at the start of every run."""
    sync_es = Elasticsearch(ES_URL)
    
    if sync_es.indices.exists(index=INDEX_NAME):
        print(f"Cleaning up old index: {INDEX_NAME}...")
        sync_es.indices.delete(index=INDEX_NAME)
    
    print(f"Creating fresh index: {INDEX_NAME}...")
    sync_es.indices.create(
        index=INDEX_NAME,
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

def load_prompt_templates():
    if not os.path.exists(PROMPTS_FILE):
        print(f"Error: '{PROMPTS_FILE}' not found.")
        return None
    with open(PROMPTS_FILE, "r") as f:
        return json.load(f)

async def run_pipeline(repo_path: str, user_prompt: str):
    # 1. Start Fresh
    setup_fresh_index()

    # 2. Load Repository
    print(f"\n--- Loading Repository: {repo_path} ---")
    reader = SimpleDirectoryReader(
        input_dir=repo_path, 
        recursive=True,
        required_exts=[".py", ".md", ".txt", ".js", ".json", ".ts", ".go"] 
    )
    documents = reader.load_data()
    print(f"Loaded {len(documents)} documents.")

    # 3. Setup Vector Store
    async_es_client = AsyncElasticsearch(ES_URL)
    vector_store = ElasticsearchStore(index_name=INDEX_NAME, es_client=async_es_client)

    # 4. Ingestion
    print("Embedding and indexing...")
    pipeline = IngestionPipeline(
        transformations=[Settings.node_parser, Settings.embed_model],
        vector_store=vector_store,
    )
    await pipeline.arun(documents=documents, show_progress=True)
    
    # 5. Query
    index = VectorStoreIndex.from_vector_store(vector_store)
    query_engine = index.as_query_engine()
    
    print("\n--- Generating Response via Ollama ---")
    response = await query_engine.aquery(user_prompt)
    
    await async_es_client.close()
    return response

async def main():
    repo_path = input("Enter the path to the code repository: ").strip()
    if not os.path.exists(repo_path):
        print(f"Error: Path '{repo_path}' not found.")
        return

    templates = load_prompt_templates()
    if not templates: return

    print("\n--- Available Analysis Templates ---")
    template_keys = list(templates.keys())
    for idx, key in enumerate(template_keys, 1):
        print(f"[{idx}] {templates[key]['description']}")

    try:
        choice = int(input("\nSelect a template number: "))
        if 1 <= choice <= len(template_keys):
            selected_config = templates[template_keys[choice - 1]]
            print(f"\nRunning: {selected_config['description']}")
            
            answer = await run_pipeline(repo_path, selected_config['prompt'])
            
            print("\n" + "="*60)
            print(f"FINAL OUTPUT: {selected_config['description']}")
            print("="*60)
            print(answer)
            print("="*60 + "\n")
        else:
            print("Invalid choice.")
    except ValueError:
        print("Invalid input.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.stop()
        print("Done.")