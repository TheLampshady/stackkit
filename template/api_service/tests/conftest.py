"""
Pytest configuration and fixtures for the test suite.

Provides:
- FastAPI test client with async support
stackkit:begin auth_firebase
- Firebase authentication mocks
stackkit:end auth_firebase
stackkit:begin database
- Firestore mock
stackkit:end database
stackkit:begin storage
- Storage bucket mock
stackkit:end storage
"""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# stackkit:begin auth_firebase
@pytest.fixture
def mock_firebase_auth():
    """Mock Firebase auth client for testing authenticated endpoints.

    Pins the allowed domains to the fixture user's, so results don't depend on
    the project's ``VALID_DOMAINS`` in ``.env``.
    """
    with (
        patch("gcp_services.clients.fb_auth.VALID_DOMAINS", ["example.com"]),
        patch("gcp_services.clients.fb_auth.auth_client") as mock_auth,
    ):
        # Mock verify_id_token to return a valid token payload
        mock_auth.verify_id_token.return_value = {
            "uid": "test-user-123",
            "email": "testuser@example.com",
            "admin": False,
        }

        # Mock get_user to return a user object
        mock_user = MagicMock()
        mock_user.email = "testuser@example.com"
        mock_user.display_name = "Test User"
        mock_auth.get_user.return_value = mock_user

        yield mock_auth


@pytest.fixture
def mock_firebase_auth_admin(mock_firebase_auth):
    """Mock Firebase auth with admin privileges."""
    mock_firebase_auth.verify_id_token.return_value["admin"] = True
    yield mock_firebase_auth


@pytest.fixture
def auth_headers():
    """Standard auth headers for authenticated requests."""
    return {"Authorization": "Bearer fake-test-token"}


# stackkit:end auth_firebase
# stackkit:begin storage
@pytest.fixture
def mock_gcp_bucket():
    """Mock Google Cloud Storage bucket."""
    # Patch where bucket is used, not where it's defined
    with patch("gcp_services.clients.gcp_services.bucket") as mock_bucket:
        # Mock list_blobs to return sample blobs
        mock_blob1 = MagicMock()
        mock_blob1.name = "file1.txt"
        mock_blob2 = MagicMock()
        mock_blob2.name = "file2.txt"
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]

        yield mock_bucket


# stackkit:end storage
# stackkit:begin database
@pytest.fixture
def mock_firestore_db():
    """Mock Firestore database client."""
    # Patch where db is used, not where it's defined
    with patch("gcp_services.clients.gcp_services.db") as mock_db:
        # Mock collections to return an async generator
        async def mock_collections():
            mock_col1 = MagicMock()
            mock_col1.id = "users"
            mock_col2 = MagicMock()
            mock_col2.id = "orders"
            for col in [mock_col1, mock_col2]:
                yield col

        mock_db.collections.return_value = mock_collections()

        yield mock_db


# stackkit:end database
@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient]:
    """
    Async HTTP client for testing FastAPI endpoints.

    Usage:
        async def test_endpoint(async_client):
            response = await async_client.get("/api/healthcheck/")
            assert response.status_code == 200
    """
    # Import app here to avoid import issues with mocks
    from app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
