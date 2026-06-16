import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-use-long-random-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# ── Password hashing ───────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ── JWT tokens ─────────────────────────────────────────────────

def create_access_token(data: dict, expires_hours: int = ACCESS_TOKEN_EXPIRE_HOURS) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

# ── User store (JSON file — no database needed) ────────────────

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users() -> dict:
    if not Path(USERS_FILE).exists():
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_user(email: str) -> Optional[dict]:
    users = load_users()
    return users.get(email.lower())

def create_user(email: str, password: str, name: str) -> dict:
    users = load_users()
    email = email.lower().strip()

    if email in users:
        raise HTTPException(400, "Email already registered")

    user = {
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan": "free"
    }
    users[email] = user
    save_users(users)

    # Return user without password
    return {k: v for k, v in user.items() if k != "password_hash"}

# ── FastAPI auth dependency ────────────────────────────────────

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency — use this to protect any endpoint.
    
    Usage:
        @app.get("/protected")
        def protected_route(user = Depends(get_current_user)):
            return {"message": f"Hello {user['name']}"}
    """
    if not credentials:
        raise HTTPException(401, "Authentication required. Please log in.")

    payload = decode_token(credentials.credentials)
    email = payload.get("sub")

    if not email:
        raise HTTPException(401, "Invalid token")

    user = get_user(email)
    if not user:
        raise HTTPException(401, "User not found")

    return {k: v for k, v in user.items() if k != "password_hash"}

def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[dict]:
    """
    Like get_current_user but doesn't raise if not logged in.
    Use for endpoints that work both logged in and out.
    """
    if not credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None

# ── Request/response models ────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str
