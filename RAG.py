#NOTE: This pipeline currently only asks for a summary
#run with python RAG.py <document_path>

import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import ollama

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 4


def load_document(path: str) -> str:
    """Load a plain-text document from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str):
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def embed_chunks(chunks, model):
    # Embedding method:
    # - SentenceTransformer (MiniLM)
    # - Mean pooling over token embeddings
    # - Output: 384-dimensional vectors
    # Produces a semantic vector space suitable for k-NN search.
    
    return model.encode(chunks, show_progress_bar=True)


def save_faiss(index, embeddings, chunks, path):
    # store locally
    os.makedirs(path, exist_ok=True)
    faiss.write_index(index, os.path.join(path, "index.faiss"))

    with open(os.path.join(path, "chunks.json"), "w") as f:
        json.dump(chunks, f)

def load_faiss(path):
    index = faiss.read_index(os.path.join(path, "index.faiss"))
    with open(os.path.join(path, "chunks.json"), "r") as f:
        chunks = json.load(f)
    return index, chunks


def build_or_load_vectorstore(doc_path):
    store_path = f"{doc_path}_faiss"

    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    if os.path.exists(os.path.join(store_path, "index.faiss")):
        print("Loading existing embeddings...")
        return load_faiss(store_path), embedder

    print("Embedding document for the first time...")
    text = load_document(doc_path)
    chunks = chunk_text(text)
    embeddings = embed_chunks(chunks, embedder)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))

    save_faiss(index, embeddings, chunks, store_path)
    return (index, chunks), embedder

def retrieve(query, index, chunks, embedder, k=TOP_K):

    # Retrieval method:
    # - Encode query into same embedding space
    # - Perform k-NN search with L2 distance
    # - Return original text chunks

    query_embedding = embedder.encode([query])
    distances, indices = index.search(query_embedding, k)
    return [chunks[i] for i in indices[0]]


def generate_answer(query, context_chunks):
    context = "\n\n".join(context_chunks)

    prompt = f"""
        You are a question-answering system.
        Use ONLY the context below to answer the question.
        If the answer is not present, say "I don't know."

        Context:
        {context}

        Question:
        {query}

        Answer:
        """

    response = ollama.chat(
        model="mistral",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]

def run_rag(doc_path, query):
    (index, chunks), embedder = build_or_load_vectorstore(doc_path)
    retrieved = retrieve(query, index, chunks, embedder)
    return generate_answer(query, retrieved)


if __name__ == "__main__":
    import sys
    doc_path = sys.argv[1]
    query = "Summarize this text."

    answer = run_rag(doc_path, query)
    print("\n--- ANSWER ---\n")
    print(answer)
