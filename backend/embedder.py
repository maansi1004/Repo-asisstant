from sentence_transformers import SentenceTransformer
import time

# Loads the model locally on first run, cached after that
# No API key, no rate limits, completely free forever
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_chunks(chunks: list[dict]) -> list[dict]:
    embedded = []
    total = len(chunks)
    print(f"Starting embedding of {total} chunks...")

    for i, chunk in enumerate(chunks):
        try:
            chunk["embedding"] = embed_text(chunk["text"])
            embedded.append(chunk)
            if i % 10 == 0:
                print(f"Progress: {i+1}/{total} chunks embedded")
        except Exception as e:
            print(f"FAILED chunk {i+1}/{total}: {type(e).__name__}: {e}")
            continue

    print(f"Finished: {len(embedded)}/{total} chunks embedded successfully")
    return embedded


def embed_query(question: str) -> list[float]:
    query_text = f"Search query about code: {question}"
    embedding = model.encode(query_text, normalize_embeddings=True)
    return embedding.tolist() 