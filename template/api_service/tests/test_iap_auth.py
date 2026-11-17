"""
Tests for the IAP identity module.

Pure functions are tested directly. The decorator and middleware are tested
through small FastAPI apps with the settings and verifier patched, so nothing
touches the network or the metadata server.
"""

from collections.abc import Mapping
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from gcp_services.clients import iap_auth
from gcp_services.clients.iap_auth import (
    DETAIL_INVALID,
    DETAIL_LOCAL_UNSET,
    DETAIL_MISSING,
    DETAIL_NOT_ALLOWED,
    DETAIL_NOT_CONFIGURED,
    IAP_ASSERTION_HEADER,
    IAP_EMAIL_HEADER,
    IdentityError,
    IdentityMiddleware,
    audience_from_region_path,
    iap_auth_required,
    is_allowed_domain,
    is_protected_path,
    parse_iap_email,
    resolve_identity,
)
from httpx import ASGITransport, AsyncClient

DOMAINS = ["example.com"]
AUDIENCE = "/projects/123/locations/us-central1/services/svc"


def _verify_ok(token: str, audience: str) -> Mapping[str, Any]:
    assert audience == AUDIENCE
    return {"email": "user@example.com", "sub": "abc123"}


def _verify_fail(token: str, audience: str) -> Mapping[str, Any]:
    raise IdentityError(401, DETAIL_INVALID)


# ----- Pure functions -----


class TestParseIapEmail:
    def test_strips_prefix_and_lowercases(self):
        assert parse_iap_email("accounts.google.com:User@X.com") == "user@x.com"

    def test_plain_email(self):
        assert parse_iap_email(" a@b.com ") == "a@b.com"

    @pytest.mark.parametrize("value", [None, "", "  ", "accounts.google.com:"])
    def test_empty_values(self, value):
        assert parse_iap_email(value) is None


class TestIsAllowedDomain:
    def test_allowed(self):
        assert is_allowed_domain("user@example.com", DOMAINS)

    @pytest.mark.parametrize("email", ["user@evil.com", "nodomain", "@example.com "])
    def test_rejected(self, email):
        assert not is_allowed_domain(email, DOMAINS)

    def test_full_address_lets_one_person_in(self):
        allowed = ["example.com", "owner@gmail.com"]
        assert is_allowed_domain("owner@gmail.com", allowed)
        assert not is_allowed_domain("stranger@gmail.com", allowed)

    def test_empty_allow_list_allows_any_domain(self):
        assert is_allowed_domain("user@anywhere.org", [])

    def test_empty_allow_list_still_requires_a_domain(self):
        assert not is_allowed_domain("nodomain", [])


class TestAudienceFromRegionPath:
    def test_builds_audience(self):
        path = "projects/123/regions/us-central1"
        assert audience_from_region_path(path, "svc") == AUDIENCE

    def test_tolerates_slashes_and_whitespace(self):
        path = " /projects/123/regions/us-central1/ "
        assert audience_from_region_path(path, "svc") == AUDIENCE

    @pytest.mark.parametrize(
        "path",
        ["projects/123", "zones/123/regions/x", "projects//regions/x", ""],
    )
    def test_bad_paths(self, path):
        assert audience_from_region_path(path, "svc") is None

    def test_missing_service(self):
        assert audience_from_region_path("projects/1/regions/r", "") is None


class TestIsProtectedPath:
    def test_api_paths_protected(self):
        assert is_protected_path("/api/")
        assert is_protected_path("/api/db-list/")

    def test_healthcheck_exempt(self):
        assert not is_protected_path("/api/healthcheck/")

    def test_docs_protected(self):
        assert is_protected_path("/api/scalar")
        assert is_protected_path("/api/docs")
        assert is_protected_path("/api/openapi.json")

    def test_non_api_paths_open(self):
        assert not is_protected_path("/")
        assert not is_protected_path("/index.html")


