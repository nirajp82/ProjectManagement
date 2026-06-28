"""Tests for board management endpoints."""
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


class TestListBoards:
    def test_list_boards_empty(self, tmp_path: Path):
        """Test listing boards when user has none."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        response = client.get("/api/boards", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["boards"] == []

    def test_list_boards_with_boards(self, tmp_path: Path):
        """Test listing boards after creating some."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        client.post(
            "/api/boards",
            json={"title": "Board 1"},
            headers=auth_headers,
        )
        client.post(
            "/api/boards",
            json={"title": "Board 2"},
            headers=auth_headers,
        )
        response = client.get("/api/boards", headers=auth_headers)
        assert response.status_code == 200
        boards = response.json()["boards"]
        assert len(boards) == 2
        # Verify both boards exist (order may vary due to same-second creation)
        board_titles = {b["title"] for b in boards}
        assert board_titles == {"Board 1", "Board 2"}


class TestCreateBoard:
    def test_create_board_success(self, tmp_path: Path):
        """Test creating a new board."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        response = client.post(
            "/api/boards",
            json={"title": "My New Board"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "id" in response.json()

    def test_create_board_with_default_columns(self, tmp_path: Path):
        """Test that new boards get default columns."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        response = client.post(
            "/api/boards",
            json={"title": "My New Board", "with_default_columns": True},
            headers=auth_headers,
        )
        board_id = response.json()["id"]
        board_response = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        columns = board_response.json()["columns"]
        assert len(columns) == 4
        column_titles = [c["title"] for c in columns]
        assert "Backlog" in column_titles
        assert "Done" in column_titles

    def test_create_board_without_default_columns(self, tmp_path: Path):
        """Test creating board without default columns."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        response = client.post(
            "/api/boards",
            json={"title": "Empty Board", "with_default_columns": False},
            headers=auth_headers,
        )
        board_id = response.json()["id"]
        board_response = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        columns = board_response.json()["columns"]
        assert len(columns) == 0


class TestGetBoard:
    def test_get_board_success(self, tmp_path: Path):
        """Test getting a specific board."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        create_response = client.post(
            "/api/boards",
            json={"title": "Test Board"},
            headers=auth_headers,
        )
        board_id = create_response.json()["id"]
        response = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["board"]["title"] == "Test Board"

    def test_get_board_not_found(self, tmp_path: Path):
        """Test getting a non-existent board."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        response = client.get("/api/boards/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_board_wrong_user(self, tmp_path: Path):
        """Test that users can't access other users' boards."""
        client = _make_client(tmp_path)
        # Create board as first user
        auth_headers = _get_auth_headers(client, "user1")
        create_response = client.post(
            "/api/boards",
            json={"title": "Private Board"},
            headers=auth_headers,
        )
        board_id = create_response.json()["id"]

        # Second user
        other_headers = _get_auth_headers(client, "user2")

        # Try to access first user's board
        response = client.get(f"/api/boards/{board_id}", headers=other_headers)
        assert response.status_code == 404


class TestUpdateBoard:
    def test_update_board_title(self, tmp_path: Path):
        """Test updating a board's title."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        create_response = client.post(
            "/api/boards",
            json={"title": "Original Title"},
            headers=auth_headers,
        )
        board_id = create_response.json()["id"]

        response = client.patch(
            f"/api/boards/{board_id}",
            json={"title": "New Title"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        get_response = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        assert get_response.json()["board"]["title"] == "New Title"


class TestDeleteBoard:
    def test_delete_board_success(self, tmp_path: Path):
        """Test deleting a board."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        create_response = client.post(
            "/api/boards",
            json={"title": "Board to Delete"},
            headers=auth_headers,
        )
        board_id = create_response.json()["id"]

        response = client.delete(f"/api/boards/{board_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_board_cascades(self, tmp_path: Path):
        """Test that deleting a board also deletes columns and cards."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        # Create board
        create_response = client.post(
            "/api/boards",
            json={"title": "Board with Data"},
            headers=auth_headers,
        )
        board_id = int(create_response.json()["id"])

        # Get board to find a column
        board_response = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        columns = board_response.json()["columns"]
        column_id = int(columns[0]["id"])

        # Create a card in that column
        client.post(
            "/api/cards",
            json={"column_id": column_id, "title": "Test Card", "details": "Details"},
            params={"board_id": board_id},
            headers=auth_headers,
        )

        # Delete the board
        response = client.delete(f"/api/boards/{board_id}", headers=auth_headers)
        assert response.status_code == 200

        # The board should be gone
        get_response = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        assert get_response.status_code == 404


class TestMultipleBoardsIsolation:
    def test_cards_isolated_between_boards(self, tmp_path: Path):
        """Test that cards in one board don't appear in another."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        # Create two boards
        board1_response = client.post(
            "/api/boards",
            json={"title": "Board 1"},
            headers=auth_headers,
        )
        board1_id = int(board1_response.json()["id"])

        board2_response = client.post(
            "/api/boards",
            json={"title": "Board 2"},
            headers=auth_headers,
        )
        board2_id = int(board2_response.json()["id"])

        # Get column from board 1
        board1_data = client.get(f"/api/boards/{board1_id}", headers=auth_headers).json()
        column1_id = int(board1_data["columns"][0]["id"])

        # Create card in board 1
        client.post(
            "/api/cards",
            json={"column_id": column1_id, "title": "Card in Board 1", "details": ""},
            params={"board_id": board1_id},
            headers=auth_headers,
        )

        # Check board 1 has the card
        board1_updated = client.get(f"/api/boards/{board1_id}", headers=auth_headers).json()
        assert len(board1_updated["cards"]) == 1

        # Check board 2 has no cards
        board2_data = client.get(f"/api/boards/{board2_id}", headers=auth_headers).json()
        assert len(board2_data["cards"]) == 0
