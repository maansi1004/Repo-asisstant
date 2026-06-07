import re
from pathlib import Path

# ─────────────────────────────────────────
# ALL SECURITY CHECKS
# Each check has: id, pattern, severity, message, fix, file_types
# file_types = None means check all files
# ─────────────────────────────────────────

CHECKS = [

    # ── HIGH SEVERITY ──────────────────────────────────────────────

    {
        "id": "hardcoded_password",
        "pattern": r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']',
        "severity": "HIGH",
        "message": "Hardcoded password detected",
        "fix": "Move to environment variable: os.getenv('PASSWORD') or process.env.PASSWORD",
        "file_types": None
    },
    {
        "id": "hardcoded_api_key",
        "pattern": r'(?i)(api_key|apikey|api-key|secret_key|secretkey)\s*[=:]\s*["\'][A-Za-z0-9_\-]{10,}["\']',
        "severity": "HIGH",
        "message": "Hardcoded API key detected",
        "fix": "Move to .env file and load with dotenv",
        "file_types": None
    },
    {
        "id": "hardcoded_token",
        "pattern": r'(?i)(token|auth_token|access_token|bearer)\s*=\s*["\'][A-Za-z0-9_\-\.]{20,}["\']',
        "severity": "HIGH",
        "message": "Hardcoded token detected",
        "fix": "Never hardcode tokens. Use environment variables.",
        "file_types": None
    },
    {
        "id": "private_key_in_code",
        "pattern": r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
        "severity": "HIGH",
        "message": "Private key hardcoded in source file",
        "fix": "Remove immediately. Store keys in secure vault or environment variables.",
        "file_types": None
    },
    {
        "id": "sql_injection_concat",
        "pattern": r'(?i)(query|execute|cursor\.execute)\s*\(\s*["\'].*?(SELECT|INSERT|UPDATE|DELETE).*?\+|f["\'].*?(SELECT|INSERT|UPDATE|DELETE).*?\{',
        "severity": "HIGH",
        "message": "Possible SQL injection — query built with string concatenation",
        "fix": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        "file_types": None
    },
    {
        "id": "eval_usage",
        "pattern": r'\beval\s*\(',
        "severity": "HIGH",
        "message": "eval() usage detected — remote code execution risk",
        "fix": "Never use eval() on user input. Use JSON.parse() for JSON or ast.literal_eval() for Python.",
        "file_types": None
    },
    {
        "id": "hardcoded_jwt_secret",
        "pattern": r'(?i)(jwt\.sign|jwt_secret|JWT_SECRET)\s*[=(:,]\s*["\'][^"\']{5,}["\']',
        "severity": "HIGH",
        "message": "Hardcoded JWT secret detected",
        "fix": "Use a long random secret from environment variables. Min 32 characters.",
        "file_types": None
    },
    {
        "id": "command_injection",
        "pattern": r'(?i)(exec|spawn|system|subprocess\.call|os\.system)\s*\(.*?\+',
        "severity": "HIGH",
        "message": "Possible command injection — shell command built with string concatenation",
        "fix": "Never concatenate user input into shell commands. Use subprocess with list args.",
        "file_types": None
    },

    # ── MEDIUM SEVERITY ────────────────────────────────────────────

    {
        "id": "no_password_hashing",
        "pattern": r'(?i)(password|passwd)\s*=\s*request\.(body|json|form|data)',
        "severity": "MEDIUM",
        "message": "Password stored directly from request without hashing",
        "fix": "Always hash passwords: bcrypt.hash(password, 10) or bcrypt.hashpw(password, bcrypt.gensalt())",
        "file_types": None
    },
    {
        "id": "md5_usage",
        "pattern": r'(?i)(md5|MD5)\s*\(',
        "severity": "MEDIUM",
        "message": "MD5 hashing detected — insecure for passwords",
        "fix": "Use bcrypt, argon2, or scrypt for passwords. Use SHA-256+ for checksums.",
        "file_types": None
    },
    {
        "id": "sha1_password",
        "pattern": r'(?i)sha1\s*\(',
        "severity": "MEDIUM",
        "message": "SHA1 detected — too weak for password hashing",
        "fix": "Use bcrypt or argon2 for password hashing",
        "file_types": None
    },
    {
        "id": "sensitive_console_log",
        "pattern": r'(?i)(console\.log|print)\s*\(.*?(password|token|secret|key|credential)',
        "severity": "MEDIUM",
        "message": "Sensitive data possibly logged to console",
        "fix": "Never log passwords, tokens, or secrets. Remove or redact before logging.",
        "file_types": None
    },
    {
        "id": "debug_mode_on",
        "pattern": r'(?i)(DEBUG\s*=\s*True|debug\s*:\s*true|app\.run.*debug\s*=\s*True)',
        "severity": "MEDIUM",
        "message": "Debug mode enabled — exposes stack traces in production",
        "fix": "Set DEBUG=False in production. Use environment variable to control.",
        "file_types": None
    },
    {
        "id": "http_not_https",
        "pattern": r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[a-zA-Z]',
        "severity": "MEDIUM",
        "message": "HTTP URL used instead of HTTPS",
        "fix": "Always use HTTPS for external URLs in production",
        "file_types": None
    },
    {
        "id": "cors_wildcard",
        "pattern": r'(?i)(allow_origins|Access-Control-Allow-Origin)\s*[=:]\s*[\["]?\*[\]"]?',
        "severity": "MEDIUM",
        "message": "CORS wildcard (*) allows any origin",
        "fix": "Restrict origins to known domains: allow_origins=['https://yourdomain.com']",
        "file_types": None
    },
    {
        "id": "no_input_validation",
        "pattern": r'(?i)req\.(body|query|params)\.\w+\s*[^=!<>]',
        "severity": "MEDIUM",
        "message": "Request input used directly without visible validation",
        "fix": "Validate and sanitize all user inputs before processing",
        "file_types": [".js", ".ts"]
    },
    {
        "id": "insecure_random",
        "pattern": r'(?i)(Math\.random\(\)|random\.random\(\))',
        "severity": "MEDIUM",
        "message": "Insecure random number generator used",
        "fix": "Use crypto.randomBytes() (Node.js) or secrets module (Python) for security-sensitive randomness",
        "file_types": None
    },

    # ── LOW SEVERITY ───────────────────────────────────────────────

    {
        "id": "todo_security",
        "pattern": r'(?i)(TODO|FIXME|HACK|XXX).{0,30}(auth|security|password|token|validate|sanitize)',
        "severity": "LOW",
        "message": "Unresolved security TODO/FIXME comment",
        "fix": "Address security-related TODOs before production deployment",
        "file_types": None
    },
    {
        "id": "commented_credentials",
        "pattern": r'(?i)#.*?(password|api_key|secret|token)\s*=\s*\S+',
        "severity": "LOW",
        "message": "Possible credentials in commented-out code",
        "fix": "Remove commented credentials from source code entirely",
        "file_types": None
    },
    {
        "id": "long_function_security",
        "pattern": r'(?i)def .{1,50}(auth|login|password|token|verify|validate)',
        "severity": "LOW",
        "message": "Security-related function detected — ensure it handles errors properly",
        "fix": "Make sure auth functions have proper error handling and don't leak information",
        "file_types": [".py"]
    },
]

