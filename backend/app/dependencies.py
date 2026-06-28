"""FastAPI dependency injection utilities."""
import sqlite3
from typing import Generator

from fastapi import Header, HTTPException

from app.config import DEFAULT_USER
from app.database import connect_db


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect_db()
    try:
        yield conn
    finally:
        conn.close()


def get_username(x_user: str | None = Header(default=None)) -> str:
    """Get username from X-User header (legacy support)."""
    return x_user or DEFAULT_USER


def get_authenticated_user(
    authorization: str | None = Header(default=None),
    x_user: str | None = Header(default=None),
) -> str:
    """
    Get authenticated username from JWT token or fall back to X-User header.

    This supports both:
    - New JWT auth via Authorization: Bearer <token>
    - Legacy X-User header auth for backwards compatibility
    """
    # Try JWT auth first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Strip "Bearer " prefix
        # Import here to avoid circular import
        from app.routes.auth import decode_token
        username = decode_token(token)
        if username:
            return username
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fall back to X-User header (legacy support)
    if x_user:
        return x_user

    # Fall back to default user for backwards compatibility
    return DEFAULT_USER
