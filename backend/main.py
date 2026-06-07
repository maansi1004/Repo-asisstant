import os
import zipfile
import tempfile
import shutil
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, dependencies, security
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from importlib_resources import files
from pydantic import BaseModel
from summarizer import generate_repo_summary
from onboarding import generate_onboarding
from security_scanner import scan_security 
from architect import generate_architecture, generate_mermaid_diagram


import google.generativeai as genai
from dotenv import load_dotenv
from chunker import chunk_all_files
from embedder import embed_chunks
from store import save_chunks, reset_collection, get_all_chunks
from retriever import retrieve, format_context
from dependency_scanner import scan_dependencies
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

SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".next"}
SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf",
                   ".zip", ".tar", ".gz", ".mp4", ".mp3", ".woff", ".woff2",
                   ".ttf", ".eot", ".lock", ".pyc"}

# Track upload status in memory (just metadata, not file contents like V1)
upload_status = {"total_files": 0, "total_chunks": 0, "uploaded": False, "summary": None, "dependencies": None, "onboarding": None,"security": None, "diagram": None}


def read_files_from_zip(zip_path: str, extract_to: str) -> dict:
    """Extract zip and read all readable text files. Same as V1."""
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
    Upload flow:
    1. Extract zip
    2. Read all files
    3. Chunk by function boundary
    4. Embed each chunk
    5. Store in ChromaDB
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Please upload a .zip file")

    # tmp_dir = tempfile.mkdtemp()
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

        # Step 2: chunk all files
        print(f"Chunking {len(files)} files...")
        chunks = chunk_all_files(files)
        print(f"Created {len(chunks)} chunks")

        # Step 3: embed all chunks
        print("Embedding chunks (this takes 1-2 minutes for large repos)...")
        embedded_chunks = embed_chunks(chunks)
        print(f"Embedded {len(embedded_chunks)} chunks")

        # Step 4: reset old data and save new chunks
        reset_collection()
        save_chunks(embedded_chunks)
        # Step 5: auto generate repo summary
        print("Generating repo summary...")
        summary = generate_repo_summary(files)
           # Step 6: scan dependencies
        print("Scanning dependencies...")
        deps = scan_dependencies(files)
        upload_status["dependencies"] = deps
        print(f"Found {deps['total_detected']} dependencies")

        upload_status["summary"] = summary
        print(f"Summary generated: {summary.get('project_name', 'Unknown')}")

        upload_status["total_files"] = len(files)
        upload_status["total_chunks"] = len(embedded_chunks)
        upload_status["uploaded"] = True
        # Step 8: generate onboarding guide
        print("Generating onboarding guide...")
        onboarding = generate_onboarding(
        summary,
        deps,
        sorted(files.keys())
         )
        upload_status["onboarding"] = onboarding
        print("Onboarding guide generated")
        # Step 9: security scan
        print("Running security scan...")
        security_report = scan_security(files)
        upload_status["security"] = security_report
        print(f"Security scan done — score: {security_report['score']}/10, issues: {security_report['total_issues']}")
        # Generate Mermaid diagram
        print("Generating architecture diagram...")
        diagram = generate_mermaid_diagram(summary, deps, sorted(files.keys()))
        upload_status["diagram"] = diagram
        print("Diagram generated")
        return {
            "success": True,
            "total_files": len(files),
            "total_chunks": len(embedded_chunks),
            "files": sorted(files.keys()),
            "summary": summary,
            "onboarding": onboarding,
            "security": security_report,
            "diagram": diagram
        }

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
async def ask_question(body: QuestionRequest):
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet. Please upload a zip first.")

    if not body.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    chunks = retrieve(body.question)
    if not chunks:
        raise HTTPException(500, "Could not retrieve relevant chunks. Try re-uploading the repo.")

    context, filepaths = format_context(chunks)

    prompt = f"""You are a senior software engineer doing a deep code review.

CODEBASE CONTEXT:
{context}

QUESTION: {body.question}

Return your response as valid JSON in exactly this format:
{{
    "direct_answer": "one sentence direct answer with exact file and function names",
    "explanation": "detailed step by step explanation of the actual code flow referencing specific functions",
    "code_evidence": ["code snippet 1 with filepath", "code snippet 2 with filepath"],
    "confidence": "high/medium/low",
    "follow_up_questions": ["specific follow-up question 1", "specific follow-up question 2"]
}}

STRICT RULES:
- Only reference code literally shown above
- Never make up function names or file paths
- Quote actual code snippets for evidence
- Return only valid JSON, no markdown backticks"""

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
        return {
            "direct_answer": structured.get("direct_answer", ""),
            "answer": structured.get("explanation", raw),
            "code_evidence": structured.get("code_evidence", []),
            "confidence": structured.get("confidence", "medium"),
            "follow_up_questions": structured.get("follow_up_questions", []),
            "files_used": filepaths,
            "chunks_retrieved": len(chunks),
            "total_files_in_repo": upload_status["total_files"],
            "total_chunks_in_repo": upload_status["total_chunks"]
        }

    except json.JSONDecodeError:
        return {
            "direct_answer": "",
            "answer": response.text,
            "code_evidence": [],
            "confidence": "medium",
            "follow_up_questions": [],
            "files_used": filepaths,
            "chunks_retrieved": len(chunks),
            "total_files_in_repo": upload_status["total_files"],
            "total_chunks_in_repo": upload_status["total_chunks"]
        }

    except Exception as e:
        raise HTTPException(500, f"Gemini API error: {str(e)}")

