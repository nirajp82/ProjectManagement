import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db


def _make_client(tmp_path: Path) -> TestClient:
    os.environ["PM_DB_PATH"] = str(tmp_path / "test.db")
    os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
    init_db()
    return TestClient(app)


def _get_auth_headers(client: TestClient, username: str = "testuser") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "testpass123"},
    )
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_chat_missing_api_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    client = _make_client(tmp_path)
    auth_headers = _get_auth_headers(client)
    response = client.post("/api/chat", json={"message": "2+2"}, headers=auth_headers)
    assert response.status_code == 500
    assert response.json() == {"detail": "OPENROUTER_API_KEY not configured"}