class TestResolveIdentityLocal:
    def test_override_used(self):
        identity = resolve_identity(
            {},
            is_gcp=False,
            override_email=" Dev@Example.com ",
            iap_audience=None,
            valid_domains=DOMAINS,
            verify=_verify_fail,
        )
        assert identity == {"email": "dev@example.com", "sub": None, "source": "local"}

    def test_override_missing_is_401(self):
        with pytest.raises(IdentityError) as exc:
            resolve_identity(
                {},
                is_gcp=False,
                override_email=None,
                iap_audience=None,
                valid_domains=DOMAINS,
                verify=_verify_fail,
            )
        assert (exc.value.status, exc.value.detail) == (401, DETAIL_LOCAL_UNSET)

    def test_override_bad_domain_is_403(self):
        with pytest.raises(IdentityError) as exc:
            resolve_identity(
                {},
                is_gcp=False,
                override_email="dev@evil.com",
                iap_audience=None,
                valid_domains=DOMAINS,
                verify=_verify_fail,
            )
        assert (exc.value.status, exc.value.detail) == (403, DETAIL_NOT_ALLOWED)


class TestResolveIdentityGcp:
    def _resolve(self, headers, verify=_verify_ok, audience=AUDIENCE):
        return resolve_identity(
            headers,
            is_gcp=True,
            override_email="ignored@example.com",
            iap_audience=audience,
            valid_domains=DOMAINS,
            verify=verify,
        )

    def test_valid_assertion(self):
        identity = self._resolve({IAP_ASSERTION_HEADER: "tok"})
        assert identity == {
            "email": "user@example.com",
            "sub": "abc123",
            "source": "iap",
        }

    def test_override_ignored_on_gcp(self):
        with pytest.raises(IdentityError) as exc:
            self._resolve({})
        assert (exc.value.status, exc.value.detail) == (401, DETAIL_MISSING)

    def test_no_audience_fails_closed(self):
        with pytest.raises(IdentityError) as exc:
            self._resolve({IAP_ASSERTION_HEADER: "tok"}, audience=None)
        assert (exc.value.status, exc.value.detail) == (401, DETAIL_NOT_CONFIGURED)

    def test_bad_token_is_401(self):
        with pytest.raises(IdentityError) as exc:
            self._resolve({IAP_ASSERTION_HEADER: "tok"}, verify=_verify_fail)
        assert (exc.value.status, exc.value.detail) == (401, DETAIL_INVALID)

    def test_email_falls_back_to_header(self):
        def verify(token: str, audience: str) -> Mapping[str, Any]:
            return {"sub": "s"}

        identity = self._resolve(
            {
                IAP_ASSERTION_HEADER: "tok",
                IAP_EMAIL_HEADER: "accounts.google.com:Fallback@Example.com",
            },
            verify=verify,
        )
        assert identity["email"] == "fallback@example.com"

    def test_no_email_anywhere_is_401(self):
        def verify(token: str, audience: str) -> Mapping[str, Any]:
            return {"sub": "s"}

        with pytest.raises(IdentityError) as exc:
            self._resolve({IAP_ASSERTION_HEADER: "tok"}, verify=verify)
        assert exc.value.status == 401

    def test_wrong_domain_is_403(self):
        def verify(token: str, audience: str) -> Mapping[str, Any]:
            return {"email": "user@evil.com", "sub": "s"}

        with pytest.raises(IdentityError) as exc:
            self._resolve({IAP_ASSERTION_HEADER: "tok"}, verify=verify)
        assert exc.value.status == 403


class TestResolveIapAudience:
    def test_explicit_setting_wins(self):
        with patch.object(iap_auth.settings, "iap_audience", "explicit"):
            assert iap_auth.resolve_iap_audience() == "explicit"

    def test_not_cloud_run_is_none(self):
        with (
            patch.object(iap_auth.settings, "iap_audience", None),
            patch.object(iap_auth.settings, "is_cloud_run", False),
            patch.object(iap_auth.settings, "cloud_run_service", "svc"),
        ):
            assert iap_auth.resolve_iap_audience() is None

    def test_derived_and_cached(self):
        iap_auth._audience_cache.clear()
        with (
            patch.object(iap_auth.settings, "iap_audience", None),
            patch.object(iap_auth.settings, "is_cloud_run", True),
            patch.object(iap_auth.settings, "cloud_run_service", "svc"),
            patch.object(
                iap_auth,
                "read_metadata_region",
                return_value="projects/123/regions/us-central1",
            ) as read,
        ):
            assert iap_auth.resolve_iap_audience() == AUDIENCE
            assert iap_auth.resolve_iap_audience() == AUDIENCE
            assert read.call_count == 1
        iap_auth._audience_cache.clear()

    def test_metadata_failure_fails_closed(self):
        iap_auth._audience_cache.clear()
        with (
            patch.object(iap_auth.settings, "iap_audience", None),
            patch.object(iap_auth.settings, "is_cloud_run", True),
            patch.object(iap_auth.settings, "cloud_run_service", "svc"),
            patch.object(iap_auth, "read_metadata_region", side_effect=OSError("down")),
        ):
            assert iap_auth.resolve_iap_audience() is None


