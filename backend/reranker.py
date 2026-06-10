from sentence_transformers import CrossEncoder
import time

# Cross-encoder model for reranking
# Unlike bi-encoders (used for initial retrieval), cross-encoders
# look at query AND document together — much more accurate scoring
# Downloads ~70MB on first use, cached after that
_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        print("Loading reranker model (first time only)...")
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        print("Reranker loaded")
    return _reranker


def rerank(question: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank retrieved chunks by relevance to the question.

    How it works:
    - Takes question + each chunk text as a pair
    - Cross-encoder scores each pair together (not separately)
    - This is more accurate than cosine similarity because it
      considers the relationship between question and chunk
    - Returns top_k chunks sorted by reranker score

    Example:
    Question: "how does login work?"
    
    Before reranking (by vector similarity):
        chunk1: login function — score 0.82  ✓ relevant
        chunk2: logout function — score 0.79  ✗ not needed
        chunk3: auth middleware — score 0.76  ✓ relevant
        chunk4: user profile — score 0.71    ✗ not needed
        chunk5: password hash — score 0.68   ✓ relevant

    After reranking (by cross-encoder):
        chunk1: login function — score 0.94  ✓ sent to Gemini
        chunk3: auth middleware — score 0.87  ✓ sent to Gemini
        chunk5: password hash — score 0.81   ✓ sent to Gemini
        chunk2: logout function — score 0.23  ✗ filtered out
        chunk4: user profile — score 0.11    ✗ filtered out
    """
    if not chunks:
        return []

    reranker = get_reranker()

    # Build (question, chunk_text) pairs for cross-encoder
    pairs = [(question, chunk["text"]) for chunk in chunks]

    # Score all pairs at once
    start = time.time()
    scores = reranker.predict(pairs)
    elapsed = round(time.time() - start, 2)
    print(f"Reranked {len(chunks)} chunks in {elapsed}s")

    # Attach reranker scores to chunks
    scored_chunks = []
    for chunk, score in zip(chunks, scores):
        chunk["reranker_score"] = round(float(score), 4)
        scored_chunks.append(chunk)

    # Sort by reranker score descending
    scored_chunks.sort(key=lambda x: x["reranker_score"], reverse=True)

    # Return top_k
    return scored_chunks[:top_k]


def rerank_with_threshold(
    question: str,
    chunks: list[dict],
    top_k: int = 5,
    min_score: float = -6.0
) -> list[dict]:
    """
    Rerank and also filter out chunks below min_score.
    Cross-encoder scores are typically in range -10 to +10.
    
    min_score = -6.0 filters out completely irrelevant chunks
    min_score = -2.0 keeps only somewhat relevant chunks
    
    Use rerank() for most cases.
    Use this when you want to also filter weak matches.
    """
    reranked = rerank(question, chunks, top_k=top_k)
    filtered = [c for c in reranked if c.get("reranker_score", 0) >= min_score]

    # Always return at least 2 chunks even if below threshold
    if len(filtered) < 2:
        return reranked[:2]

    return filtered
