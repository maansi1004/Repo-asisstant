import os
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from itertools import combinations
import math

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3",
    ".woff", ".woff2", ".ttf", ".eot", ".lock",
    ".pyc", ".exe", ".dll", ".bin"
}

# Files that are NOT real code — cap their risk and exclude from reading order
LOW_RISK_EXTENSIONS = {".md", ".rst", ".txt", ".yaml", ".yml", ".toml"}
LOW_RISK_FILENAMES = {
    "security.md", "changelog.md", "license.md", "contributing.md",
    "readme.md", "announcement.md", "code_of_conduct.md",
    "package-lock.json", "yarn.lock", ".gitignore",
    ".env.example", ".env.sample", "bug_report.yml",
    "bug-report.md", "feature-request.md", "document-update.md",
    "other-issues.md", "requirements.txt", "package.json",
    "package-lock.json"
}

# Skip these in git analysis entirely — IDE / CI noise
SKIP_DIRS_GIT = {
    ".idea", ".vscode", ".github", "node_modules",
    "__pycache__", ".git", "venv", ".venv"
}

# Files worth reading as a new developer — actual code entry points
GOOD_READING_FILES = {
    "main.py": 100, "app.py": 100, "server.js": 100,
    "index.js": 95, "index.ts": 95, "app.js": 90,
    "app.ts": 90, "main.go": 90, "main.rs": 90,
    "manage.py": 85, "wsgi.py": 80, "asgi.py": 80,
    "routes.py": 75, "urls.py": 75, "router.js": 75,
    "router.ts": 75, "controllers": 70, "views.py": 70,
    "models.py": 70, "schema.py": 70, "db.js": 65,
    "db.py": 65, "database.py": 65, "config.py": 60,
    "settings.py": 60, "auth.py": 55, "middleware.py": 55,
}

MAX_COMMITS = 300


def is_code_file(filepath: str) -> bool:
    ext = Path(filepath).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return False
    parts = filepath.replace("\\", "/").split("/")
    if any(s in parts for s in SKIP_DIRS_GIT):
        return False
    return True


def is_low_risk_file(filepath: str) -> bool:
    ext = Path(filepath).suffix.lower()
    filename = Path(filepath).name.lower()
    return ext in LOW_RISK_EXTENSIONS or filename in LOW_RISK_FILENAMES


def is_good_reading_file(filepath: str) -> bool:
    """Returns true for files worth reading as a new developer."""
    filename = Path(filepath).name.lower()
    return filename in GOOD_READING_FILES or filename not in LOW_RISK_FILENAMES