# ─────────────────────────────────────────
# OK CHECKS — good practices to reward
# ─────────────────────────────────────────

OK_CHECKS = [
    {
        "id": "env_vars_used",
        "pattern": r'(?i)(os\.getenv|process\.env|dotenv|load_dotenv)',
        "message": "Environment variables used for configuration"
    },
    {
        "id": "bcrypt_used",
        "pattern": r'(?i)(bcrypt|argon2|hashpw|werkzeug\.security)',
        "message": "Secure password hashing library detected"
    },
    {
        "id": "cors_configured",
        "pattern": r'(?i)(CORSMiddleware|cors\(\)|app\.use\(cors)',
        "message": "CORS middleware configured"
    },
    {
        "id": "jwt_used",
        "pattern": r'(?i)(jsonwebtoken|jwt\.sign|jwt\.verify|python-jose|PyJWT)',
        "message": "JWT authentication library detected"
    },
    {
        "id": "parameterized_queries",
        "pattern": r'(?i)(cursor\.execute\s*\(.*?,\s*\(|db\.query\s*\(.*?,\s*\[|\$\d+|\?)',
        "message": "Parameterized queries detected — SQL injection protection"
    },
    {
        "id": "https_enforced",
        "pattern": r'(?i)(https_only|SECURE|force_https|sslify)',
        "message": "HTTPS enforcement detected"
    },
    {
        "id": "rate_limiting",
        "pattern": r'(?i)(rate.?limit|throttle|slowDown|rateLimit)',
        "message": "Rate limiting detected"
    },
    {
        "id": "input_validation",
        "pattern": r'(?i)(joi|yup|zod|pydantic|marshmallow|validator)',
        "message": "Input validation library detected"
    },
]

