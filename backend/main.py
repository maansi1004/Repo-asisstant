import os
import zipfile
import tempfile
import shutil
import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

from chunker import chunk_all_files
from embedder import embed_chunks
from store import save_chunks, reset_collection, get_all_chunks, chunk_count, load_store
from retriever import retrieve, format_context
from dependency_scanner import scan_dependencies
from security_scanner import scan_security
from summarizer import generate_repo_summary
from architect import generate_architecture, generate_mermaid_diagram
from onboarding import generate_onboarding
from git_analyzer import analyze_git_repo, get_git_summary_for_prompt

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# Load existing vectors on startup
load_store()

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "venv",
    ".venv", "dist", "build", ".next", ".idea", ".vscode"
}
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf",
    ".zip", ".tar", ".gz", ".mp4", ".mp3", ".woff", ".woff2",
    ".ttf", ".eot", ".lock", ".pyc", ".exe", ".dll", ".bin",".env",".idea",".vscode"
}

# Central state — files kept in memory for lazy generation
upload_status = {
    "uploaded": False,
    "total_files": 0,
    "total_chunks": 0,
    "file_list": [],
    "files_content": {},   # raw file contents kept for lazy generation
    # All generated data — None until first request
    "summary": None,
    "dependencies": None,
    "security": None,
    "architecture": None,
    "diagram": None,
    "onboarding": None,
    "chat_history": []   # list of {"question": str, "answer": str, "files": [str]},
    ,
    "git_data": None,
    "source": "zip",
    "github_url": None,
}


def restore_upload_status():
    """
    On backend restart, check if ChromaDB already has chunks
    and restore upload_status so user doesn't need to re-upload.
    """
    try:
        count = chunk_count()
        if count == 0:
            return

        # Get all chunks to rebuild file list
        chunks = get_all_chunks()
        if not chunks:
            return

        # Rebuild file list from chunk metadata
        files = sorted(set(
            c["metadata"]["filepath"]
            for c in chunks
            if "filepath" in c.get("metadata", {})
        ))

        # Rebuild files_content from chunks
        # Group chunks by filepath and reconstruct content
        file_content_map = {}
        for chunk in chunks:
            fp = chunk["metadata"].get("filepath", "")
            if fp and fp not in file_content_map:
                # Use chunk text as proxy — good enough for lazy generation
                file_content_map[fp] = chunk["text"]

        upload_status.update({
            "uploaded": True,
            "total_files": len(files),
            "total_chunks": count,
            "file_list": files,
            "files_content": file_content_map,
            "source": "restored",
        })

        print(f"Restored session — {len(files)} files, {count} chunks from ChromaDB")

    except Exception as e:
        print(f"Could not restore session: {e}")


# Call it at startup
restore_upload_status()

def read_files_from_zip(zip_path: str, extract_to: str) -> dict:
    files = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_to)
    for root, dirs, filenames in os.walk(extract_to):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, extract_to)
            if Path(rel_path).suffix.lower() in SKIP_EXTENSIONS:
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if content.strip():
                    files[rel_path] = content
            except Exception:
                continue
    return files


