import json
import google.generativeai as genai


def generate_architecture(summary: dict, dependencies: dict) -> dict:
    """
    Generate architecture overview using summary + deps.
    No extra file reading needed.
    """
    tech = dependencies.get("dependencies", {})
    features = summary.get("main_features", [])
    architecture_desc = summary.get("architecture", "")
    project_name = summary.get("project_name", "This project")

    context = f"""
Project: {project_name}
One liner: {summary.get('one_liner', '')}
Architecture: {architecture_desc}

Tech Stack:
{json.dumps(tech, indent=2)}

Main Features:
{chr(10).join(f'- {f}' for f in features)}
"""

    prompt = f"""You are a software architect. Based on this project information, generate a clear architecture summary.

PROJECT INFO:
{context}

Return valid JSON:
{{
    "layers": [
        {{
            "name": "Frontend",
            "technologies": ["React", "Next.js"],
            "responsibility": "User interface and client-side logic"
        }}
    ],
    "external_services": ["Firebase Auth", "Socket.IO"],
    "data_flow": "Step by step explanation of how data flows from user to database",
    "key_patterns": ["REST API", "MVC"],
    "diagram_explanation": "Plain English 2-3 sentence architecture explanation"
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
        return json.loads(raw.strip())
    except Exception as e:
        return {
            "layers": [],
            "external_services": [],
            "data_flow": "Could not determine",
            "key_patterns": [],
            "diagram_explanation": f"Error: {str(e)}"
        }


def generate_mermaid_diagram(
    summary: dict,
    dependencies: dict,
    files: list
) -> dict:
    """
    Generate a GitDiagram-style Mermaid diagram with:
    - Actual filenames in nodes
    - Subgraphs grouped by layer
    - Labeled relationship arrows
    """
    tech = dependencies.get("dependencies", {})
    project_name = summary.get("project_name", "Project")
    architecture = summary.get("architecture", "")

    # Build detailed folder -> files map
    folder_map = {}
    for fp in files:
        parts = fp.replace("\\", "/").split("/")
        # Skip the repo root folder (first part is usually repo name)
        if len(parts) >= 2:
            folder = parts[1]
        else:
            folder = "root"

        if folder not in folder_map:
            folder_map[folder] = []
        folder_map[folder].append(parts[-1])

    # Build file tree string — show up to 8 files per folder
    file_tree = ""
    for folder, filenames in list(folder_map.items())[:15]:
        file_tree += f"\n{folder}/\n"
        for fname in filenames[:8]:
            file_tree += f"  {fname}\n"

    prompt = f"""You are a software architect creating a clean system diagram.

PROJECT: {project_name}
ARCHITECTURE: {architecture}

TECH STACK:
{json.dumps(tech, indent=2)}

FILE STRUCTURE:
{file_tree}

Generate a clean Mermaid diagram. Follow these rules STRICTLY:

LAYOUT RULES:
- Use graph LR (left to right) NOT top-down
- Maximum 3 subgraphs
- Maximum 15 nodes total
- Each subgraph max 5 nodes
- Only draw arrows between SUBGRAPHS not between every single node
- Use one representative node per layer to connect layers

GOOD EXAMPLE FORMAT:
graph LR
    subgraph Frontend
        A["App Shell\\n[index.html]"]
        B["Events Page\\n[events.html]"]
        C["Dashboard\\n[dashboard.html]"]
    end
    subgraph Backend
        D["Auth Controller\\n[authController.js]"]
        E["Event Controller\\n[eventController.js]"]
        F["DB Connector\\n[db.js]"]
    end
    subgraph Database
        G[("MySQL DB\\n[DB Instance]")]
    end
    A -->|hosts| B
    A -->|hosts| C
    B -->|calls| D
    C -->|calls| E
    D -->|queries| F
    E -->|queries| F
    F -->|connects| G

Return valid JSON:
{{
    "mermaid_code": "your clean diagram here",
    "description": "plain english description"
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

        result = json.loads(raw)

        # Validate mermaid code exists
        if "mermaid_code" not in result or not result["mermaid_code"]:
            raise ValueError("No mermaid_code in response")

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return a valid fallback diagram
        return {
            "mermaid_code": f"""graph TD
    subgraph Frontend
        A["{project_name} Frontend"]
    end
    subgraph Backend
        B["Backend API"]
    end
    subgraph Database
        C[("Database")]
    end
    A -->|calls| B
    B -->|queries| C""",
            "description": f"Basic architecture diagram. Full generation failed: {str(e)}"
        }
