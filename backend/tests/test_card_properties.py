"""Tests for card due dates and priorities."""
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db


def _make_client(tmp_path: Path) -> TestClient:
    """Set up a fresh database and return a test client."""
    os.environ["PM_DB_PATH"] = str(tmp_path / "test.db")
    os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
    init_db()
    return TestClient(app)


def _get_auth_headers(client: TestClient, username: str = "testuser") -> dict:
    """Register a user and return auth headers."""
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "testpass123"},
    )
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestCardDueDate:
    def test_create_card_with_due_date(self, tmp_path: Path):
        """Test creating a card with a due date."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        # Create a board and get a column
        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        # Create card with due date
        response = client.post(
            "/api/cards",
            json={
                "column_id": column_id,
                "title": "Card with Due Date",
                "details": "",
                "due_date": "2024-12-31",
            },
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert response.status_code == 200
        card_id = response.json()["id"]

        # Verify due date is returned
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        card = board_data["cards"][card_id]
        assert card["due_date"] == "2024-12-31"

    def test_update_card_due_date(self, tmp_path: Path):
        """Test updating a card's due date."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        # Create card without due date
        create_resp = client.post(
            "/api/cards",
            json={"column_id": column_id, "title": "Test Card", "details": ""},
            params={"board_id": board_id},
            headers=auth_headers,
        )
        card_id = create_resp.json()["id"]

        # Update with due date
        update_resp = client.patch(
            f"/api/cards/{card_id}",
            json={"due_date": "2024-06-15"},
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200

        # Verify
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert board_data["cards"][card_id]["due_date"] == "2024-06-15"

    def test_invalid_due_date_format(self, tmp_path: Path):
        """Test that invalid due date format is rejected."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        response = client.post(
            "/api/cards",
            json={
                "column_id": column_id,
                "title": "Test",
                "details": "",
                "due_date": "invalid-date",
            },
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestCardPriority:
    def test_create_card_with_priority(self, tmp_path: Path):
        """Test creating a card with priority."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        response = client.post(
            "/api/cards",
            json={
                "column_id": column_id,
                "title": "High Priority Card",
                "details": "",
                "priority": "high",
            },
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert response.status_code == 200
        card_id = response.json()["id"]

        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert board_data["cards"][card_id]["priority"] == "high"

    def test_update_card_priority(self, tmp_path: Path):
        """Test updating a card's priority."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        create_resp = client.post(
            "/api/cards",
            json={"column_id": column_id, "title": "Test Card", "details": ""},
            params={"board_id": board_id},
            headers=auth_headers,
        )
        card_id = create_resp.json()["id"]

        # Default priority should be none
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert board_data["cards"][card_id]["priority"] == "none"

        # Update to medium
        update_resp = client.patch(
            f"/api/cards/{card_id}",
            json={"priority": "medium"},
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200

        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert board_data["cards"][card_id]["priority"] == "medium"

    def test_all_priority_levels(self, tmp_path: Path):
        """Test all valid priority levels."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        for priority in ["none", "low", "medium", "high"]:
            response = client.post(
                "/api/cards",
                json={
                    "column_id": column_id,
                    "title": f"{priority.title()} Priority Card",
                    "details": "",
                    "priority": priority,
                },
                params={"board_id": board_id},
                headers=auth_headers,
            )
            assert response.status_code == 200
            card_id = response.json()["id"]

            board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
            assert board_data["cards"][card_id]["priority"] == priority

    def test_invalid_priority_rejected(self, tmp_path: Path):
        """Test that invalid priority values are rejected."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        response = client.post(
            "/api/cards",
            json={
                "column_id": column_id,
                "title": "Test",
                "details": "",
                "priority": "urgent",  # Not a valid priority
            },
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestCardDueDateAndPriority:
    def test_create_card_with_both(self, tmp_path: Path):
        """Test creating a card with both due date and priority."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)

        board_resp = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = int(board_resp.json()["id"])
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        response = client.post(
            "/api/cards",
            json={
                "column_id": column_id,
                "title": "Important Task",
                "details": "Must complete by deadline",
                "due_date": "2024-03-15",
                "priority": "high",
            },
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert response.status_code == 200
        card_id = response.json()["id"]

        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        card = board_data["cards"][card_id]
        assert card["due_date"] == "2024-03-15"
        assert card["priority"] == "high"
        assert card["title"] == "Important Task"
        assert card["details"] == "Must complete by deadline"