@app.get("/status")
def status():
    return {
        "repo_loaded": upload_status["uploaded"],
        "total_files": upload_status["total_files"],
        "total_chunks": upload_status["total_chunks"]
    }

@app.get("/explain")
async def explain_file(filepath: str):
    chunks = get_all_chunks()

    
    # Normalize path separators for matching
    normalized_input = filepath.replace("\\\\", "\\").replace("/", "\\")

    file_chunks = [
        c for c in chunks
        if c["metadata"]["filepath"].replace("/", "\\") == normalized_input
    ]

    if not file_chunks:
        # Show available files to help debug
        available = sorted(set(c["metadata"]["filepath"] for c in chunks))
        raise HTTPException(404, {
            "error": f"File '{filepath}' not found",
            "available_files": available[:10]
        })

    file_content = "\n\n".join([c["text"] for c in file_chunks])


    prompt = f"""Analyze this file completely:

{file_content}

Return as JSON:
{{
    "purpose": "what this file does and why it exists",
    "functions": [{{"name": "funcName", "description": "what it does"}}],
    "dependencies": ["import and why"],
    "connections": "how this file connects to rest of codebase",
    "complexity": 7,
    "complexity_reason": "why this complexity rating"
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
        return {
            "filepath": filepath,
            "chunks_analyzed": len(file_chunks),
            **structured
        }

    except json.JSONDecodeError:
        return {
            "filepath": filepath,
            "chunks_analyzed": len(file_chunks),
            "explanation": response.text
        }

    except Exception as e:
        raise HTTPException(500, f"Gemini error: {str(e)}")
        
@app.get("/summary")
def get_summary():
    """
    Returns the auto-generated repo summary.
    Available immediately after upload.
    """
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")
    
    if not upload_status["summary"]:
        raise HTTPException(404, "Summary not generated yet. Try re-uploading.")
    
    return upload_status["summary"] 
@app.get("/dependencies")
def get_dependencies():
    """
    Returns rule-based dependency scan results.
    Fast, accurate, no LLM needed.
    """
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    if not upload_status["dependencies"]:
        raise HTTPException(404, "Dependencies not scanned yet.")

    return upload_status["dependencies"]
@app.get("/onboard")
def get_onboarding():
    """
    Returns structured onboarding guide for new developers.
    Includes learning path, key files, prerequisites, first tasks.
    """
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    if not upload_status["onboarding"]:
        raise HTTPException(404, "Onboarding guide not generated yet.")

    return upload_status["onboarding"] 
class OnboardingQuestion(BaseModel):
    question: str
    experience_level: str = "beginner"  # beginner / intermediate / senior


@app.post("/onboard/ask")
async def onboard_ask(body: OnboardingQuestion):
    """
    Answer specific onboarding questions with experience-level context.
    Examples:
    - 'How do I add a new API endpoint?'
    - 'Where should I add a new React component?'
    - 'How does authentication work here?'
    """
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")

    # Retrieve relevant chunks
    chunks = retrieve(body.question)
    if not chunks:
        raise HTTPException(500, "Could not retrieve relevant code.")

    context, filepaths = format_context(chunks)

    # Add onboarding context if available
    onboard_context = ""
    if upload_status["onboarding"]:
        ob = upload_status["onboarding"]
        onboard_context = f"""
Project summary: {upload_status['summary'].get('one_liner', '')}
Key files: {[f['file'] for f in ob.get('key_files_to_read', [])[:3]]}
"""

    prompt = f"""You are a senior engineer helping a {body.experience_level} developer understand a codebase.

ONBOARDING CONTEXT:
{onboard_context}

RELEVANT CODE:
{context}

QUESTION: {body.question}

Return valid JSON:
{{
    "answer": "clear explanation tailored for a {body.experience_level}",
    "relevant_files": ["file1", "file2"],
    "next_steps": ["what to do after understanding this", "related thing to explore"],
    "code_example": "relevant code snippet if helpful, empty string if not",
    "simpler_explanation": "one sentence ELI5 explanation"
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
        return {
            **structured,
            "files_searched": filepaths,
            "experience_level": body.experience_level
        }

    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")
    
@app.get("/security")
def get_security():
    """
    Returns security scan results.
    Rule-based — instant, no LLM needed.
    """
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")
    if not upload_status["security"]:
        raise HTTPException(404, "Security scan not run yet.")
    return upload_status["security"]
@app.get("/diagram")
def get_diagram():
    if not upload_status["uploaded"]:
        raise HTTPException(400, "No repo uploaded yet.")
    if not upload_status["diagram"]:
        raise HTTPException(404, "Diagram not generated yet.")
    return upload_status["diagram"]