@app.post("/upload")
async def upload_repo(file: UploadFile = File(...)):
    """
    Upload flow — minimal, fast, no Gemini calls:
    1. Extract zip
    2. Read files
    3. Chunk by function boundary
    4. Embed chunks locally
    5. Save to ChromaDB
    6. Run dependency scan (rule-based, instant)

    Everything else (summary, security, diagram, onboarding)
    is generated lazily on first request.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Please upload a .zip file")

    tmp_dir = tempfile.mkdtemp(dir="D:\\tmp")
    zip_path = os.path.join(tmp_dir, "repo.zip")
    extract_path = os.path.join(tmp_dir, "extracted")
    os.makedirs(extract_path)

    try:
        content = await file.read()
        with open(zip_path, "wb") as f:
            f.write(content)

        # Step 1: read files
        files = read_files_from_zip(zip_path, extract_path)
        if not files:
            raise HTTPException(400, "No readable files found in the zip")

        # Step 2: chunk
        print(f"Chunking {len(files)} files...")
        chunks = chunk_all_files(files)
        print(f"Created {len(chunks)} chunks")

        # Step 3: embed
        print("Embedding chunks...")
        embedded_chunks = embed_chunks(chunks)
        print(f"Embedded {len(embedded_chunks)} chunks")

        # Step 4: save
        reset_collection()
        save_chunks(embedded_chunks)

        # Step 5: dependency scan (free, rule-based — run immediately)
        print("Scanning dependencies...")
        deps = scan_dependencies(files)

        # Reset all lazy-generated data
        upload_status.update({
            "uploaded": True,
            "total_files": len(files),
            "total_chunks": len(embedded_chunks),
            "file_list": sorted(files.keys()),
            "files_content": files,   # keep in memory for lazy generation
            "summary": None,
            "dependencies": deps,     # already computed, no cost
            "security": None,
            "architecture": None,
            "diagram": None,
            "onboarding": None,
            "chat_history": []
        })

        print("Upload complete. All analysis available on demand.")

        return {
            "success": True,
            "total_files": len(files),
            "total_chunks": len(embedded_chunks),
            "files": sorted(files.keys()),
            "dependencies": deps,     # send deps immediately since it's free
        }

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── Lazy endpoints ────────────────────────────────────────────

@app.get("/summary")
def get_summary():
    """Generates on first call, cached after that."""
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    if not upload_status["summary"]:
        print("Generating summary (first request)...")
        upload_status["summary"] = generate_repo_summary(
            upload_status["files_content"]
        )

    return upload_status["summary"]


@app.get("/security")
def get_security():
    """Generates on first call (rule-based, no Gemini), cached after that."""
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    if not upload_status["security"]:
        print("Running security scan (first request)...")
        upload_status["security"] = scan_security(
            upload_status["files_content"]
        )

    return upload_status["security"]


@app.get("/dependencies")
def get_dependencies():
    """Already computed during upload — instant."""
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")
    if not upload_status["dependencies"]:
        raise HTTPException(404, "Dependencies not available.")
    return upload_status["dependencies"]


@app.get("/architecture")
def get_architecture():
    """Generates on first call, cached after that."""
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    if not upload_status["architecture"]:
        # Need summary first
        if not upload_status["summary"]:
            upload_status["summary"] = generate_repo_summary(
                upload_status["files_content"]
            )
        print("Generating architecture (first request)...")
        upload_status["architecture"] = generate_architecture(
            upload_status["summary"],
            upload_status["dependencies"] or {}
        )

    return upload_status["architecture"]


@app.get("/diagram")
def get_diagram():
    """Generates on first call, cached after that."""
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    if not upload_status["diagram"]:
        # Need summary + deps first
        if not upload_status["summary"]:
            upload_status["summary"] = generate_repo_summary(
                upload_status["files_content"]
            )
        print("Generating diagram (first request)...")
        upload_status["diagram"] = generate_mermaid_diagram(
            upload_status["summary"],
            upload_status["dependencies"] or {},
            upload_status["file_list"]
        )

    return upload_status["diagram"]


@app.get("/onboard")
def get_onboarding():
    """Generates on first call, cached after that."""
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    if not upload_status["onboarding"]:
        if not upload_status["summary"]:
            upload_status["summary"] = generate_repo_summary(
                upload_status["files_content"]
            )
        print("Generating onboarding guide (first request)...")
        upload_status["onboarding"] = generate_onboarding(
            upload_status["summary"],
            upload_status["dependencies"] or {},
            upload_status["file_list"]
        )

    return upload_status["onboarding"]


@app.get("/status")
def status():
    count = chunk_count()
    git_data = upload_status.get("git_data")
    return {
        "repo_loaded": upload_status["uploaded"],
        "total_files": upload_status["total_files"],
        "total_chunks": upload_status["total_chunks"],
        "chunks_in_store": count,
        "ready": count > 0,
        "source": upload_status.get("source", "zip"),
        "github_url": upload_status.get("github_url"),
        "git_available": git_data is not None and "error" not in (git_data or {}),
        "cached": {
            "summary": upload_status["summary"] is not None,
            "security": upload_status["security"] is not None,
            "architecture": upload_status["architecture"] is not None,
            "diagram": upload_status["diagram"] is not None,
            "onboarding": upload_status["onboarding"] is not None,
            "git": git_data is not None,
        }
    }


@app.get("/explain")
async def explain_file(filepath: str):
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    chunks = get_all_chunks()
    normalized_input = filepath.replace("\\\\", "\\").replace("/", "\\")
    file_chunks = [
        c for c in chunks
        if c["metadata"]["filepath"].replace("/", "\\") == normalized_input
    ]

    if not file_chunks:
        available = sorted(set(c["metadata"]["filepath"] for c in chunks))
        raise HTTPException(404, {
            "error": f"File '{filepath}' not found",
            "available_files": available[:10]
        })

    file_content = "\n\n".join([c["text"] for c in file_chunks])

    prompt = f"""Analyze this file:

