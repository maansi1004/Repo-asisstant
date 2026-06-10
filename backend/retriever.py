from store import search, get_all_chunks, load_store
from embedder import embed_query
from reranker import rerank

ALWAYS_INCLUDE_NAMES = [
    "readme.md", "main.py", "index.js", "app.py",
    "index.ts", "app.ts", "config.py", "settings.py",
    "server.js", "package.json", "pyproject.toml"
]

# How many candidates to fetch before reranking
# Wider net = better reranking results
RETRIEVE_CANDIDATES = 20

# How many to send to Gemini after reranking
FINAL_TOP_K = 5


def keyword_score(question: str, text: str) -> float:
    """Simple keyword overlap — used as tiebreaker only."""
    question_words = set(question.lower().split())
    text_lower = text.lower()
    stop_words = {
        "the", "a", "an", "is", "in", "of", "to", "and",
        "or", "for", "with", "how", "what", "where", "which", "does"
    }
    question_words -= stop_words
    if not question_words:
        return 0.0
    matches = sum(1 for word in question_words if word in text_lower)
    return matches / len(question_words)


def expand_query(question: str) -> str:
    """
    Expand short questions with domain-specific terms.
    Helps embedding model find relevant chunks even when
    the exact words don't match.
    """
    expansions = {
        "auth": "authentication login logout session token jwt passport oauth middleware verify credentials user signin signup",
        "login": "login authentication signin credentials username password jwt session token",
        "database": "database db query model schema table sql orm mongoose prisma sequelize",
        "api": "api endpoint route handler request response controller express fastapi",
        "error": "error exception handling try catch logging middleware",
        "config": "configuration settings environment variables constants dotenv",
        "payment": "payment stripe checkout billing invoice subscription",
        "upload": "upload file storage multer s3 cloudinary",
        "email": "email smtp nodemailer sendgrid notification",
        "test": "test unittest pytest jest spec describe",
        "security": "security auth jwt bcrypt cors helmet validation sanitize",
        "deploy": "deployment docker kubernetes ci cd pipeline",
        "cache": "cache redis memcache storage session",
        "websocket": "websocket socket realtime emit listen event",
        "middleware": "middleware interceptor filter guard pipe decorator",
    }

    expanded = question
    question_lower = question.lower()
    for keyword, expansion in expansions.items():
        if keyword in question_lower:
            expanded = f"{question} {expansion}"
            break

    return expanded


def get_always_include_chunks() -> list[dict]:
    """
    Fetch structural files that always go into context.
    These give Gemini the big picture regardless of the question.
    """
    all_chunks = get_all_chunks()
    results = []
    seen_files = set()

    for chunk in all_chunks:
        filename = chunk["metadata"].get("filename", "").lower()
        filepath = chunk["metadata"].get("filepath", "")
        if filename in ALWAYS_INCLUDE_NAMES and filepath not in seen_files:
            seen_files.add(filepath)
            results.append({
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "score": 1.0,
                "reranker_score": 1.0,
                "source": "always_include"
            })

    return results[:2]  # max 2 always-include


def retrieve(question: str) -> list[dict]:
    """
    Full retrieval pipeline with reranking:

    1. Expand query for better embedding matching
    2. Embed expanded query
    3. Vector search — get top 20 candidates (wide net)
    4. Rerank — cross-encoder scores all 20, keeps top 5
    5. Add always-include structural files
    6. Return final context chunks

    The key improvement over basic retrieval:
    Step 4 filters out false positives that vector similarity
    would have included. Cross-encoder is much more precise
    because it evaluates query + chunk together.
    """

    # Step 1: expand query
    expanded = expand_query(question)

    # Step 2: embed
    q_embedding = embed_query(expanded)

    # Step 3: vector search — get wide set of candidates
    candidates = search(q_embedding, n_results=RETRIEVE_CANDIDATES)

    if not candidates:
        return []

    # Convert to standard format with scores
    for c in candidates:
        c["score"] = c.get("similarity", 0)
        c["source"] = "search"

    # Step 4: RERANK — this is the key improvement
    # Cross-encoder re-scores all 20 candidates against the question
    # Much more accurate than cosine similarity alone
    reranked = rerank(question, candidates, top_k=FINAL_TOP_K)

    # Step 5: add always-include structural files
    always = get_always_include_chunks()

    # Merge — always-include first, then reranked results
    seen_paths = set()
    final = []

    for chunk in always + reranked:
        fp = chunk["metadata"].get("filepath", "")
        if fp not in seen_paths:
            seen_paths.add(fp)
            final.append(chunk)
        if len(final) >= FINAL_TOP_K + len(always):
            break

    return final


def format_context(chunks: list[dict]) -> tuple[str, list[str]]:
    """
    Format chunks into a prompt-ready context string.
    Shows reranker score so Gemini knows which chunks are most relevant.
    """
    context_parts = []
    filepaths = []

    for i, chunk in enumerate(chunks):
        fp = chunk["metadata"].get("filepath", "unknown")
        func = chunk["metadata"].get("func_name", "")
        lang = chunk["metadata"].get("language", "")
        reranker_score = chunk.get("reranker_score", chunk.get("score", 0))
        source = chunk.get("source", "search")

        if source == "always_include":
            relevance = "structural"
        else:
            relevance = f"{int(reranker_score * 10) if reranker_score <= 1 else round(reranker_score, 2)}"

        context_parts.append(
            f"--- [{i+1}] {fp} | fn: {func} | lang: {lang} | relevance: {relevance} ---\n"
            f"{chunk['text']}"
        )

        if fp not in filepaths:
            filepaths.append(fp)

    return "\n\n".join(context_parts), filepaths
