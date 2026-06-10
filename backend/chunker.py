import re
from pathlib import Path

# ─── Constants ────────────────────────────────────────────────

OVERLAP_LINES = 3
MIN_CHUNK_CHARS = 10
MAX_CHUNK_CHARS = 800

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".cpp", ".c", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".r", ".m", ".sh"
}

# These get special chunkers
SQL_EXTENSIONS = {".sql"}
HTML_EXTENSIONS = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte"}
MARKDOWN_EXTENSIONS = {".md", ".mdx", ".rst"}

# These stay as one chunk — splitting them loses meaning
WHOLE_FILE_EXTENSIONS = {
    ".json", ".toml", ".yaml", ".yml", ".env",
    ".ini", ".cfg", ".conf", ".xml", ".csv"
}

# Skip these entirely
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3",
    ".woff", ".woff2", ".ttf", ".eot", ".lock",
    ".pyc", ".pyo", ".class", ".exe", ".bin", ".dll"
}

# Function/class boundary patterns for code files
BOUNDARY_PATTERNS = [
    ("python",  r"^(def |class |async def )"),
    ("js",      r"^(function |class |const .+ = .*(function|\(.*\) =>)|export (default |const |function |class ))"),
    ("java",    r"^(public |private |protected |static |void |class )"),
    ("go",      r"^func "),
    ("rust",    r"^(pub fn |fn |impl |pub struct |struct )"),
    ("generic", r"^(def |function |func |sub |procedure )")
]

# SQL block patterns
SQL_BOUNDARY_PATTERNS = [
    r"(?i)^CREATE\s+(OR\s+REPLACE\s+)?(TABLE|VIEW|INDEX|PROCEDURE|FUNCTION|TRIGGER|SEQUENCE)",
    r"(?i)^ALTER\s+TABLE",
    r"(?i)^DROP\s+(TABLE|VIEW|INDEX|PROCEDURE|FUNCTION|TRIGGER)",
    r"(?i)^INSERT\s+INTO",
    r"(?i)^SELECT\s+",
    r"(?i)^UPDATE\s+",
    r"(?i)^DELETE\s+FROM",
    r"(?i)^--\s+\w",  # SQL comment as section marker
]


# ─── Language detection ────────────────────────────────────────

def get_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
        ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
        ".cs": "csharp", ".cpp": "cpp", ".c": "c", ".swift": "swift",
        ".sql": "sql", ".html": "html", ".htm": "html",
        ".vue": "vue", ".svelte": "svelte",
        ".md": "markdown", ".mdx": "markdown", ".rst": "rst",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".toml": "toml", ".sh": "bash", ".env": "env"
    }
    return mapping.get(ext, "text")


def should_process(filepath: str) -> bool:
    return Path(filepath).suffix.lower() not in SKIP_EXTENSIONS


def make_chunk(filepath: str, text: str, func_name: str,
               chunk_index: int, sub_index: int = 0) -> dict:
    """Helper to build a standard chunk dict."""
    language = get_language(filepath)
    filename = Path(filepath).name
    context_header = f"File: {filepath}\nLanguage: {language}\nBlock: {func_name}\n\n"
    full_text = context_header + text.strip()

    return {
        "id": f"{filepath}::{func_name}::{chunk_index}_{sub_index}",
        "text": full_text,
        "metadata": {
            "filepath": filepath,
            "filename": filename,
            "language": language,
            "func_name": func_name,
            "chunk_index": chunk_index,
            "char_count": len(text)
        }
    }


# ─── Code chunker (Python, JS, Java, etc) ─────────────────────

