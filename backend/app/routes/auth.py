"""Authentication routes for user registration and login."""
import sqlite3
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_jwt_secret
from app.dependencies import get_authenticated_user, get_db
from app.models import AuthResponse, LoginRequest, PasswordChange, RegisterRequest, UserProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# Note: rate limiting on /register and /login should be handled at the
# infrastructure level (nginx, reverse proxy) before public exposure.


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_token(username: str) -> str:
    secret = get_jwt_secret()
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str | None:
    """Decode and validate a JWT token. Returns username or None if invalid."""
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@router.post("/register", response_model=AuthResponse)
def register(
    payload: RegisterRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> AuthResponse:
    """Register a new user."""
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (payload.username,),
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    password_hash = hash_password(payload.password)
    conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (payload.username, password_hash),
    )
    conn.commit()

    token = create_token(payload.username)
    return AuthResponse(token=token, username=payload.username)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> AuthResponse:
    """Login with username and password."""
    user = conn.execute(
        "SELECT username, password_hash FROM users WHERE username = ?",
        (payload.username,),
    ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_hash = user["password_hash"]
    if not password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(payload.username)
    return AuthResponse(token=token, username=payload.username)


@router.get("/profile", response_model=UserProfile)
def get_profile(
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> UserProfile:
    """Get the current user's profile."""
    user = conn.execute(
        "SELECT username, created_at FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(username=user["username"], created_at=user["created_at"])


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Change the current user's password."""
    user = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user["password_hash"] or not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = hash_password(payload.new_password)
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
        (new_hash, username),
    )
    conn.commit()
    return {"status": "ok"}
