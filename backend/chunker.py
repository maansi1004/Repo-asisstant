import re
from pathlib import Path

# File extensions we actually want to chunk
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".cpp", ".c", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".r", ".m", ".sh", ".yaml", ".yml",
    ".json", ".toml", ".md", ".html", ".css", ".sql"
}

# Regex patterns that mark the START of a new chunk
# Each tuple is (language_hint, pattern)
BOUNDARY_PATTERNS = [
    ("python",  r"^(def |class |async def )"),
    ("js",      r"^(function |class |const .+ = .*(function|\(.*\) =>)|export (default |const |function |class ))"),
    ("java",    r"^(public |private |protected |static |void |class )"),
    ("go",      r"^func "),
    ("rust",    r"^(pub fn |fn |impl |pub struct |struct )"),
    ("generic", r"^(def |function |func |sub |procedure )")
]

OVERLAP_LINES = 3   # how many lines from prev chunk to prepend to next
MIN_CHUNK_CHARS = 60  # skip tiny chunks like a single import line
MAX_CHUNK_CHARS = 1500  # split very large functions so they fit in context


def get_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
        ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
        ".cs": "csharp", ".cpp": "cpp", ".c": "c", ".swift": "swift"
    }
    return mapping.get(ext, "text")


def should_chunk(filepath: str) -> bool:
    return Path(filepath).suffix.lower() in CODE_EXTENSIONS


def is_boundary(line: str) -> bool:
    """
    Returns True if this line starts a new logical block
    (a function, class, method etc.)
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith("//"):
        return False
    for _, pattern in BOUNDARY_PATTERNS:
        if re.match(pattern, stripped):
            return True
    return False


def split_into_chunks(filepath: str, content: str) -> list[dict]:
    """
    Split a file's content into meaningful chunks.

    Strategy:
    1. Find every function/class boundary
    2. Each boundary starts a new chunk
    3. Add last OVERLAP_LINES of prev chunk to start of next
    4. Add rich metadata to every chunk so retrieval knows context

    Returns list of chunk dicts, each with:
    - id: unique identifier
    - text: the actual code (with context header)
    - metadata: filepath, language, function name, chunk index
    """
    if not should_chunk(filepath):
        return []

    lines = content.splitlines()
    if not lines:
        return []

    language = get_language(filepath)
    filename = Path(filepath).name

    # Find all boundary line indices
    boundaries = [0]  # always start first chunk at line 0
    for i, line in enumerate(lines):
        if i > 0 and is_boundary(line):
            boundaries.append(i)

    # If no boundaries found (e.g. a config file), treat whole file as one chunk
    if len(boundaries) == 1:
        boundaries.append(len(lines))
    else:
        boundaries.append(len(lines))  # sentinel end

    chunks = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        chunk_lines = lines[start:end]

        # Add overlap from previous chunk
        if idx > 0 and OVERLAP_LINES > 0:
            prev_start = boundaries[idx - 1]
            overlap = lines[max(prev_start, start - OVERLAP_LINES):start]
            chunk_lines = overlap + chunk_lines

        chunk_text = "\n".join(chunk_lines).strip()

        # Skip tiny chunks
        if len(chunk_text) < MIN_CHUNK_CHARS:
            continue

        # Split oversized chunks in half (rare but happens with big classes)
        sub_chunks = []
        if len(chunk_text) > MAX_CHUNK_CHARS:
            mid = len(chunk_lines) // 2
            sub_chunks.append("\n".join(chunk_lines[:mid]).strip())
            sub_chunks.append("\n".join(chunk_lines[mid:]).strip())
        else:
            sub_chunks.append(chunk_text)

        # Try to extract function/class name from first non-empty line
        first_line = chunk_lines[0].strip() if chunk_lines else ""
        name_match = re.match(r"(?:def |class |func |function |pub fn )(\w+)", first_line)
        func_name = name_match.group(1) if name_match else f"block_{idx}"

        for sub_idx, sub_text in enumerate(sub_chunks):
            # Build a rich context header so the embedding understands WHERE this code lives
            context_header = f"File: {filepath}\nLanguage: {language}\nFunction/block: {func_name}\n\n"
            full_text = context_header + sub_text

            chunk_id = f"{filepath}::{func_name}::{idx}_{sub_idx}"

            chunks.append({
                "id": chunk_id,
                "text": full_text,
                "metadata": {
                    "filepath": filepath,
                    "filename": filename,
                    "language": language,
                    "func_name": func_name,
                    "chunk_index": idx,
                    "char_count": len(sub_text)
                }
            })

    return chunks


def chunk_all_files(files: dict) -> list[dict]:
    """
    Chunk every file in the repo.
    files = {filepath: content} dict (same as V1)
    Returns flat list of all chunks across all files.
    """
    all_chunks = []
    for filepath, content in files.items():
        file_chunks = split_into_chunks(filepath, content)
        all_chunks.extend(file_chunks)
    return all_chunks
