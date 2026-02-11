from elasticsearch import Elasticsearch
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.llms import MockLLM
from llama_index.llms.ollama import Ollama

# CONFIG
ES_URL = "http://127.0.0.1:9201"          # your confirmed working port
INDEX_NAME = "github_rag_index"           # name for repo chunks

Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

es_client = Elasticsearch(ES_URL)
print("Connected to Elasticsearch:", es_client.info().get("name", "Unknown"))

vector_store = ElasticsearchStore(
    index_name=INDEX_NAME,
    es_client=es_client,
)

# Create vector index if it doesn't exist
if not es_client.indices.exists(index=INDEX_NAME):
    es_client.indices.create(
        index=INDEX_NAME,
        body={
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
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
    print(f"Created vector index: {INDEX_NAME}")
else:
    print(f"Index {INDEX_NAME} already exists")

# Test ingestion - assumes sample.txt is in the repo root
documents = SimpleDirectoryReader(input_files=["sample.txt"]).load_data()
index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)
print("Sample data indexed successfully.")

# Quick query test
llm = Ollama(model="llama3.1", request_timeout=120.0)  # or "mistral"
query_engine = index.as_query_engine(llm=llm)
response = query_engine.query("What is this test document about?")
print("Test query response:", response)