# ----- Boundaries: decorator and middleware -----


def _decorated_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/")
    @iap_auth_required()
    async def home(request: Request) -> dict[str, Any]:
        return dict(request.state.user)

    return app


def _middleware_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(IdentityMiddleware)

    @app.get("/api/")
    async def home(request: Request) -> dict[str, Any]:
        return dict(request.state.user)

    @app.get("/api/healthcheck/")
    async def healthcheck() -> dict[str, bool]:
        return {"success": True}

    return app


async def _get(app: FastAPI, path: str, headers: dict[str, str] | None = None):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers=headers)


@pytest.fixture
def local_identity():
    """Runs as a local process with LOCAL_USER_EMAIL set."""
    with (
        patch.object(iap_auth.settings, "is_gcp", False),
        patch.object(iap_auth.settings, "local_user_email", "dev@example.com"),
        patch.object(iap_auth.settings, "valid_domains", DOMAINS),
    ):
        yield


@pytest.fixture
def local_identity_unset():
    """Runs as a local process without LOCAL_USER_EMAIL."""
    with (
        patch.object(iap_auth.settings, "is_gcp", False),
        patch.object(iap_auth.settings, "local_user_email", None),
        patch.object(iap_auth.settings, "valid_domains", DOMAINS),
    ):
        yield


@pytest.fixture
def gcp_identity():
    """Runs as a deployed instance with a known audience and a stub verifier."""
    with (
        patch.object(iap_auth.settings, "is_gcp", True),
        patch.object(iap_auth.settings, "iap_audience", AUDIENCE),
        patch.object(iap_auth.settings, "valid_domains", DOMAINS),
        patch.object(iap_auth, "verify_iap_assertion", _verify_ok),
    ):
        yield


class TestIapAuthRequiredDecorator:
    async def test_local_override(self, local_identity):
        response = await _get(_decorated_app(), "/api/")
        assert response.status_code == 200
        assert response.json() == {
            "email": "dev@example.com",
            "sub": None,
            "source": "local",
        }

    async def test_local_unset_is_401(self, local_identity_unset):
        response = await _get(_decorated_app(), "/api/")
        assert response.status_code == 401
        assert DETAIL_LOCAL_UNSET in response.json()["detail"]

    async def test_gcp_valid_assertion(self, gcp_identity):
        response = await _get(
            _decorated_app(), "/api/", headers={IAP_ASSERTION_HEADER: "tok"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "user@example.com"
        assert response.json()["source"] == "iap"

    async def test_gcp_missing_assertion_is_401(self, gcp_identity):
        response = await _get(_decorated_app(), "/api/")
        assert response.status_code == 401
        assert DETAIL_MISSING in response.json()["detail"]


class TestIdentityMiddleware:
    async def test_local_override(self, local_identity):
        response = await _get(_middleware_app(), "/api/")
        assert response.status_code == 200
        assert response.json()["email"] == "dev@example.com"

    async def test_healthcheck_exempt(self, local_identity_unset):
        response = await _get(_middleware_app(), "/api/healthcheck/")
        assert response.status_code == 200

    async def test_gcp_missing_assertion_is_401(self, gcp_identity):
        response = await _get(_middleware_app(), "/api/")
        assert response.status_code == 401
        assert response.json() == {"detail": DETAIL_MISSING}

    async def test_gcp_valid_assertion(self, gcp_identity):
        response = await _get(
            _middleware_app(), "/api/", headers={IAP_ASSERTION_HEADER: "tok"}
        )
        assert response.status_code == 200
        assert response.json()["sub"] == "abc123"
