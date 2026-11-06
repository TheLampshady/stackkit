"""
Tests for the API router endpoints.
"""

from unittest.mock import patch

from httpx import AsyncClient


class TestHealthcheck:
    """Tests for the healthcheck endpoint."""

    async def test_healthcheck_returns_success(self, async_client: AsyncClient):
        """Healthcheck should return success without authentication."""
        response = await async_client.get("/api/healthcheck/")

        assert response.status_code == 200
        assert response.json() == {"success": True}


# stackkit:begin auth_firebase
class TestHomeEndpoint:
    """Tests for the authenticated home endpoint."""

    async def test_home_without_auth_returns_401(self, async_client: AsyncClient):
        """Home endpoint should reject unauthenticated requests."""
        response = await async_client.get("/api/")

        assert response.status_code == 401

    async def test_home_with_valid_auth_returns_message(
        self,
        async_client: AsyncClient,
        mock_firebase_auth,
        auth_headers,
    ):
        """Home endpoint should return message for authenticated users."""
        response = await async_client.get("/api/", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}

    async def test_home_with_invalid_domain_returns_403(
        self,
        async_client: AsyncClient,
        mock_firebase_auth,
        auth_headers,
    ):
        """Home endpoint should reject users from invalid domains."""
        # Override mock to return invalid domain
        mock_firebase_auth.verify_id_token.return_value["email"] = "user@invalid.com"
        mock_user = mock_firebase_auth.get_user.return_value
        mock_user.email = "user@invalid.com"

        response = await async_client.get("/api/", headers=auth_headers)

        assert response.status_code == 403

    async def test_home_with_empty_domain_list_allows_any_domain(
        self,
        async_client: AsyncClient,
        mock_firebase_auth,
        auth_headers,
    ):
        """An empty VALID_DOMAINS list disables the domain check."""
        mock_firebase_auth.verify_id_token.return_value["email"] = "user@other.com"
        mock_firebase_auth.get_user.return_value.email = "user@other.com"

        with patch("gcp_services.clients.fb_auth.VALID_DOMAINS", []):
            response = await async_client.get("/api/", headers=auth_headers)

        assert response.status_code == 200


# stackkit:end auth_firebase
class TestQueryEndpoint:
    """Tests for the query endpoint."""

    async def test_query_returns_text(self, async_client: AsyncClient):
        """Query endpoint should echo back the provided text."""
        response = await async_client.post(
            "/api/query/",
            json={"text": "Hello, test!"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Hello, test!"}

    async def test_query_with_empty_text(self, async_client: AsyncClient):
        """Query endpoint should handle empty text."""
        response = await async_client.post(
            "/api/query/",
            json={"text": ""},
        )

        assert response.status_code == 200
        assert response.json() == {"message": ""}

    async def test_query_without_text_returns_422(self, async_client: AsyncClient):
        """Query endpoint should reject requests without text field."""
        response = await async_client.post(
            "/api/query/",
            json={},
        )

        assert response.status_code == 422


# stackkit:begin storage
class TestFileListEndpoint:
    """Tests for the file-list endpoint."""

    async def test_file_list_returns_files(
        self,
        async_client: AsyncClient,
        mock_gcp_bucket,
    ):
        """File list endpoint should return bucket file names."""
        response = await async_client.get("/api/file-list/")

        assert response.status_code == 200
        assert response.json() == {"file_names": ["file1.txt", "file2.txt"]}


# stackkit:end storage
# stackkit:begin database
class TestDbListEndpoint:
    """Tests for the db-list endpoint."""

    async def test_db_list_returns_collections(
        self,
        async_client: AsyncClient,
        mock_firestore_db,
    ):
        """DB list endpoint should return Firestore collection IDs."""
        response = await async_client.get("/api/db-list/")

        assert response.status_code == 200
        assert response.json() == {"db_ids": ["users", "orders"]}


# stackkit:end database
