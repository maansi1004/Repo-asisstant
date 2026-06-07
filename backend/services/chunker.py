import re
from dataclasses import dataclass
from config import MIN_CHUNK_CHARS, MAX_CHUNK_CHARS


@dataclass
class Chunk:
    # A single meaningful piece of code
    text: str           # the actual code content
    filepath: str       # which file it came from
    chunk_type: str     # "function", "class", or "block"
    name: str           # function/class name if found, else ""
    start_line: int     # line number where this chunk starts


# Patterns that signal the start of a new meaningful unit
# Works for Python, JS, TS, Java, Go, Rust basics
BOUNDARY_PATTERNS = [
    # Python / Ruby
    r"^(async\s+)?def\s+\w+",
    r"^class\s+\w+",
    # JavaScript / TypeScript
    r"^(export\s+)?(default\s+)?(async\s+)?function\s+\w+",
    r"^(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?\(",
    r"^(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?function",
    r"^(export\s+)?class\s+\w+",
    # Arrow functions assigned to const at top level
    r"^(export\s+)?(const|let)\s+\w+\s*=\s*(\w+\s*)=>",
    # Go
    r"^func\s+\w+",
    # Rust
    r"^(pub\s+)?fn\s+\w+",
    # Java / C#
    r"^(public|private|protected|static|\s)+[\w<>\[\]]+\s+\w+\s*\(",
]

COMPILED = [re.compile(p, re.MULTILINE) for p in BOUNDARY_PATTERNS]


def _is_boundary(line: str) -> tuple[bool, str, str]:
    """
    Returns (is_boundary, chunk_type, name).
    Checks if a line starts a new logical unit.
    """
    stripped = line.strip()
    for pattern in COMPILED:
        if pattern.match(stripped):
            # Extract the name — word after def/function/class/fn/func
            name_match = re.search(r"\b(def|function|class|fn|func)\s+(\w+)", stripped)
            name = name_match.group(2) if name_match else ""
            chunk_type = "class" if "class" in stripped else "function"
            return True, chunk_type, name
    return False, "", ""


def _extract_name(line: str) -> str:
    m = re.search(r"\b(def|function|class|fn|func)\s+(\w+)", line)
    return m.group(2) if m else ""


def chunk_file(filepath: str, content: str) -> list[Chunk]:
    """
    Main function — takes a file path and its text content,
    returns a list of Chunk objects.

    Strategy:
    1. Walk lines and detect boundary patterns
    2. Each boundary starts a new chunk
    3. Add last 3 lines of previous chunk to next one (overlap)
    4. Skip chunks that are too short or too long
    """
    lines = content.splitlines()
    chunks: list[Chunk] = []

    current_lines: list[str] = []
    current_start = 1
    current_type = "block"
    current_name = ""
    overlap_lines: list[str] = []  # last few lines of prev chunk

    def save_chunk():
        """Save whatever is in current_lines as a finished chunk."""
        if not current_lines:
            return
        # Prepend overlap from previous chunk for context
        text = "\n".join(overlap_lines + current_lines)
        # Add file + function header so embedding includes location
        header = f"# File: {filepath}"
        if current_name:
            header += f"  |  {current_type}: {current_name}"
        full_text = header + "\n" + text

        if len(full_text) < MIN_CHUNK_CHARS:
            return   # too short — skip (e.g. a single import line)
        if len(full_text) > MAX_CHUNK_CHARS:
            # Truncate rather than skip — still useful, just trimmed
            full_text = full_text[:MAX_CHUNK_CHARS] + "\n# ... truncated"

        chunks.append(Chunk(
            text=full_text,
            filepath=filepath,
            chunk_type=current_type,
            name=current_name,
            start_line=current_start,
        ))

    for i, line in enumerate(lines, start=1):
        is_boundary, btype, bname = _is_boundary(line)

        if is_boundary and current_lines:
            # Save the current chunk before starting new one
            # Keep last 3 lines as overlap for next chunk
            overlap_lines = current_lines[-3:]
            save_chunk()
            current_lines = []
            current_start = i
            current_type = btype
            current_name = bname

        current_lines.append(line)

    # Don't forget the last chunk
    save_chunk()

    # If no boundaries found (e.g. a config file), treat whole file as one chunk
    if not chunks and content.strip():
        text = f"# File: {filepath}\n{content}"
        if MIN_CHUNK_CHARS <= len(text) <= MAX_CHUNK_CHARS * 2:
            chunks.append(Chunk(
                text=text[:MAX_CHUNK_CHARS],
                filepath=filepath,
                chunk_type="block",
                name="",
                start_line=1,
            ))

    return chunks
