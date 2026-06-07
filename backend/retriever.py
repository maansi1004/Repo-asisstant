from store import get_collection
from embedder import embed_query

# Always include these files regardless of what search returns
# They give Claude the structural overview of the repo
ALWAYS_INCLUDE_NAMES = ["readme.md", "main.py", "index.js", "app.py",
                         "index.ts", "app.ts", "main.go", "config.py",
                         "settings.py", "package.json", "pyproject.toml"]

RETRIEVE_CANDIDATES = 20   # fetch top 20 from ChromaDB first
FINAL_TOP_K = 8          # send only top 5 to Groq


def keyword_score(question: str, text: str) -> float:
    """
    Simple keyword overlap score.
    Counts how many question words appear in the chunk text.
    Used as the second signal in hybrid search.
    
    Returns a float 0.0 to 1.0
    """
    question_words = set(question.lower().split())
    text_lower = text.lower()

    # Remove common stop words that add noise
    stop_words = {"the", "a", "an", "is", "in", "of", "to", "and",
                  "or", "for", "with", "how", "what", "where", "which", "does"}
    question_words -= stop_words

    if not question_words:
        return 0.0

    matches = sum(1 for word in question_words if word in text_lower)
    return matches / len(question_words)


def get_always_include_chunks() -> list[dict]:
    """
    Fetch structural files that should always be in context.
    These are retrieved by filename match, not by vector search.
    """
    collection = get_collection()
    results = []

    try:
        # Query ChromaDB for chunks from important files
        all_results = collection.get(include=["documents", "metadatas"])
        if not all_results["ids"]:
            return []

        seen_files = set()
        for doc, meta in zip(all_results["documents"], all_results["metadatas"]):
            filename = meta.get("filename", "").lower()
            filepath = meta.get("filepath", "")

            if filename in ALWAYS_INCLUDE_NAMES and filepath not in seen_files:
                seen_files.add(filepath)
                results.append({
                    "text": doc,
                    "metadata": meta,
                    "score": 1.0,  # always-include gets max score
                    "source": "always_include"
                })

    except Exception as e:
        print(f"Could not fetch always-include chunks: {e}")

    return results[:2]  # max 2 always-include so they don't crowd out search results


def retrieve(question: str) -> list[dict]:
    """
    Main retrieval function. Returns top chunks relevant to the question.
    
    Process:
    1. Embed the question
    2. Fetch top 20 candidates from ChromaDB by vector similarity
    3. Score each by keyword overlap too (hybrid search)
    4. Combine scores: 70% vector + 30% keyword
    5. Sort by combined score
    6. Add always-include structural files
    7. Return top FINAL_TOP_K chunks
    """
    collection = get_collection()

    # Step 1 — embed the question
    q_embedding = embed_query(question)

    # Step 2 — vector search: get top 20 candidates
    try:
        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=min(RETRIEVE_CANDIDATES, collection.count()),
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        print(f"ChromaDB query failed: {e}")
        return []

    if not results["ids"] or not results["ids"][0]:
        return []

    # Step 3 — score each candidate
    candidates = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        # ChromaDB returns cosine distance (lower = more similar)
        # Convert to similarity score (higher = better)
        vector_sim = 1 - distance  # now higher = better

        # Step 4 — hybrid: combine vector + keyword
        kw_score = keyword_score(question, doc)
        combined = (vector_sim * 0.7) + (kw_score * 0.3)

        candidates.append({
            "text": doc,
            "metadata": meta,
            "score": round(combined, 4),
            "vector_sim": round(vector_sim, 4),
            "keyword_score": round(kw_score, 4),
            "source": "search"
        })

    # Step 5 — sort by combined score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Step 6 — add always-include structural files
    always = get_always_include_chunks()

    # Merge: always-include first, then search results
    # Deduplicate by filepath (don't include same file twice)
    seen_paths = set()
    final = []

    for chunk in always + candidates:
        fp = chunk["metadata"].get("filepath", "")
        if fp not in seen_paths:
            seen_paths.add(fp)
            final.append(chunk)
        if len(final) >= FINAL_TOP_K:
            break

    return final


def format_context(chunks: list[dict]) -> tuple[str, list[str]]:
    """
    Convert retrieved chunks into a prompt-ready string.
    Also returns a list of filepaths used (for the frontend to display).
    
    Returns: (context_string, list_of_filepaths)
    """
    context_parts = []
    filepaths = []

    for i, chunk in enumerate(chunks):
        fp = chunk["metadata"].get("filepath", "unknown")
        func = chunk["metadata"].get("func_name", "")
        score = chunk.get("score", 0)
        source = chunk.get("source", "search")



        confidence = f"{int(score * 100)}%" if source == "search" else "always-include"


        context_parts.append(
            f"--- Source {i+1}: {fp} (function: {func}| relevance: {score} |confidence: {confidence}) ---\n"
            f"{chunk['text']}"
        )

        if fp not in filepaths:
            filepaths.append(fp)

    return "\n\n".join(context_parts), filepaths