def analyze_git_repo(repo_path: str) -> dict:
    if not GIT_AVAILABLE:
        return {"error": "gitpython not installed. Run: pip install gitpython"}

    try:
        repo = git.Repo(repo_path)
    except git.InvalidGitRepositoryError:
        return {"error": "No .git folder found. Use GitHub URL input for V3 features."}
    except Exception as e:
        return {"error": f"Could not open repo: {str(e)}"}

    print(f"Analyzing git history (max {MAX_COMMITS} commits)...")
    commits = list(repo.iter_commits(max_count=MAX_COMMITS))
    if not commits:
        return {"error": "No commits found in repository"}

    print(f"Found {len(commits)} commits")

    file_commits = defaultdict(list)
    file_authors = defaultdict(lambda: defaultdict(int))
    file_dates = defaultdict(list)
    co_changes = defaultdict(int)
    author_total = defaultdict(int)
    all_authors = set()

    for commit in commits:
        author = commit.author.name or "Unknown"
        all_authors.add(author)
        author_total[author] += 1

        try:
            changed_files = [
                f for f in commit.stats.files.keys()
                if is_code_file(f)
            ]
        except Exception:
            continue

        commit_date = datetime.fromtimestamp(
            commit.committed_date, tz=timezone.utc
        )

        for filepath in changed_files:
            file_commits[filepath].append(commit.hexsha[:8])
            file_authors[filepath][author] += 1
            file_dates[filepath].append(commit_date)

        if len(changed_files) >= 2:
            for file_a, file_b in combinations(sorted(changed_files), 2):
                co_changes[(file_a, file_b)] += 1

    # ── Churn ──────────────────────────────────────────────────

    now = datetime.now(tz=timezone.utc)
    churn = {}

    for filepath, commit_list in file_commits.items():
        dates = file_dates[filepath]
        if not dates:
            continue

        first_date = min(dates)
        last_date = max(dates)
        # Minimum 7 days to avoid single-day burst inflation
        days_active = max((last_date - first_date).days, 7)
        days_since_last = (now - last_date).days
        commit_count = len(commit_list)

        recency_weight = max(0.1, 1 - (days_since_last / 365))
        churn_score = round((commit_count / (days_active / 7)) * recency_weight, 2)

        churn[filepath] = {
            "commits": commit_count,
            "churn_score": churn_score,
            "days_active": days_active,
            "days_since_last_change": days_since_last,
            "last_modified": last_date.strftime("%Y-%m-%d"),
            "first_modified": first_date.strftime("%Y-%m-%d"),
            "is_config_file": is_low_risk_file(filepath)
        }

    # ── Ownership ──────────────────────────────────────────────

    ownership = {}

    for filepath, authors in file_authors.items():
        total = sum(authors.values())
        if total == 0:
            continue

        top_author = max(authors, key=authors.get)
        top_count = authors[top_author]
        ownership_pct = round(top_count / total * 100, 1)
        num_authors = len(authors)

        if num_authors == 1:
            ownership_status = "sole_owner"
            is_shared = False
        elif ownership_pct >= 75:
            ownership_status = "clear_owner"
            is_shared = False
        elif ownership_pct >= 50:
            ownership_status = "primary_owner"
            is_shared = False
        else:
            ownership_status = "shared"
            is_shared = True

        ownership[filepath] = {
            "owner": top_author,
            "ownership_percent": ownership_pct,
            "ownership_status": ownership_status,
            "is_shared": is_shared,
            "total_commits": total,
            "num_authors": num_authors,
            "all_authors": dict(sorted(
                authors.items(), key=lambda x: x[1], reverse=True
            )),
        }

    # ── Coupling ───────────────────────────────────────────────

    total_commits = len(commits)

    file_coupling_count = defaultdict(set)
    for (file_a, file_b), count in co_changes.items():
        if count >= 2:
            file_coupling_count[file_a].add(file_b)
            file_coupling_count[file_b].add(file_a)

    coupling_list = []
    for (file_a, file_b), count in co_changes.items():
        if count < 2:
            continue
        strength = round(count / total_commits * 100, 1)
        coupling_list.append({
            "file_a": file_a,
            "file_b": file_b,
            "co_changes": count,
            "strength_percent": strength,
            "label": "tight" if strength > 10 else "moderate" if strength > 5 else "loose"
        })

    coupling_list.sort(key=lambda x: x["co_changes"], reverse=True)

    # ── Risk scoring — calibrated thresholds ───────────────────

    # First pass: compute raw scores to find distribution
    raw_scores = []
    file_risk_data = []

    for filepath in file_commits:
        if filepath not in churn:
            continue

        c = churn[filepath]
        commit_count = c["commits"]
        churn_score = c["churn_score"]
        days_since = c["days_since_last_change"]
        is_low_risk = is_low_risk_file(filepath)
        coupled_file_count = len(file_coupling_count.get(filepath, set()))
        owner_data = ownership.get(filepath, {})
        is_shared = owner_data.get("is_shared", False)

        # Churn factor — normalize against repo's own max churn
        # (computed in second pass below)
        churn_factor_raw = churn_score

        # Recency — modified in last 30 days
        recency_factor = max(0.0, 1.0 - (days_since / 60.0))

        # Coupling — log scale
        coupling_factor = min(math.log1p(coupled_file_count) / math.log1p(50), 1.0)

        # Shared ownership
        shared_factor = 0.4 if is_shared else 0.0

        file_risk_data.append({
            "filepath": filepath,
            "commit_count": commit_count,
            "churn_score": churn_score,
            "churn_factor_raw": churn_factor_raw,
            "recency_factor": recency_factor,
            "coupling_factor": coupling_factor,
            "shared_factor": shared_factor,
            "coupled_file_count": coupled_file_count,
            "is_low_risk": is_low_risk,
            "owner_data": owner_data,
            "days_since": days_since
        })

    # Find max churn among CODE files only for normalization
    code_churn_scores = [
        f["churn_factor_raw"] for f in file_risk_data
        if not f["is_low_risk"]
    ]
    max_churn = max(code_churn_scores, default=1.0)

    # Second pass: compute calibrated risk scores
    risk_ranking = []

    for fd in file_risk_data:
        filepath = fd["filepath"]

        # Normalize churn against repo's own max
        churn_factor = fd["churn_factor_raw"] / max_churn if max_churn > 0 else 0

        raw_score = (
            (churn_factor          * 0.35) +
            (fd["recency_factor"]  * 0.25) +
            (fd["coupling_factor"] * 0.30) +
            (fd["shared_factor"]   * 0.10)
        )

        # Hard cap for doc/config files
        if fd["is_low_risk"]:
            raw_score = min(raw_score, 0.30)

        risk_score = round(raw_score, 3)

        # Calibrated thresholds
        # High = top 20% of files in this repo
        # Medium = next 40%
        # Low = bottom 40%
        risk_level = "pending"  # resolved in third pass

        reasons = []
        if fd["commit_count"] > 10:
            reasons.append(f"{fd['commit_count']} commits")
        if fd["days_since"] < 7:
            reasons.append("modified recently")
        if fd["coupled_file_count"] > 5:
            reasons.append(f"coupled with {fd['coupled_file_count']} files")
        if fd["shared_factor"] > 0:
            reasons.append("shared ownership")
        if fd["is_low_risk"]:
            reasons.append("config/doc file")

        risk_ranking.append({
            "file": filepath,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "commit_count": fd["commit_count"],
            "churn_score": fd["churn_score"],
            "coupled_files": fd["coupled_file_count"],
            "days_since_last_change": fd["days_since"],
            "reason": ", ".join(reasons) if reasons else "stable file",
            "owner": fd["owner_data"].get("owner", "unknown"),
            "ownership_status": fd["owner_data"].get("ownership_status", "unknown"),
            "is_doc_file": fd["is_low_risk"],
        })

    # Third pass: assign risk levels based on distribution
    risk_ranking.sort(key=lambda x: x["risk_score"], reverse=True)
    total = len(risk_ranking)
    for i, r in enumerate(risk_ranking):
        pct = i / total if total > 0 else 0
        if pct < 0.20:
            r["risk_level"] = "high"
        elif pct < 0.60:
            r["risk_level"] = "medium"
        else:
            r["risk_level"] = "low"
        # Doc files never exceed medium
        if r["is_doc_file"] and r["risk_level"] == "high":
            r["risk_level"] = "medium"

    # ── Reading order — code files only ───────────────────────

    reading_order = []
    for filepath in file_commits:
        filename = Path(filepath).name.lower()
        churn_data = churn.get(filepath, {})
        commit_count = churn_data.get("commits", 0)

        # Skip config/doc files from reading order
        if is_low_risk_file(filepath):
            continue

        # Skip hidden/IDE folders
        parts = filepath.replace("\\", "/").split("/")
        if any(p.startswith(".") for p in parts[:-1]):
            continue

        priority = GOOD_READING_FILES.get(filename, 0)
        # Stability = fewer commits = safer to read first
        stability = max(0, 50 - commit_count)

        reading_order.append({
            "file": filepath,
            "score": priority + stability,
            "commits": commit_count,
            "reason": "entry point" if priority >= 80 else
                      "core module" if priority >= 50 else "stable file"
        })

    reading_order.sort(key=lambda x: x["score"], reverse=True)

    # ── Repo stats ─────────────────────────────────────────────

    first_commit_date = commits[-1].committed_datetime if commits else None
    last_commit_date = commits[0].committed_datetime if commits else None

    repo_stats = {
        "total_commits_analyzed": len(commits),
        "total_files_tracked": len(file_commits),
        "total_authors": len(all_authors),
        "authors": dict(sorted(author_total.items(), key=lambda x: x[1], reverse=True)),
        "most_active_author": max(author_total, key=author_total.get) if author_total else "unknown",
        "date_range": {
            "first": first_commit_date.strftime("%Y-%m-%d") if first_commit_date else None,
            "last": last_commit_date.strftime("%Y-%m-%d") if last_commit_date else None,
        }
    }

    print(f"Git analysis complete — {len(file_commits)} files analyzed")

    return {
        "churn": churn,
        "ownership": ownership,
        "coupling": coupling_list[:20],
        "risk_ranking": risk_ranking[:30],
        "reading_order": reading_order[:12],
        "repo_stats": repo_stats,
    }


