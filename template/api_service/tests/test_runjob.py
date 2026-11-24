"""Tests for starting background jobs from the server (gcp_runjob)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from gcp_services.clients.gcp_runjob import JobBusyError, cloud_run_name, reserve
from httpx import AsyncClient

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LATER = NOW + timedelta(hours=2)


def going(**runs: str | None) -> dict:
    """Runs going, by id, each with its key and a deadline still ahead."""
    return {rid: {"key": key, "deadline_at": LATER} for rid, key in runs.items()}


class TestReserve:
    """Deciding whether a run may start."""

    def test_adds_the_run(self):
        active, existing = reserve({}, "new", None, 10, NOW, LATER)
        assert existing is None
        assert active == {"new": {"key": None, "deadline_at": LATER}}

    def test_same_key_returns_the_run_going(self):
        active, existing = reserve(
            going(a="report:1"), "new", "report:1", 10, NOW, LATER
        )
        assert existing == "a"
        assert "new" not in active

    def test_other_key_starts(self):
        _, existing = reserve(going(a="report:1"), "new", "report:2", 10, NOW, LATER)
        assert existing is None

    def test_refuses_past_the_limit(self):
        with pytest.raises(JobBusyError):
            reserve(going(a=None, b=None), "new", None, 2, NOW, LATER)

    def test_no_limit(self):
        active, _ = reserve(going(a=None, b=None), "new", None, None, NOW, LATER)
        assert len(active) == 3

    def test_runs_past_their_deadline_free_their_place(self):
        stale = {"a": {"key": "report:1", "deadline_at": NOW - timedelta(seconds=1)}}
        active, existing = reserve(stale, "new", "report:1", 1, NOW, LATER)
        assert existing is None
        assert list(active) == ["new"]


def test_cloud_run_name_matches_deploy():
    with patch("gcp_services.clients.gcp_runjob.settings") as settings:
        settings.namespace = "shop"
        assert cloud_run_name("summarize_file") == "shop-summarize-file"
        settings.namespace = None
        assert cloud_run_name("summarize_file") == "summarize-file"


# stackkit:begin auth_iap,auth_firebase
@pytest.fixture
def headers(request: pytest.FixtureRequest) -> dict[str, str]:
    """Headers that get past the project's sign-in."""
    found: dict[str, str] = {}
    # stackkit:begin auth_firebase
    request.getfixturevalue("mock_firebase_auth")
    found = request.getfixturevalue("auth_headers")
    # stackkit:end auth_firebase
    return found


@pytest.fixture
def me() -> str:
    """The email the endpoints see for the caller."""
    email = ""
    # stackkit:begin auth_iap
    from app_settings import settings

    email = settings.local_user_email or ""
    # stackkit:end auth_iap
    # stackkit:begin auth_firebase
    email = "testuser@example.com"  # conftest's mock_firebase_auth
    # stackkit:end auth_firebase
    return email


class TestRunEndpoints:
    """The example endpoints that start a job and report on it."""

    async def test_start_answers_with_the_run_id(
        self, async_client: AsyncClient, headers, me
    ):
        with patch("api.router.start_job", AsyncMock(return_value="r1")) as start:
            response = await async_client.post("/api/example-runs/", headers=headers)
        assert response.status_code == 202
        assert response.json() == {"run_id": "r1"}
        assert start.call_args.args[0] == "example"
        assert start.call_args.kwargs["owner"] == me

    async def test_busy_is_429(self, async_client: AsyncClient, headers):
        busy = AsyncMock(side_effect=JobBusyError("full"))
        with patch("api.router.start_job", busy):
            response = await async_client.post("/api/example-runs/", headers=headers)
        assert response.status_code == 429

    async def test_status(self, async_client: AsyncClient, headers, me):
        run = {"job": "example", "status": "running", "error": None, "owner": me}
        with patch("api.router.get_run", AsyncMock(return_value=run)):
            response = await async_client.get("/api/runs/r1", headers=headers)
        assert response.json() == {"job": "example", "status": "running", "error": None}

    async def test_unknown_run_is_404(self, async_client: AsyncClient, headers):
        with patch("api.router.get_run", AsyncMock(return_value=None)):
            response = await async_client.get("/api/runs/nope", headers=headers)
        assert response.status_code == 404

    async def test_someone_elses_run_is_404(self, async_client: AsyncClient, headers):
        run = {"job": "example", "status": "done", "error": None, "owner": "x@y.z"}
        with patch("api.router.get_run", AsyncMock(return_value=run)):
            response = await async_client.get("/api/runs/r1", headers=headers)
        assert response.status_code == 404


# stackkit:end auth_iap,auth_firebase
