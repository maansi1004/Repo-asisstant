# Repo Intelligence Platform

An AI-powered code intelligence platform that analyzes any GitHub repository and answers natural language questions about it.

## Features

- **Semantic Q&A** — Ask anything about a codebase, get answers with exact file references
- **Auto Repository Summary** — Instantly detects tech stack, architecture, main features
- **Architecture Diagram** — Generates GitDiagram-style visual diagrams with actual filenames
- **Security Scanner** — Detects hardcoded secrets, SQL injection risks, missing .env files
- **Dependency Scanner** — Rule-based detection of 50+ frameworks and libraries
- **Onboarding Assistant** — Creates learning paths for new developers
- **File Deep Explain** — Detailed breakdown of any file's purpose and connections

## Tech Stack

- **Backend** — FastAPI (Python)
- **LLM** — Google Gemini 2.5 Flash
- **Embeddings** — Sentence Transformers (all-MiniLM-L6-v2)
- **Vector DB** — ChromaDB
- **Frontend** — React + Vite
- **Diagram** — Mermaid.js

## Architecture
ZIP Upload → File Extraction → Smart Chunking (by function boundary)
→ Embedding (local, no API) → ChromaDB Storage
→ Semantic Search (hybrid: vector + keyword) → Gemini Answer

## Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend/frontend
npm install
npm run dev
```

Open `http://localhost:5173`

## How to use

1. Go to any GitHub repo → Code → Download ZIP
2. Upload the ZIP in the app
3. Ask questions like:
   - "Where is authentication handled?"
   - "What are the main modules?"
   - "Which files are security risks?"
   - "What should a new developer read first?"