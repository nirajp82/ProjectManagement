"""Tests for authentication endpoints."""
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


class TestRegister:
    def test_register_success(self, tmp_path: Path):
        """Test successful user registration."""
        client = _make_client(tmp_path)
        response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "secret123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["username"] == "newuser"

    def test_register_duplicate_username(self, tmp_path: Path):
        """Test registration with duplicate username."""
        client = _make_client(tmp_path)
        client.post(
            "/api/auth/register",
            json={"username": "existinguser", "password": "secret123"},
        )
        response = client.post(
            "/api/auth/register",
            json={"username": "existinguser", "password": "different123"},
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_register_short_username(self, tmp_path: Path):
        """Test registration with too short username."""
        client = _make_client(tmp_path)
        response = client.post(
            "/api/auth/register",
            json={"username": "ab", "password": "secret123"},
        )
        assert response.status_code == 422

    def test_register_short_password(self, tmp_path: Path):
        """Test registration with too short password."""
        client = _make_client(tmp_path)
        response = client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "12345"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, tmp_path: Path):
        """Test successful login."""
        client = _make_client(tmp_path)
        # Register first
        client.post(
            "/api/auth/register",
            json={"username": "loginuser", "password": "mypassword123"},
        )
        # Then login
        response = client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "mypassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["username"] == "loginuser"

    def test_login_wrong_password(self, tmp_path: Path):
        """Test login with wrong password."""
        client = _make_client(tmp_path)
        client.post(
            "/api/auth/register",
            json={"username": "testuser2", "password": "correctpassword"},
        )
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser2", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, tmp_path: Path):
        """Test login with non-existent user."""
        client = _make_client(tmp_path)
        response = client.post(
            "/api/auth/login",
            json={"username": "nosuchuser", "password": "anypassword"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]


class TestJWTAuth:
    def test_authenticated_board_access(self, tmp_path: Path):
        """Test accessing board with JWT token."""
        client = _make_client(tmp_path)
        # Register and get token
        response = client.post(
            "/api/auth/register",
            json={"username": "jwtuser", "password": "jwtpassword"},
        )
        token = response.json()["token"]

        # Access board with token
        response = client.get(
            "/api/board",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "board" in response.json()

    def test_invalid_token_rejected(self, tmp_path: Path):
        """Test that invalid tokens are rejected."""
        client = _make_client(tmp_path)
        response = client.get(
            "/api/board",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_expired_token_rejected(self, tmp_path: Path):
        """Test that expired tokens are rejected."""
        import jwt
        from datetime import datetime, timedelta, timezone

        client = _make_client(tmp_path)
        payload = {
            "sub": "testuser",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = jwt.encode(payload, "test-secret-key-for-testing", algorithm="HS256")

        response = client.get(
            "/api/board",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_legacy_x_user_header_still_works(self, tmp_path: Path):
        """Test that legacy X-User header still works for backwards compatibility."""
        client = _make_client(tmp_path)
        response = client.get(
            "/api/board",
            headers={"X-User": "legacyuser"},
        )
        assert response.status_code == 200
        assert "board" in response.json()


class TestUserProfile:
    def test_get_profile(self, tmp_path: Path):
        """Test getting user profile."""
        client = _make_client(tmp_path)
        # Register a user
        response = client.post(
            "/api/auth/register",
            json={"username": "profileuser", "password": "testpass123"},
        )
        token = response.json()["token"]

        # Get profile
        response = client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "profileuser"
        assert "created_at" in data

    def test_change_password_success(self, tmp_path: Path):
        """Test changing password successfully."""
        client = _make_client(tmp_path)
        # Register a user
        response = client.post(
            "/api/auth/register",
            json={"username": "pwduser", "password": "oldpassword123"},
        )
        token = response.json()["token"]

        # Change password
        response = client.post(
            "/api/auth/change-password",
            json={"current_password": "oldpassword123", "new_password": "newpassword456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify new password works
        response = client.post(
            "/api/auth/login",
            json={"username": "pwduser", "password": "newpassword456"},
        )
        assert response.status_code == 200

        # Verify old password doesn't work
        response = client.post(
            "/api/auth/login",
            json={"username": "pwduser", "password": "oldpassword123"},
        )
        assert response.status_code == 401

    def test_change_password_wrong_current(self, tmp_path: Path):
        """Test changing password with wrong current password."""
        client = _make_client(tmp_path)
        response = client.post(
            "/api/auth/register",
            json={"username": "wrongpwduser", "password": "correctpass123"},
        )
        token = response.json()["token"]

        response = client.post(
            "/api/auth/change-password",
            json={"current_password": "wrongpass123", "new_password": "newpassword456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"]
