import json
import google.generativeai as genai


def generate_onboarding(
    summary: dict,
    dependencies: dict,
    files: list[str]
) -> dict:
    """
    Generate a structured onboarding guide for a new developer.
    Uses summary + deps + file list — no extra file reading.
    """

    tech = dependencies.get("dependencies", {})
    project_name = summary.get("project_name", "this project")
    architecture = summary.get("architecture", "")
    features = summary.get("main_features", [])
    entry_points = summary.get("entry_points", [])
    complexity = summary.get("complexity", "moderate")
    for_beginners = summary.get("for_beginners", "")

    # Build file tree summary — group by folder
    folder_map = {}
    for fp in files:
        parts = fp.replace("\\", "/").split("/")
        if len(parts) > 1:
            folder = parts[0] + "/" + parts[1] if len(parts) > 2 else parts[0]
        else:
            folder = "root"
        if folder not in folder_map:
            folder_map[folder] = []
        folder_map[folder].append(parts[-1])

    folder_summary = "\n".join(
        f"{folder}/: {', '.join(fnames[:5])}"
        for folder, fnames in list(folder_map.items())[:15]
    )

    context = f"""
Project: {project_name}
Complexity: {complexity}
Architecture: {architecture}

Tech Stack:
{json.dumps(tech, indent=2)}

Main Features:
{chr(10).join(f'- {f}' for f in features)}

Entry Points:
{json.dumps(entry_points, indent=2)}

Folder Structure:
{folder_summary}

Beginner Tip from README:
{for_beginners}
"""

    prompt = f"""You are a senior engineer onboarding a new developer to a codebase.

PROJECT CONTEXT:
{context}

Create a detailed onboarding guide. Return valid JSON in exactly this format:
{{
    "welcome_message": "Friendly 2-sentence welcome explaining what this project does",
    "prerequisites": [
        {{"skill": "Node.js basics", "why": "The backend is built with Express.js"}},
        {{"skill": "React fundamentals", "why": "Frontend uses React/Next.js"}}
    ],
    "learning_path": [
        {{
            "day": 1,
            "title": "Understand the project",
            "tasks": [
                {{"action": "Read README.md", "reason": "Get the full picture before touching code"}},
                {{"action": "Run the project locally", "reason": "See it working before reading code"}}
            ]
        }},
        {{
            "day": 2,
            "title": "Explore the backend",
            "tasks": [
                {{"action": "Read server.js or main entry file", "reason": "Understand how the server starts"}},
                {{"action": "Trace one API endpoint end to end", "reason": "See route → controller → database pattern"}}
            ]
        }},
        {{
            "day": 3,
            "title": "Explore the frontend",
            "tasks": []
        }},
        {{
            "day": 4,
            "title": "Make your first contribution",
            "tasks": []
        }}
    ],
    "key_files_to_read": [
        {{
            "file": "README.md",
            "priority": 1,
            "reason": "Project overview and setup instructions",
            "time_needed": "15 minutes"
        }},
        {{
            "file": "server/index.js",
            "priority": 2,
            "reason": "Backend entry point — understand server setup",
            "time_needed": "20 minutes"
        }}
    ],
    "concepts_to_understand": [
        {{"concept": "REST API", "why_needed": "All client-server communication uses REST"}},
        {{"concept": "JWT Authentication", "why_needed": "Used for user sessions throughout the app"}}
    ],
    "first_task_suggestion": "Specific actionable first task a new dev could do to get familiar",
    "common_pitfalls": [
        "Common mistake 1 new devs make in this codebase",
        "Common mistake 2"
    ],
    "useful_commands": [
        {{"command": "npm install", "description": "Install dependencies"}},
        {{"command": "npm run dev", "description": "Start development server"}}
    ]
}}

Rules:
- Be specific to THIS project, not generic advice
- Reference actual file names and folder structure shown above
- Learning path should be realistic — 4 days for moderate complexity
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
        traceback.print_exc()
        return {
            "welcome_message": f"Welcome to {project_name}!",
            "prerequisites": [],
            "learning_path": [],
            "key_files_to_read": [],
            "concepts_to_understand": [],
            "first_task_suggestion": "Start by reading the README",
            "common_pitfalls": [],
            "useful_commands": [],
            "error": str(e)
        }