def get_git_summary_for_prompt(git_data: dict) -> str:
    if not git_data or "error" in git_data:
        return ""

    stats = git_data.get("repo_stats", {})
    risk = git_data.get("risk_ranking", [])[:5]
    reading = git_data.get("reading_order", [])[:5]
    coupling = git_data.get("coupling", [])[:3]

    lines = ["\nGIT INTELLIGENCE (from commit history):"]

    if stats:
        lines.append(
            f"Repo: {stats.get('total_commits_analyzed')} commits, "
            f"{stats.get('total_authors')} authors, "
            f"most active: {stats.get('most_active_author')}"
        )

    if risk:
        lines.append("Highest risk code files:")
        for r in risk:
            if not r.get("is_doc_file"):
                lines.append(f"  - {r['file']} (risk: {r['risk_level']}, {r['reason']})")

    if reading:
        lines.append("Recommended reading order for new devs:")
        for i, r in enumerate(reading[:5], 1):
            lines.append(f"  {i}. {r['file']} ({r['reason']})")

    if coupling:
        lines.append("Tightly coupled pairs:")
        for c in coupling:
            lines.append(
                f"  - {c['file_a']} ↔ {c['file_b']} "
                f"({c['co_changes']} co-changes)"
            )

    return "\n".join(lines)
