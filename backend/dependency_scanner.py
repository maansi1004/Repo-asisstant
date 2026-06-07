import json
import re
from pathlib import Path


# Known package → category + display name mapping
PACKAGE_MAP = {
    # Frontend frameworks
    "react": ("frontend", "React"),
    "next": ("frontend", "Next.js"),
    "vue": ("frontend", "Vue.js"),
    "nuxt": ("frontend", "Nuxt.js"),
    "svelte": ("frontend", "Svelte"),
    "angular": ("frontend", "Angular"),
    "vite": ("frontend", "Vite"),

    # CSS / UI
    "tailwindcss": ("ui", "Tailwind CSS"),
    "bootstrap": ("ui", "Bootstrap"),
    "chakra-ui": ("ui", "Chakra UI"),
    "material-ui": ("ui", "Material UI"),
    "@mui/material": ("ui", "Material UI"),
    "shadcn": ("ui", "shadcn/ui"),
    "antd": ("ui", "Ant Design"),

    # Backend frameworks
    "express": ("backend", "Express.js"),
    "fastapi": ("backend", "FastAPI"),
    "django": ("backend", "Django"),
    "flask": ("backend", "Flask"),
    "spring-boot": ("backend", "Spring Boot"),
    "rails": ("backend", "Ruby on Rails"),
    "nestjs": ("backend", "NestJS"),
    "@nestjs/core": ("backend", "NestJS"),
    "koa": ("backend", "Koa.js"),
    "hono": ("backend", "Hono"),

    # Databases
    "mongoose": ("database", "MongoDB (Mongoose)"),
    "mongodb": ("database", "MongoDB"),
    "mysql2": ("database", "MySQL"),
    "pg": ("database", "PostgreSQL"),
    "prisma": ("database", "Prisma ORM"),
    "@prisma/client": ("database", "Prisma ORM"),
    "sequelize": ("database", "Sequelize ORM"),
    "sqlalchemy": ("database", "SQLAlchemy"),
    "redis": ("database", "Redis"),
    "ioredis": ("database", "Redis"),
    "firebase": ("database", "Firebase"),
    "firebase-admin": ("database", "Firebase Admin"),
    "supabase": ("database", "Supabase"),
    "@supabase/supabase-js": ("database", "Supabase"),

    # Auth
    "jsonwebtoken": ("auth", "JWT"),
    "passport": ("auth", "Passport.js"),
    "bcrypt": ("auth", "bcrypt"),
    "bcryptjs": ("auth", "bcrypt"),
    "next-auth": ("auth", "NextAuth.js"),
    "clerk": ("auth", "Clerk"),

    # Real-time
    "socket.io": ("realtime", "Socket.IO"),
    "ws": ("realtime", "WebSockets"),

    # AI / ML
    "openai": ("ai", "OpenAI"),
    "anthropic": ("ai", "Anthropic Claude"),
    "langchain": ("ai", "LangChain"),
    "transformers": ("ai", "HuggingFace Transformers"),
    "torch": ("ai", "PyTorch"),
    "tensorflow": ("ai", "TensorFlow"),
    "groq": ("ai", "Groq"),
    "google-generativeai": ("ai", "Google Gemini"),

    # Testing
    "jest": ("testing", "Jest"),
    "pytest": ("testing", "Pytest"),
    "mocha": ("testing", "Mocha"),
    "cypress": ("testing", "Cypress"),
    "playwright": ("testing", "Playwright"),
    "vitest": ("testing", "Vitest"),

    # DevOps / deployment
    "docker": ("devops", "Docker"),
    "dotenv": ("config", "dotenv"),
    "python-dotenv": ("config", "dotenv"),
}

