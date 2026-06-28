"""Tests for label management endpoints."""
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


def _create_board(client: TestClient, auth_headers: dict, title: str = "Test Board") -> int:
    """Create a board and return its ID."""
    response = client.post(
        "/api/boards",
        json={"title": title},
        headers=auth_headers,
    )
    return int(response.json()["id"])


class TestLabelCRUD:
    def test_create_label(self, tmp_path: Path):
        """Test creating a label."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        board_id = _create_board(client, auth_headers)

        response = client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "id" in response.json()

    def test_list_labels(self, tmp_path: Path):
        """Test listing labels for a board."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        board_id = _create_board(client, auth_headers)

        # Create some labels
        client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=auth_headers,
        )
        client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Feature", "color": "#00ff00"},
            headers=auth_headers,
        )

        response = client.get(
            f"/api/boards/{board_id}/labels",
            headers=auth_headers,
        )
        assert response.status_code == 200
        labels = response.json()
        assert len(labels) == 2
        names = {label["name"] for label in labels}
        assert names == {"Bug", "Feature"}

    def test_update_label(self, tmp_path: Path):
        """Test updating a label."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        board_id = _create_board(client, auth_headers)

        # Create a label
        create_response = client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=auth_headers,
        )
        label_id = create_response.json()["id"]

        # Update it
        update_response = client.patch(
            f"/api/labels/{label_id}",
            json={"name": "Critical Bug", "color": "#990000"},
            headers=auth_headers,
        )
        assert update_response.status_code == 200

        # Verify update
        list_response = client.get(
            f"/api/boards/{board_id}/labels",
            headers=auth_headers,
        )
        labels = list_response.json()
        updated = next(l for l in labels if l["id"] == label_id)
        assert updated["name"] == "Critical Bug"
        assert updated["color"] == "#990000"

    def test_delete_label(self, tmp_path: Path):
        """Test deleting a label."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        board_id = _create_board(client, auth_headers)

        # Create a label
        create_response = client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=auth_headers,
        )
        label_id = create_response.json()["id"]

        # Delete it
        delete_response = client.delete(
            f"/api/labels/{label_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200

        # Verify it's gone
        list_response = client.get(
            f"/api/boards/{board_id}/labels",
            headers=auth_headers,
        )
        assert len(list_response.json()) == 0


class TestCardLabels:
    def test_add_label_to_card(self, tmp_path: Path):
        """Test adding a label to a card."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        board_id = _create_board(client, auth_headers)

        # Get a column to create a card
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        # Create a card
        card_response = client.post(
            "/api/cards",
            json={"column_id": column_id, "title": "Test Card", "details": ""},
            params={"board_id": board_id},
            headers=auth_headers,
        )
        card_id = int(card_response.json()["id"])

        # Create a label
        label_response = client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=auth_headers,
        )
        label_id = int(label_response.json()["id"])

        # Add label to card
        response = client.post(
            f"/api/cards/{card_id}/labels",
            json={"label_id": label_id},
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify label is on card
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        card = board_data["cards"][str(card_id)]
        assert str(label_id) in card["labelIds"]

    def test_remove_label_from_card(self, tmp_path: Path):
        """Test removing a label from a card."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        board_id = _create_board(client, auth_headers)

        # Get a column
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        column_id = int(board_data["columns"][0]["id"])

        # Create card and label
        card_response = client.post(
            "/api/cards",
            json={"column_id": column_id, "title": "Test Card", "details": ""},
            params={"board_id": board_id},
            headers=auth_headers,
        )
        card_id = int(card_response.json()["id"])

        label_response = client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=auth_headers,
        )
        label_id = int(label_response.json()["id"])

        # Add then remove label
        client.post(
            f"/api/cards/{card_id}/labels",
            json={"label_id": label_id},
            params={"board_id": board_id},
            headers=auth_headers,
        )

        response = client.delete(
            f"/api/cards/{card_id}/labels/{label_id}",
            params={"board_id": board_id},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify label is removed
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        card = board_data["cards"][str(card_id)]
        assert str(label_id) not in card["labelIds"]

    def test_labels_included_in_board_response(self, tmp_path: Path):
        """Test that labels are included in board fetch response."""
        client = _make_client(tmp_path)
        auth_headers = _get_auth_headers(client)
        board_id = _create_board(client, auth_headers)

        # Create labels
        client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=auth_headers,
        )
        client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Feature", "color": "#00ff00"},
            headers=auth_headers,
        )

        # Fetch board and check labels
        board_data = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert "labels" in board_data
        assert len(board_data["labels"]) == 2


class TestLabelAccess:
    def test_cannot_access_other_users_labels(self, tmp_path: Path):
        """Test that users cannot access other users' board labels."""
        client = _make_client(tmp_path)

        # User 1 creates a board with labels
        headers1 = _get_auth_headers(client, "user1")
        board_id = _create_board(client, headers1)
        label_response = client.post(
            f"/api/boards/{board_id}/labels",
            json={"name": "Bug", "color": "#ff0000"},
            headers=headers1,
        )
        label_id = int(label_response.json()["id"])

        # User 2 tries to access
        headers2 = _get_auth_headers(client, "user2")

        # Cannot list labels
        response = client.get(
            f"/api/boards/{board_id}/labels",
            headers=headers2,
        )
        assert response.status_code == 404

        # Cannot update label
        response = client.patch(
            f"/api/labels/{label_id}",
            json={"name": "Hacked"},
            headers=headers2,
        )
        assert response.status_code == 404

        # Cannot delete label
        response = client.delete(
            f"/api/labels/{label_id}",
            headers=headers2,
        )
        assert response.status_code == 404