def is_code_boundary(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith("//"):
        return False
    for _, pattern in BOUNDARY_PATTERNS:
        if re.match(pattern, stripped):
            return True
    return False


def chunk_code_file(filepath: str, content: str) -> list[dict]:
    """
    Split code files by function/class boundaries.
    Works for Python, JavaScript, TypeScript, Java, Go, Rust, etc.
    """
    lines = content.splitlines()
    if not lines:
        return []

    # Find boundaries
    boundaries = [0]
    current_class = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^class \w+", stripped):
            current_class = re.match(r"^class (\w+)", stripped)
            current_class = current_class.group(1) if current_class else None
        if i > 0 and is_code_boundary(line):
            boundaries.append(i)
    boundaries.append(len(lines))

    chunks = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        chunk_lines = lines[start:end]

        # Add overlap
        if idx > 0 and OVERLAP_LINES > 0:
            prev_start = boundaries[idx - 1]
            overlap = lines[max(prev_start, start - OVERLAP_LINES):start]
            chunk_lines = overlap + chunk_lines

        chunk_text = "\n".join(chunk_lines).strip()
        if len(chunk_text) < MIN_CHUNK_CHARS:
            continue

        # Split oversized chunks
        sub_chunks = []
        if len(chunk_text) > MAX_CHUNK_CHARS:
            mid = len(chunk_lines) // 2
            sub_chunks.append("\n".join(chunk_lines[:mid]).strip())
            sub_chunks.append("\n".join(chunk_lines[mid:]).strip())
        else:
            sub_chunks.append(chunk_text)

        # Extract function name
        first_line = chunk_lines[0].strip() if chunk_lines else ""
        name_match = re.match(r"(?:def |class |func |function |pub fn |async def )(\w+)", first_line)
        func_name = name_match.group(1) if name_match else f"block_{idx}"
        if current_class and func_name != current_class:
            func_name = f"{current_class}.{func_name}"

        for sub_idx, sub_text in enumerate(sub_chunks):
            if len(sub_text) >= MIN_CHUNK_CHARS:
                chunks.append(make_chunk(filepath, sub_text, func_name, idx, sub_idx))

    return chunks


# ─── SQL chunker ───────────────────────────────────────────────

def chunk_sql_file(filepath: str, content: str) -> list[dict]:
    """
    Split SQL files by CREATE/ALTER/SELECT/INSERT etc.
    Each procedure, trigger, table definition becomes one chunk.
    
    Before: entire SQL file = 1 giant useless chunk
    After:  CREATE TABLE users, CREATE PROCEDURE login_user, etc = separate chunks
    """
    lines = content.splitlines()
    if not lines:
        return []

    boundaries = [0]
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        for pattern in SQL_BOUNDARY_PATTERNS:
            if re.match(pattern, stripped):
                if i > 0:
                    boundaries.append(i)
                break
    boundaries.append(len(lines))

    # Deduplicate and sort
    boundaries = sorted(set(boundaries))

    chunks = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        chunk_text = "\n".join(lines[start:end]).strip()

        if len(chunk_text) < MIN_CHUNK_CHARS:
            continue

        # Extract SQL object name for func_name
        first_meaningful = ""
        for line in lines[start:end]:
            if line.strip() and not line.strip().startswith("--"):
                first_meaningful = line.strip()
                break

        name_match = re.search(
            r"(?i)(TABLE|PROCEDURE|FUNCTION|TRIGGER|VIEW)\s+`?(\w+)`?",
            first_meaningful
        )
        if name_match:
            func_name = f"{name_match.group(1).lower()}_{name_match.group(2)}"
        else:
            words = first_meaningful.split()[:3]
            func_name = "_".join(words).lower()[:40] if words else f"block_{idx}"

        # Split large SQL blocks
        if len(chunk_text) > MAX_CHUNK_CHARS:
            mid = len(chunk_text) // 2
            chunks.append(make_chunk(filepath, chunk_text[:mid], f"{func_name}_part1", idx, 0))
            chunks.append(make_chunk(filepath, chunk_text[mid:], f"{func_name}_part2", idx, 1))
        else:
            chunks.append(make_chunk(filepath, chunk_text, func_name, idx))

    # Fallback — if no boundaries found treat as one chunk
    if not chunks and content.strip():
        chunks.append(make_chunk(filepath, content[:MAX_CHUNK_CHARS], "sql_content", 0))

    return chunks


# ─── HTML/JSX/Vue chunker ──────────────────────────────────────

def chunk_html_file(filepath: str, content: str) -> list[dict]:
    """
    Split HTML/JSX/Vue files by major sections.
    
    Strategy:
    - Split at top-level tags: <section>, <div id=>, <component>
    - Keep script and style blocks separate
    - For JSX/TSX: split by return statement and function definitions
    """
    ext = Path(filepath).suffix.lower()

    # For JSX/TSX use code chunker since they have JS function boundaries
    if ext in {".jsx", ".tsx"}:
        return chunk_code_file(filepath, content)

    lines = content.splitlines()
    if not lines:
        return []

    # HTML section boundaries
    section_patterns = [
        r"^\s*<(section|article|header|footer|main|nav|aside)",
        r"^\s*<div\s+(id|class)=",
        r"^\s*<(script|style)",
        r"^\s*<!--\s*\w",  # HTML comment as section marker
        r"^\s*<(form|table|ul|ol)",
    ]

    boundaries = [0]
    for i, line in enumerate(lines):
        for pattern in section_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                if i > 0:
                    boundaries.append(i)
                break
    boundaries.append(len(lines))
    boundaries = sorted(set(boundaries))

    # If no boundaries found, split by character count
    if len(boundaries) <= 2:
        if len(content) <= MAX_CHUNK_CHARS:
            return [make_chunk(filepath, content, "html_content", 0)]
        else:
            chunks = []
            for i, start in enumerate(range(0, len(content), MAX_CHUNK_CHARS)):
                chunk_text = content[start:start + MAX_CHUNK_CHARS]
                chunks.append(make_chunk(filepath, chunk_text, f"html_section_{i}", i))
            return chunks

    chunks = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        chunk_text = "\n".join(lines[start:end]).strip()

        if len(chunk_text) < MIN_CHUNK_CHARS:
            continue

        # Name from first meaningful tag
        first_line = lines[start].strip() if lines[start:end] else ""
        tag_match = re.search(r"<(\w+)", first_line)
        func_name = f"html_{tag_match.group(1)}_{idx}" if tag_match else f"html_block_{idx}"

        if len(chunk_text) > MAX_CHUNK_CHARS:
            chunks.append(make_chunk(filepath, chunk_text[:MAX_CHUNK_CHARS], func_name, idx, 0))
            chunks.append(make_chunk(filepath, chunk_text[MAX_CHUNK_CHARS:], f"{func_name}_cont", idx, 1))
        else:
            chunks.append(make_chunk(filepath, chunk_text, func_name, idx))

    return chunks


# ─── Markdown chunker ──────────────────────────────────────────

def chunk_markdown_file(filepath: str, content: str) -> list[dict]:
    """
    Split markdown by ## headings.
    Each section becomes one chunk.
    README is very important — keep it well-chunked.
    """
    lines = content.splitlines()
    if not lines:
        return []

    boundaries = [0]
    for i, line in enumerate(lines):
        if re.match(r"^#{1,3}\s+\w", line):
            if i > 0:
                boundaries.append(i)
    boundaries.append(len(lines))
    boundaries = sorted(set(boundaries))

    # If no headings, treat as one chunk
    if len(boundaries) <= 2:
        if len(content) <= MAX_CHUNK_CHARS * 2:
            return [make_chunk(filepath, content, "readme_content", 0)]
        else:
            # Split by paragraphs
            paragraphs = re.split(r"\n\n+", content)
            chunks = []
            for i, para in enumerate(paragraphs):
                if len(para.strip()) >= MIN_CHUNK_CHARS:
                    chunks.append(make_chunk(filepath, para, f"paragraph_{i}", i))
            return chunks

    chunks = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        chunk_text = "\n".join(lines[start:end]).strip()

        if len(chunk_text) < MIN_CHUNK_CHARS:
            continue

        # Extract heading as name
        heading_match = re.match(r"^#{1,3}\s+(.+)", lines[start].strip())
        if heading_match:
            heading = heading_match.group(1)
            func_name = re.sub(r"[^\w\s]", "", heading).strip().replace(" ", "_")[:40].lower()
        else:
            func_name = f"section_{idx}"

        if len(chunk_text) > MAX_CHUNK_CHARS:
            chunks.append(make_chunk(filepath, chunk_text[:MAX_CHUNK_CHARS], func_name, idx, 0))
            chunks.append(make_chunk(filepath, chunk_text[MAX_CHUNK_CHARS:], f"{func_name}_cont", idx, 1))
        else:
            chunks.append(make_chunk(filepath, chunk_text, func_name, idx))

    return chunks


# ─── Whole file chunker ────────────────────────────────────────

def chunk_whole_file(filepath: str, content: str) -> list[dict]:
    """
    For JSON, YAML, TOML, .env etc — keep as one chunk.
    Splitting these loses the structural meaning.
    If too large, split by MAX_CHUNK_CHARS only.
    """
    if not content.strip():
        return []

    if len(content) <= MAX_CHUNK_CHARS * 2:
        return [make_chunk(filepath, content, "config_content", 0)]

    # Too large — split but keep it simple
    chunks = []
    for i, start in enumerate(range(0, len(content), MAX_CHUNK_CHARS)):
        chunk_text = content[start:start + MAX_CHUNK_CHARS]
        if chunk_text.strip():
            chunks.append(make_chunk(filepath, chunk_text, f"config_part_{i}", i))
    return chunks


# ─── Main dispatcher ───────────────────────────────────────────

def split_into_chunks(filepath: str, content: str) -> list[dict]:
    """
    Route each file to the right chunker based on extension.

    .py .js .ts .java etc  → chunk_code_file    (function boundaries)
    .sql                   → chunk_sql_file     (SQL statement boundaries)
    .html .htm .vue        → chunk_html_file    (tag/section boundaries)
    .md .rst               → chunk_markdown_file (heading boundaries)
    .json .yaml .toml .env → chunk_whole_file   (keep whole)
    anything else          → chunk_code_file    (best effort)
    """
    if not should_process(filepath):
        return []

    if not content or not content.strip():
        return []

    ext = Path(filepath).suffix.lower()

    if ext in SKIP_EXTENSIONS:
        return []
    elif ext in SQL_EXTENSIONS:
        return chunk_sql_file(filepath, content)
    elif ext in MARKDOWN_EXTENSIONS:
        return chunk_markdown_file(filepath, content)
    elif ext in WHOLE_FILE_EXTENSIONS:
        return chunk_whole_file(filepath, content)
    elif ext in HTML_EXTENSIONS:
        return chunk_html_file(filepath, content)
    elif ext in CODE_EXTENSIONS:
        return chunk_code_file(filepath, content)
    else:
        # Unknown extension — try code chunker, fallback to whole file
        chunks = chunk_code_file(filepath, content)
        if not chunks:
            return chunk_whole_file(filepath, content)
        return chunks


def chunk_all_files(files: dict) -> list[dict]:
    """
    Chunk every file in the repo using the right strategy per file type.
    files = {filepath: content} dict
    Returns flat list of all chunks.
    """
    all_chunks = []
    stats = {}

    for filepath, content in files.items():
        ext = Path(filepath).suffix.lower()
        file_chunks = split_into_chunks(filepath, content)
        all_chunks.extend(file_chunks)

        # Track stats per extension
        if ext not in stats:
            stats[ext] = {"files": 0, "chunks": 0}
        stats[ext]["files"] += 1
        stats[ext]["chunks"] += len(file_chunks)

    # Print chunking summary
    print("\nChunking summary:")
    for ext, s in sorted(stats.items()):
        print(f"  {ext or 'no-ext'}: {s['files']} files → {s['chunks']} chunks")
    print(f"  Total: {len(all_chunks)} chunks\n")

    return all_chunks