# Files to skip for security scanning
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3",
    ".woff", ".woff2", ".ttf", ".eot", ".pyc",
    ".lock", ".min.js", ".min.css"
}

SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "dist", "build"}


def should_scan(filepath: str) -> bool:
    path = Path(filepath)
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return False
    for skip in SKIP_DIRS:
        if skip in filepath.replace("\\", "/"):
            return False
    return True


def scan_file(filepath: str, content: str) -> list[dict]:
    """Scan a single file for security issues. Returns list of findings."""
    if not should_scan(filepath):
        return []

    ext = Path(filepath).suffix.lower()
    findings = []
    lines = content.splitlines()

    for check in CHECKS:
        # Skip if check is only for specific file types
        if check["file_types"] and ext not in check["file_types"]:
            continue

        pattern = re.compile(check["pattern"])

        for line_num, line in enumerate(lines, start=1):
            if pattern.search(line):
                # Get evidence — truncate long lines
                evidence = line.strip()[:120]

                findings.append({
                    "severity": check["severity"],
                    "check_id": check["id"],
                    "file": filepath,
                    "line": line_num,
                    "message": check["message"],
                    "evidence": evidence,
                    "fix": check["fix"]
                })
                break  # one finding per check per file to avoid spam

    return findings


def check_ok_practices(files: dict) -> list[str]:
    """Check for good security practices across all files."""
    ok_found = []
    all_content = "\n".join(files.values())

    for check in OK_CHECKS:
        if re.search(check["pattern"], all_content):
            ok_found.append(check["message"])

    return ok_found


def calculate_score(issues: list[dict], ok_checks: list[str]) -> tuple[float, str]:
    """Calculate security score 0-10 and letter grade."""
    score = 10.0

    for issue in issues:
        if issue["severity"] == "HIGH":
            score -= 1.5
        elif issue["severity"] == "MEDIUM":
            score -= 0.5
        elif issue["severity"] == "LOW":
            score -= 0.1

    # Reward good practices
    score += len(ok_checks) * 0.2

    score = max(0.0, min(10.0, score))
    score = round(score, 1)

    if score >= 9:
        grade = "A"
    elif score >= 8:
        grade = "B"
    elif score >= 7:
        grade = "C"
    elif score >= 5:
        grade = "D"
    else:
        grade = "F"

    return score, grade


def get_recommendation(score: float, issues: list[dict]) -> str:
    high_count = sum(1 for i in issues if i["severity"] == "HIGH")
    med_count = sum(1 for i in issues if i["severity"] == "MEDIUM")

    if high_count > 0:
        return f"Fix {high_count} HIGH severity issue(s) immediately before any deployment"
    elif med_count > 3:
        return f"Address {med_count} medium severity issues to improve security posture"
    elif score >= 8:
        return "Good security posture. Continue following best practices."
    else:
        return "Review and address all flagged issues before production deployment"


# ─────────────────────────────────────────
# DOCUMENTATION CHECKS
# These check for missing files/practices
# not patterns inside files
# ─────────────────────────────────────────