# File-based detection (presence of file = technology detected)
FILE_SIGNALS = {
    "docker-compose.yml": ("devops", "Docker Compose"),
    "dockerfile": ("devops", "Docker"),
    ".github/workflows": ("devops", "GitHub Actions"),
    "kubernetes": ("devops", "Kubernetes"),
    "terraform": ("devops", "Terraform"),
    "vercel.json": ("deployment", "Vercel"),
    "netlify.toml": ("deployment", "Netlify"),
    "railway.json": ("deployment", "Railway"),
    "render.yaml": ("deployment", "Render"),
    "tailwind.config.js": ("ui", "Tailwind CSS"),
    "tailwind.config.ts": ("ui", "Tailwind CSS"),
    "prisma/schema.prisma": ("database", "Prisma ORM"),
    ".eslintrc": ("tooling", "ESLint"),
    "jest.config.js": ("testing", "Jest"),
    "vite.config.js": ("frontend", "Vite"),
    "vite.config.ts": ("frontend", "Vite"),
    "next.config.js": ("frontend", "Next.js"),
    "next.config.ts": ("frontend", "Next.js"),
}


def scan_package_json(content: str) -> list[tuple]:
    """Extract dependencies from package.json"""
    found = []
    try:
        data = json.loads(content)
        all_deps = {}
        all_deps.update(data.get("dependencies", {}))
        all_deps.update(data.get("devDependencies", {}))

        for pkg_name in all_deps:
            pkg_lower = pkg_name.lower()
            if pkg_lower in PACKAGE_MAP:
                found.append(PACKAGE_MAP[pkg_lower])
            # Partial match for scoped packages like @nestjs/core
            for known_pkg, info in PACKAGE_MAP.items():
                if known_pkg in pkg_lower and info not in found:
                    found.append(info)
    except Exception:
        pass
    return found


def scan_requirements_txt(content: str) -> list[tuple]:
    """Extract dependencies from requirements.txt"""
    found = []
    for line in content.splitlines():
        line = line.strip().lower()
        # Remove version specifiers: flask==2.0.0 → flask
        pkg = re.split(r"[>=<!]", line)[0].strip()
        if pkg in PACKAGE_MAP:
            found.append(PACKAGE_MAP[pkg])
    return found


def scan_pyproject_toml(content: str) -> list[tuple]:
    """Extract dependencies from pyproject.toml"""
    found = []
    for line in content.splitlines():
        line = line.strip().lower()
        for pkg, info in PACKAGE_MAP.items():
            if pkg in line and info not in found:
                found.append(info)
    return found


def scan_pom_xml(content: str) -> list[tuple]:
    """Extract dependencies from Maven pom.xml"""
    found = []
    content_lower = content.lower()
    for pkg, info in PACKAGE_MAP.items():
        if pkg in content_lower and info not in found:
            found.append(info)
    return found


def scan_files_for_signals(files: dict) -> list[tuple]:
    """Detect technologies from file presence alone"""
    found = []
    for filepath in files.keys():
        filepath_lower = filepath.lower().replace("\\", "/")
        for signal, info in FILE_SIGNALS.items():
            if signal in filepath_lower and info not in found:
                found.append(info)
    return found


def scan_dependencies(files: dict) -> dict:
    """
    Main function — scans all relevant files and returns
    a structured dependency report grouped by category.
    """
    all_found = []

    for filepath, content in files.items():
        filename = filepath.replace("\\", "/").split("/")[-1].lower()

        if filename == "package.json":
            all_found.extend(scan_package_json(content))
        elif filename == "requirements.txt":
            all_found.extend(scan_requirements_txt(content))
        elif filename == "pyproject.toml":
            all_found.extend(scan_pyproject_toml(content))
        elif filename == "pom.xml":
            all_found.extend(scan_pom_xml(content))

    # File-based signals
    all_found.extend(scan_files_for_signals(files))

    # Deduplicate and group by category
    seen = set()
    grouped = {}
    for category, name in all_found:
        if name not in seen:
            seen.add(name)
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(name)

    return {
        "dependencies": grouped,
        "total_detected": len(seen),
        "categories_found": list(grouped.keys())
    }