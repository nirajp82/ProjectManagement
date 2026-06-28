"""FastAPI dependency injection utilities."""
import sqlite3
from typing import Generator

from fastapi import Header, HTTPException

from app.database import connect_db


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect_db()
    try:
        yield conn
    finally:
        conn.close()


def get_authenticated_user(
    authorization: str | None = Header(default=None),
    x_user: str | None = Header(default=None),
) -> str:
    """
    Get authenticated username from JWT token or fall back to X-User header.

    Supports:
    - JWT auth via Authorization: Bearer <token>
    - Legacy X-User header for backwards compatibility
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        from app.routes.auth import decode_token
        username = decode_token(token)
        if username:
            return username
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if x_user:
        return x_user

    raise HTTPException(status_code=401, detail="Authentication required")