{file_content}

Return as JSON:
{{
    "purpose": "what this file does",
    "functions": [{{"name": "fn", "description": "what it does"}}],
    "dependencies": ["import and why"],
    "connections": "how it connects to the codebase",
    "complexity": 5,
    "complexity_reason": "why"
}}
Return only valid JSON, no markdown backticks."""

    try:
        gemini = genai.GenerativeModel("gemini-2.0-flash")
        response = gemini.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        structured = json.loads(raw.strip())
        return {"filepath": filepath, "chunks_analyzed": len(file_chunks), **structured}
    except json.JSONDecodeError:
        return {"filepath": filepath, "chunks_analyzed": len(file_chunks), "explanation": response.text}
    except Exception as e:
        raise HTTPException(500, f"Gemini error: {str(e)}")


# ─── Q&A endpoint ──────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    # conversation_id: Optional[str] = None  # for future multi-session support

# Replace your /ask endpoint in main.py with this version
# It automatically includes git intelligence in answers when available

@app.post("/ask")
async def ask_question(body: QuestionRequest):
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")
    if not body.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    chunks = retrieve(body.question)
    if not chunks:
        raise HTTPException(500, "Could not retrieve relevant chunks.")

    context, filepaths = format_context(chunks)

    # Build conversation history
    history = upload_status.get("chat_history", [])
    history_text = ""
    if history:
        history_text = "\n\nPREVIOUS CONVERSATION:\n"
        for turn in history[-3:]:
            history_text += f"User: {turn['question']}\n"
            history_text += f"Assistant: {turn['answer']}\n\n"

    # Inject git intelligence if available (V3 feature)
    git_context = ""
    git_data = upload_status.get("git_data")
    if git_data and "error" not in git_data:
        from git_analyzer import get_git_summary_for_prompt
        git_context = get_git_summary_for_prompt(git_data)

    prompt = f"""You are a senior software engineer analyzing a codebase.

RELEVANT CODE SECTIONS:
{context}
{git_context}
{history_text}
CURRENT QUESTION: {body.question}

If the question refers to something from the previous conversation
use the history to understand the reference.

If git intelligence is provided above, use it to give more specific
answers about file risk, ownership, and stability.

