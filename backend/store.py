import chromadb
from chromadb.config import Settings

# Create a persistent ChromaDB client
# persist_directory means data survives backend restarts
# Unlike V1 where everything lived in a Python dict in RAM

client = chromadb.PersistentClient(
    path="D:\\chroma_db",  # folder where vectors are saved on disk
    settings=Settings(anonymized_telemetry=False)
)

# A "collection" is like a table in a regular database
# It holds all our code chunks + their vectors
# collection = client.get_or_create_collection(
#     name="repo_chunks",
#     metadata={"hnsw:space": "cosine"}  # cosine = measure similarity by angle, best for text
# )
collection = client.get_or_create_collection(
    name="repo_chunks",
    metadata={"hnsw:space": "cosine"}
)

def save_chunks(chunks: list[dict]):
    """
    Save a list of chunks into ChromaDB.
    Each chunk must have: id, text, embedding, metadata

    What gets stored per chunk:
    - id: unique string like "auth.py::login::0"
    - embedding: list of ~768 numbers (the vector)
    - document: the raw code text (so we can return it later)
    - metadata: filepath, function name, language, etc.
    """
    if not chunks:
        return

    collection.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )


def reset_collection():
    """
    Delete all stored chunks and start fresh.
    Called when user uploads a new repo.
    """
    global collection
    client.delete_collection("repo_chunks")
    collection = client.get_or_create_collection(
        name="repo_chunks",
        metadata={"hnsw:space": "cosine"}
    )


def get_collection():
    return collection

def get_all_chunks() -> list[dict]:
    """Return all chunks stored in ChromaDB."""
    count = collection.count()
    if count == 0:
        return []
    results = collection.get(include=["documents", "metadatas"])
    output = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        output.append({"text": doc, "metadata": meta})
    return output


def chunk_count() -> int:
    """Return total number of chunks stored."""
    return collection.count()


def load_store():
    """Compatibility stub — ChromaDB loads automatically from disk."""
    count = collection.count()
    if count > 0:
        print(f"ChromaDB ready with {count} existing chunks")
    else:
        print("ChromaDB ready — upload a repo to get started")


def search(query_embedding: list[float], n_results: int = 20) -> list[dict]:
    """Search ChromaDB by vector similarity."""
    count = collection.count()
    if count == 0:
        return []
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"]
    )
    if not results["ids"] or not results["ids"][0]:
        return []
    output = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        output.append({
            "text": doc,
            "metadata": meta,
            "similarity": round(1 - distance, 4)
        })
    return output