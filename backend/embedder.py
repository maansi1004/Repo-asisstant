from sentence_transformers import SentenceTransformer
import time

# Loads the model locally on first run, cached after that
# No API key, no rate limits, completely free forever
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()




def embed_chunks(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []

    total = len(chunks)
    print(f"Embedding {total} chunks in batches of 32...")

    texts = [c["text"] for c in chunks]
    all_embeddings = []

    # Process 32 at a time instead of one by one
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32
        )
        all_embeddings.extend(embeddings.tolist())
        print(f"Embedded {min(i + batch_size, total)}/{total}")

    # Attach embeddings back to chunks
    embedded = []
    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding
        embedded.append(chunk)

    print(f"Done — {len(embedded)} chunks embedded")
    return embedded

def embed_query(question: str) -> list[float]:
    query_text = f"Search query about code: {question}"
    embedding = model.encode(query_text, normalize_embeddings=True)
    return embedding.tolist() 