import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# --- Embedding ---
# Runs locally via sentence-transformers, no API key needed
EMBED_MODEL = "all-MiniLM-L6-v2"

# --- Vector Store ---
# Simple JSON file on D drive, no ChromaDB needed
VECTOR_STORE_PATH = "D:\\vector_store.json"

# --- Chunking ---
MIN_CHUNK_CHARS = 10
MAX_CHUNK_CHARS = 800

# --- Retrieval ---
RETRIEVAL_CANDIDATES = 20
RETRIEVAL_TOP_K = 8  # Gemini has huge context so we can send more chunks

# --- Files always injected regardless of search result ---
ALWAYS_INCLUDE_NAMES = [
    "readme.md", "main.py", "index.js", "app.py",
    "config.py", "index.ts", "app.ts", "main.go",
    "settings.py", "package.json", "pyproject.toml"
]

# --- Files / dirs to skip during repo walk ---
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".env",
    "venv", ".venv", "dist", "build", ".next", ".idea", ".vscode"
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3",
    ".woff", ".woff2", ".ttf", ".eot", ".lock",
    ".pyc", ".pyo", ".class", ".exe", ".bin", ".dll"
}

# --- Temp directory for zip extraction ---
TMP_DIR = "D:\\tmp"
