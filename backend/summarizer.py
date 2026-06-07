import google.generativeai as genai
import json
import os


SUMMARY_FILES = [
    "readme.md", "readme.rst", "readme.txt",
    "package.json", "requirements.txt", "pyproject.toml",
    "pom.xml", "go.mod", "gemfile", "cargo.toml",
    "docker-compose.yml", "dockerfile",
    "main.py", "app.py", "index.js", "server.js",
    "manage.py", "settings.py"
]


def get_summary_context(files: dict) -> str:
    """
    Pick only the most useful files for generating a summary.
    Don't send everything — just structural/config files.
    """
    context = ""
    selected = []

    for filepath, content in files.items():
        filename = filepath.split("\\")[-1].split("/")[-1].lower()
        if filename in SUMMARY_FILES:
            selected.append((filepath, content))

    # Sort — README first, then config files
    selected.sort(key=lambda x: (
        0 if "readme" in x[0].lower() else
        1 if "package.json" in x[0].lower() else
        2 if "requirements" in x[0].lower() else 3
    ))

    # Build context string, cap at 8000 chars so Gemini stays fast
    for filepath, content in selected:
        chunk = f"\n\n--- {filepath} ---\n{content}"
        if len(context) + len(chunk) > 8000:
            break
        context += chunk

    return context


def generate_repo_summary(files: dict) -> dict:
    """
    Automatically generate a structured summary of the repo.
    Called once after upload completes.
    Returns a dict with tech stack, architecture, features, entry points.
    """
    context = get_summary_context(files)

    # Debug — print first 5 file paths to see their format
    print("Sample file paths:")
    for fp in list(files.keys())[:5]:
        print(f"  '{fp}'")
    print(f"Context length: {len(context)}")
    print(f"Summary context length: {len(context)} chars")
    print(f"Context preview: {context[:200]}")
    if not context:
        return {
            "tech_stack": {},
            "architecture": "Could not determine architecture",
            "main_features": [],
            "entry_points": [],
            "summary": "No README or config files found"
        }

    prompt = f"""Analyze this repository and return a structured summary.

REPOSITORY FILES:
{context}

Return valid JSON in exactly this format:
{{
    "project_name": "name of the project",
    "one_liner": "one sentence description of what this project does",
    "tech_stack": {{
        "frontend": ["React", "Tailwind"],
        "backend": ["FastAPI", "Python"],
        "database": ["PostgreSQL"],
        "authentication": ["JWT"],
        "deployment": ["Docker"],
        "other": ["Redis"]
    }},
    "architecture": "2-3 sentence description of the overall architecture and how components connect",
    "main_features": ["feature 1", "feature 2", "feature 3"],
    "entry_points": [
        {{"file": "main.py", "role": "FastAPI application entry point"}},
        {{"file": "src/index.js", "role": "React frontend entry point"}}
    ],
    "recommended_reading_order": [
        {{"file": "README.md", "reason": "Start here for overview"}},
        {{"file": "main.py", "reason": "Understand backend structure"}}
    ],
    "complexity": "simple/moderate/complex",
    "for_beginners": "one tip for someone new to this codebase"
}}

Rules:
- Only include tech that you can actually see evidence of in the files
- If a category has nothing, use empty array []
- Return only valid JSON, no markdown backticks"""

    try:
        gemini = genai.GenerativeModel("gemini-2.0-flash")
        response = gemini.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except Exception as e:
       import traceback
       print(f"Summary generation failed: {e}")
       traceback.print_exc()   
       return {
            "project_name": "Unknown",
            "one_liner": "Could not generate summary",
            "tech_stack": {},
            "architecture": "Could not determine",
            "main_features": [],
            "entry_points": [],
            "complexity": "unknown",
            "for_beginners": ""
        }