Return valid JSON:
{{
    "direct_answer": "one sentence answer with exact file and function names",
    "explanation": "detailed explanation referencing actual code and git data if relevant",
    "code_evidence": ["snippet 1 with filepath", "snippet 2"],
    "confidence": "high/medium/low",
    "follow_up_questions": ["follow-up 1", "follow-up 2", "follow-up 3"]
}}
Return only valid JSON, no markdown backticks."""

    try:
        gemini = genai.GenerativeModel("gemini-2.5-flash")
        response = gemini.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        structured = json.loads(raw)

        answer_text = structured.get("explanation", raw)

        upload_status["chat_history"].append({
            "question": body.question,
            "answer": structured.get("direct_answer", answer_text[:200]),
            "files": filepaths
        })

        if len(upload_status["chat_history"]) > 20:
            upload_status["chat_history"] = upload_status["chat_history"][-20:]

        return {
            "direct_answer": structured.get("direct_answer", ""),
            "answer": answer_text,
            "code_evidence": structured.get("code_evidence", []),
            "confidence": structured.get("confidence", "medium"),
            "follow_up_questions": structured.get("follow_up_questions", []),
            "files_used": filepaths,
            "chunks_retrieved": len(chunks),
            "total_files_in_repo": upload_status["total_files"],
            "total_chunks_in_repo": upload_status["total_chunks"],
            "git_available": git_data is not None and "error" not in (git_data or {}),
            "turn_number": len(upload_status["chat_history"])
        }

    except json.JSONDecodeError:
        upload_status["chat_history"].append({
            "question": body.question,
            "answer": response.text[:200],
            "files": filepaths
        })
        return {
            "direct_answer": "",
            "answer": response.text,
            "code_evidence": [],
            "confidence": "medium",
            "follow_up_questions": [],
            "files_used": filepaths,
            "chunks_retrieved": len(chunks),
            "total_files_in_repo": upload_status["total_files"],
            "total_chunks_in_repo": upload_status["total_chunks"],
            "git_available": False,
            "turn_number": len(upload_status["chat_history"])
        }

    except Exception as e:
        raise HTTPException(500, f"Gemini error: {str(e)}")





@app.get("/history")
def get_history():
    """Returns the full chat history for the current session."""
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")
    return {
        "history": upload_status.get("chat_history", []),
        "total_turns": len(upload_status.get("chat_history", []))
    }


@app.delete("/history")
def clear_history():
    """Clear chat history without re-uploading."""
    upload_status["chat_history"] = []
    return {"message": "Chat history cleared"}



class GithubRequest(BaseModel):
    url: str


@app.post("/upload/github")
async def upload_from_github(body: GithubRequest):
    """
    V3 endpoint — clone a public GitHub repo by URL.
    Runs full V2 pipeline PLUS git history analysis.

    Gives access to:
    - churn analysis (which files change most)
    - ownership detection (who owns each file)
    - coupling detection (files that break together)
    - risk ranking (riskiest files to modify)
    - smart reading order for new developers
    """
    url = body.url.strip()

    # Validate URL
    if not url.startswith("https://github.com/"):
        raise HTTPException(400, "Please provide a valid GitHub URL like https://github.com/user/repo")

    # Clean URL — remove trailing slash, .git suffix
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    clone_path = tempfile.mkdtemp(dir="D:\\tmp", prefix="v3_clone_")

    try:
        print(f"Cloning {url}...")
        import git as gitlib
        repo = gitlib.Repo.clone_from(url, clone_path, depth=300)
        print("Clone complete")

    except Exception as e:
        raise HTTPException(400, f"Could not clone repository: {str(e)}. Make sure it's a public GitHub repo.")

    try:
        # Read source files — same as ZIP upload
        files = {}
        for root, dirs, filenames in os.walk(clone_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, clone_path)
                if Path(rel_path).suffix.lower() in SKIP_EXTENSIONS:
                    continue
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if content.strip():
                        files[rel_path] = content
                except Exception:
                    continue

        if not files:
            raise HTTPException(400, "No readable files found in repository")

        # V2 pipeline — chunk + embed + store
        print(f"Chunking {len(files)} files...")
        chunks = chunk_all_files(files)
        print(f"Embedding {len(chunks)} chunks...")
        embedded_chunks = embed_chunks(chunks)
        reset_collection()
        save_chunks(embedded_chunks)

        # Dependency scan (free, instant)
        deps = scan_dependencies(files)

        # V3 — git history analysis
        print("Running git analysis...")
        git_data = analyze_git_repo(clone_path)

        # Update state
        upload_status.update({
            "uploaded": True,
            "total_files": len(files),
            "total_chunks": len(embedded_chunks),
            "file_list": sorted(files.keys()),
            "files_content": files,
            "dependencies": deps,
            "git_data": git_data,
            # Reset lazy features
            "summary": None,
            "security": None,
            "architecture": None,
            "diagram": None,
            "onboarding": None,
            "chat_history": [],
            "source": "github",
            "github_url": url,
        })

        # Build response
        repo_stats = git_data.get("repo_stats", {})

        return {
            "success": True,
            "source": "github",
            "url": url,
            "total_files": len(files),
            "total_chunks": len(embedded_chunks),
            "files": sorted(files.keys()),
            "dependencies": deps,
            "git_available": "error" not in git_data,
            "git_stats": repo_stats,
        }

    finally:
        shutil.rmtree(clone_path, ignore_errors=True)


# 4. Add these new git endpoints:

@app.get("/git/churn")
def get_churn():
    """Returns file churn data — which files change most often."""
    if not upload_status.get("git_data"):
        raise HTTPException(400, "No git data. Use /upload/github endpoint.")
    if "error" in upload_status["git_data"]:
        raise HTTPException(400, upload_status["git_data"]["error"])

    churn = upload_status["git_data"]["churn"]
    sorted_churn = sorted(
        [{"file": k, **v} for k, v in churn.items()],
        key=lambda x: x["churn_score"],
        reverse=True
    )
    return {
        "churn": sorted_churn[:30],
        "total_files_tracked": len(churn)
    }


@app.get("/git/ownership")
def get_ownership():
    """Returns file ownership — who owns each file."""
    if not upload_status.get("git_data"):
        raise HTTPException(400, "No git data. Use /upload/github endpoint.")

    if "error" in upload_status["git_data"]:
        raise HTTPException(400, upload_status["git_data"]["error"])

    ownership = upload_status["git_data"]["ownership"]
    return {
        "ownership": ownership,
        "total_files": len(ownership)
    }


@app.get("/git/coupling")
def get_coupling():
    """Returns file coupling — files that always change together."""
    if not upload_status.get("git_data"):
        raise HTTPException(400, "No git data. Use /upload/github endpoint.")

    if "error" in upload_status["git_data"]:
        raise HTTPException(400, upload_status["git_data"]["error"])

    return {
        "coupling": upload_status["git_data"]["coupling"],
        "insight": "Files that frequently change together are tightly coupled. Modifying one likely requires modifying the other."
    }


@app.get("/git/risk")
def get_risk():
    """Returns risk ranking — riskiest files to modify."""
    if not upload_status.get("git_data"):
        raise HTTPException(400, "No git data. Use /upload/github endpoint.")

    if "error" in upload_status["git_data"]:
        raise HTTPException(400, upload_status["git_data"]["error"])

    return {
        "risk_ranking": upload_status["git_data"]["risk_ranking"],
        "reading_order": upload_status["git_data"]["reading_order"],
        "repo_stats": upload_status["git_data"]["repo_stats"]
    }


@app.get("/git/summary")
def get_git_summary():
    """Returns a complete git intelligence summary."""
    if not upload_status.get("git_data"):
        raise HTTPException(400, "No git data. Use /upload/github endpoint.")

    gd = upload_status["git_data"]
    if "error" in gd:
        raise HTTPException(400, gd["error"])

    stats = gd["repo_stats"]
    risk = gd["risk_ranking"]
    reading = gd["reading_order"]
    coupling = gd["coupling"]

    high_risk = [r for r in risk if r["risk_level"] == "high"]
    medium_risk = [r for r in risk if r["risk_level"] == "medium"]

    return {
        "repo_stats": stats,
        "risk_summary": {
            "high_risk_files": high_risk[:5],
            "medium_risk_files": medium_risk[:5],
            "safest_files": risk[-5:][::-1] if len(risk) >= 5 else []
        },
        "reading_order": reading[:10],
        "top_coupling": coupling[:5],
        "key_insights": [
            f"Most active contributor: {stats.get('most_active_author', 'unknown')}",
            f"Analyzed {stats.get('total_commits_analyzed', 0)} commits across {stats.get('total_authors', 0)} authors",
            f"{len(high_risk)} high-risk files detected",
            f"Top coupled pair: {coupling[0]['file_a']} ↔ {coupling[0]['file_b']} ({coupling[0]['co_changes']} co-changes)" if coupling else "No strong coupling detected"
        ]
    }
@app.post("/restore")
def manual_restore():
    """
    Manually trigger session restore from ChromaDB.
    Useful if auto-restore didn't work.
    """
    restore_upload_status()
    return {
        "restored": upload_status["uploaded"],
        "total_files": upload_status["total_files"],
        "total_chunks": upload_status["total_chunks"],
        "message": "Session restored from ChromaDB" if upload_status["uploaded"] else "No data found in ChromaDB"
    }