DOC_CHECKS = [
    {
        "id": "missing_readme",
        "files_to_check": ["readme.md", "readme.rst", "readme.txt", "readme"],
        "severity": "MEDIUM",
        "message": "No README file found",
        "fix": "Add a README.md explaining what the project does, how to install, and how to run it"
    },
    {
        "id": "missing_env_example",
        "files_to_check": [".env.example", ".env.sample", ".env.template"],
        "severity": "MEDIUM",
        "message": "No .env.example file found",
        "fix": "Add .env.example showing required environment variables without real values"
    },
    {
        "id": "env_file_committed",
        "files_to_check": [".env"],
        "severity": "HIGH",
        "message": ".env file committed to repository — secrets exposed",
        "fix": "Add .env to .gitignore immediately and rotate all exposed credentials"
    },
    {
        "id": "missing_gitignore",
        "files_to_check": [".gitignore"],
        "severity": "LOW",
        "message": "No .gitignore file found",
        "fix": "Add .gitignore to prevent committing node_modules, .env, and build files"
    },
    {
        "id": "missing_license",
        "files_to_check": ["license", "license.md", "license.txt"],
        "severity": "LOW",
        "message": "No LICENSE file found",
        "fix": "Add a LICENSE file — MIT is common for open source projects"
    },
    {
        "id": "missing_contributing",
        "files_to_check": ["contributing.md", "contributing.rst"],
        "severity": "LOW",
        "message": "No CONTRIBUTING guide found",
        "fix": "Add CONTRIBUTING.md explaining how others can contribute"
    },
]


def check_documentation(files: dict) -> list[dict]:
    """
    Check for missing important files.
    Runs against the full file list, not file contents.
    """
    findings = []

    # Normalize all filepaths to lowercase for matching
    all_filenames = set()
    for filepath in files.keys():
        filename = filepath.replace("\\", "/").split("/")[-1].lower()
        all_filenames.add(filename)

    for check in DOC_CHECKS:
        found = any(f in all_filenames for f in check["files_to_check"])

        # .env committed is bad — flag if FOUND
        if check["id"] == "env_file_committed":
            if found:
                findings.append({
                    "severity": check["severity"],
                    "check_id": check["id"],
                    "file": ".env",
                    "line": 0,
                    "message": check["message"],
                    "evidence": ".env file present in repository",
                    "fix": check["fix"]
                })
        else:
            # All other checks — flag if NOT found
            if not found:
                findings.append({
                    "severity": check["severity"],
                    "check_id": check["id"],
                    "file": "— (missing file)",
                    "line": 0,
                    "message": check["message"],
                    "evidence": f"None of {check['files_to_check']} found in repo",
                    "fix": check["fix"]
                })

    return findings

def scan_security(files: dict) -> dict:
    """
    Main function — scan all files for security issues.
    Returns a structured security report.
    """
    all_issues = []
    scanned_files = 0

    for filepath, content in files.items():
        if not should_scan(filepath):
            continue
        scanned_files += 1
        file_issues = scan_file(filepath, content)
        all_issues.extend(file_issues)

# Documentation checks
    doc_issues = check_documentation(files)
    all_issues.extend(doc_issues)
    # Check for good practices
    ok_checks = check_ok_practices(files)

    # Calculate score
    score, grade = calculate_score(all_issues, ok_checks)

    # Count by severity
    by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for issue in all_issues:
        by_severity[issue["severity"]] += 1

    # Top risk files — files with most HIGH issues
    file_risk = {}
    for issue in all_issues:
        if issue["severity"] == "HIGH":
            file_risk[issue["file"]] = file_risk.get(issue["file"], 0) + 1
    top_risk_files = sorted(file_risk, key=file_risk.get, reverse=True)[:5]

    # Sort issues — HIGH first
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_issues.sort(key=lambda x: severity_order[x["severity"]])

    return {
        "score": score,
        "grade": grade,
        "scanned_files": scanned_files,
        "total_issues": len(all_issues),
        "by_severity": by_severity,
        "issues": all_issues,
        "ok_checks": ok_checks,
        "top_risk_files": top_risk_files,
        "recommendation": get_recommendation(score, all_issues),
          "documentation_issues": [i for i in all_issues if i["check_id"] in 
                             [d["id"] for d in DOC_CHECKS]],
    "code_issues": [i for i in all_issues if i["check_id"] not in 
                   [d["id"] for d in DOC_CHECKS]]
    }
