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


def test_get_board_returns_seeded_data(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    auth_headers = _get_auth_headers(client)
    response = client.get("/api/board", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["columns"]) == 5
    assert len(data["cards"]) >= 8


def test_create_and_rename_column(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    auth_headers = _get_auth_headers(client)
    create = client.post("/api/columns", json={"title": "New Column"}, headers=auth_headers)
    assert create.status_code == 200
    column_id = create.json()["id"]

    rename = client.patch(f"/api/columns/{column_id}", json={"title": "Renamed"}, headers=auth_headers)
    assert rename.status_code == 200

    board = client.get("/api/board", headers=auth_headers).json()
    titles = [column["title"] for column in board["columns"]]
    assert "Renamed" in titles


def test_create_move_and_delete_card(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    auth_headers = _get_auth_headers(client)
    board = client.get("/api/board", headers=auth_headers).json()
    first_column = board["columns"][0]
    second_column = board["columns"][1]

    create = client.post(
        "/api/cards",
        json={
            "column_id": int(first_column["id"]),
            "title": "New Card",
            "details": "Details",
        },
        headers=auth_headers,
    )
    assert create.status_code == 200
    card_id = create.json()["id"]

    move = client.patch(
        f"/api/cards/{card_id}",
        json={"column_id": int(second_column["id"]), "position": 0},
        headers=auth_headers,
    )
    assert move.status_code == 200

    updated = client.get("/api/board", headers=auth_headers).json()
    assert card_id in updated["columns"][1]["cardIds"]

    delete = client.delete(f"/api/cards/{card_id}", headers=auth_headers)
    assert delete.status_code == 200

    final = client.get("/api/board", headers=auth_headers).json()
    assert card_id not in final["cards"]


def test_delete_column_removes_cards(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    auth_headers = _get_auth_headers(client)
    board = client.get("/api/board", headers=auth_headers).json()
    target_column = board["columns"][0]
    column_id = target_column["id"]
    card_ids = list(target_column["cardIds"])

    delete = client.delete(f"/api/columns/{column_id}", headers=auth_headers)
    assert delete.status_code == 200

    updated = client.get("/api/board", headers=auth_headers).json()
    assert column_id not in {column["id"] for column in updated["columns"]}
    for card_id in card_ids:
        assert card_id not in updated["cards"]
