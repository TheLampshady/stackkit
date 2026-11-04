"""
Caller identity from Identity-Aware Proxy (IAP).

For deployments fronted by IAP (Cloud Run with ``--iap``, or App Engine behind
IAP). IAP authenticates the browser session and
forwards a signed ``x-goog-iap-jwt-assertion`` header; this module verifies it
and exposes the caller on ``request.state.user``.

Two ways to apply it, matching the two styles already used in the service:

- ``@iap_auth_required()`` protects a single endpoint.
- ``IdentityMiddleware`` protects every ``/api/`` path except the health check.

Deployed (GCP): the assertion is verified against the service's IAP audience
and the email comes from its claims.
Local: ``LOCAL_USER_EMAIL`` is the identity. It is ignored when deployed.

Pure functions come first and have no side effects; the verifier and the
decorator/middleware are the boundaries.
"""

import logging
from collections.abc import Callable, Mapping
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Literal, TypedDict

from app_settings import settings
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

IAP_EMAIL_HEADER = "x-goog-authenticated-user-email"
IAP_ASSERTION_HEADER = "x-goog-iap-jwt-assertion"
IAP_EMAIL_PREFIX = "accounts.google.com:"
IAP_ISSUER = "https://cloud.google.com/iap"
IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key"
METADATA_REGION_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/region"
)

PROTECTED_PREFIX = "/api/"
EXEMPT_PATHS = frozenset({"/api/healthcheck/"})

DETAIL_MISSING = "Missing identity"
DETAIL_INVALID = "Invalid identity"
DETAIL_NOT_CONFIGURED = "Identity not configured"
DETAIL_NOT_ALLOWED = "Account not allowed"
DETAIL_LOCAL_UNSET = "Set LOCAL_USER_EMAIL for local development"


class Identity(TypedDict):
    """The authenticated caller, set on ``request.state.user``."""

    email: str
    sub: str | None
    source: Literal["iap", "local"]


class IdentityError(Exception):
    """A request that must be rejected, with the HTTP status to use."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


Verifier = Callable[[str, str], Mapping[str, Any]]


# ----- Pure functions -----


def parse_iap_email(header_value: str | None) -> str | None:
    """
    Extracts the email from an IAP identity value.

    :param header_value: Raw value such as ``accounts.google.com:user@x.com``.
    :return: The lowercased email, or None when the value is empty.
    """
    if not header_value:
        return None
    value = header_value.strip()
    if value.lower().startswith(IAP_EMAIL_PREFIX):
        value = value[len(IAP_EMAIL_PREFIX) :]
    value = value.strip().lower()
    return value or None


def is_allowed_domain(email: str, valid_domains: list[str]) -> bool:
    """
    Checks the email's domain against the allow list.

    Entries are domains (``example.com``) or full addresses (``someone@gmail.com``),
    so a few people on personal accounts can be let in one by one.
    An empty allow list means no domain restriction: any email with a domain
    is accepted. Set ``VALID_DOMAINS=`` (blank) to opt into this.

    :param email: A lowercased email address.
    :param valid_domains: Lowercased domains that may use the app; empty for any.
    :return: True when the domain is allowed.
    """
    local, sep, domain = email.rpartition("@")
    if not (sep and local and domain):
        return False
    return not valid_domains or domain in valid_domains or email in valid_domains


def audience_from_region_path(region_path: str, service: str) -> str | None:
    """
    Builds the IAP audience from the metadata server's region path.

    :param region_path: Value of the ``instance/region`` metadata entry, in the
        form ``projects/<number>/regions/<region>``.
    :param service: The Cloud Run service name (``K_SERVICE``).
    :return: ``/projects/<number>/locations/<region>/services/<service>``, or
        None when the path is not in the expected form.
    """
    parts = region_path.strip().strip("/").split("/")
    if len(parts) != 4 or parts[0] != "projects" or parts[2] != "regions":
        return None
    project_number, region = parts[1], parts[3]
    if not project_number or not region or not service:
        return None
    return f"/projects/{project_number}/locations/{region}/services/{service}"


def is_protected_path(path: str) -> bool:
    """
    Decides whether a path requires an identity.

    :param path: The request path.
    :return: True for ``/api/`` paths other than the health endpoint.
    """
    return path.startswith(PROTECTED_PREFIX) and path not in EXEMPT_PATHS


def resolve_identity(
    headers: Mapping[str, str],
    *,
    is_gcp: bool,
    override_email: str | None,
    iap_audience: str | None,
    valid_domains: list[str],
    verify: Verifier,
) -> Identity:
    """
    Determines the caller from IAP headers (deployed) or the local override.

    :param headers: Lowercased request headers.
    :param is_gcp: Whether the process runs on GCP.
    :param override_email: ``LOCAL_USER_EMAIL``; used only when not on GCP.
    :param iap_audience: Expected JWT audience; required on GCP.
    :param valid_domains: Allowed email domains.
    :param verify: Callable that verifies the assertion and returns its claims.
    :return: The resolved identity.
    :raises IdentityError: With 401 or 403 per the identity contract.
    """
    if not is_gcp:
        if not override_email:
            raise IdentityError(401, DETAIL_LOCAL_UNSET)
        email = override_email.strip().lower()
        if not is_allowed_domain(email, valid_domains):
            raise IdentityError(403, DETAIL_NOT_ALLOWED)
        return Identity(email=email, sub=None, source="local")

    if not iap_audience:
        raise IdentityError(401, DETAIL_NOT_CONFIGURED)

    token = headers.get(IAP_ASSERTION_HEADER)
    if not token:
        raise IdentityError(401, DETAIL_MISSING)

    claims = verify(token, iap_audience)
    email = parse_iap_email(claims.get("email")) or parse_iap_email(
        headers.get(IAP_EMAIL_HEADER)
    )
    if not email:
        raise IdentityError(401, DETAIL_INVALID)
    if not is_allowed_domain(email, valid_domains):
        raise IdentityError(403, DETAIL_NOT_ALLOWED)

    sub = claims.get("sub")
    return Identity(email=email, sub=str(sub) if sub else None, source="iap")


# ----- Boundaries -----

_audience_cache: dict[str, str] = {}


def read_metadata_region() -> str:
    """
    Reads the instance region path from the Cloud Run metadata server.

    :return: ``projects/<number>/regions/<region>``.
    :raises Exception: Any transport error; callers treat it as "unknown".
    """
    import urllib.request

    request = urllib.request.Request(
        METADATA_REGION_URL, headers={"Metadata-Flavor": "Google"}
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return response.read().decode("utf-8")


def resolve_iap_audience() -> str | None:
    """
    Determines the expected IAP audience for this instance.

    An explicit ``IAP_AUDIENCE`` wins. Otherwise, on Cloud Run, the audience is
    derived once from the metadata server and ``K_SERVICE`` and cached.

    :return: The audience, or None when it cannot be determined (fail closed).
    :side effects: One metadata request per process; logs the outcome.
    """
    if settings.iap_audience:
        return settings.iap_audience
    service = settings.cloud_run_service
    if not settings.is_cloud_run or not service:
        return None
    if service in _audience_cache:
        return _audience_cache[service]
    try:
        audience = audience_from_region_path(read_metadata_region(), service)
    except Exception as exc:  # noqa: BLE001 - unknown audience fails closed
        logger.error("Identity: could not derive IAP audience: %r", exc)
        return None
    if audience is None:
        logger.error("Identity: metadata region path was not understood")
        return None
    logger.info("Identity: IAP audience %s", audience)
    _audience_cache[service] = audience
    return audience


def verify_iap_assertion(token: str, audience: str) -> Mapping[str, Any]:
    """
    Verifies an IAP JWT assertion against Google's IAP public keys.

    Imports the transport inside the function so nothing touches the network
    at import time.

    :param token: The ``x-goog-iap-jwt-assertion`` header value.
    :param audience: The expected audience for this Cloud Run service.
    :return: The verified claims.
    :raises IdentityError: 401 when the token fails verification.
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_token(
            token,
            google_requests.Request(),
            audience=audience,
            certs_url=IAP_CERTS_URL,
        )
    except Exception as exc:
        raise IdentityError(401, DETAIL_INVALID) from exc
    if claims.get("iss") != IAP_ISSUER:
        raise IdentityError(401, DETAIL_INVALID)
    return claims


def warn_if_override_ignored() -> None:
    """
    Logs once at startup when the local override is set on a deployed instance.

    :side effects: Emits a WARNING log line.
    """
    if settings.is_gcp and settings.local_user_email:
        logger.warning(
            "Identity: LOCAL_USER_EMAIL is set but ignored on deployed instances"
        )


def resolve_request_identity(headers: Mapping[str, str]) -> Identity:
    """
    Resolves the caller for a request using the live settings and verifier.

    Shared by the decorator and the middleware so both apply the same rules.

    :param headers: Lowercased request headers.
    :return: The resolved identity.
    :raises IdentityError: With 401 or 403 per the identity contract.
    """
    return resolve_identity(
        headers,
        is_gcp=settings.is_gcp,
        override_email=settings.local_user_email,
        iap_audience=resolve_iap_audience(),
        valid_domains=settings.valid_domains,
        verify=verify_iap_assertion,
    )


def iap_auth_required() -> Callable[..., Any]:
    """
    Decorator to secure FastAPI handlers with IAP. Attaches an
    :class:`Identity` to ``request.state.user``.

    :return: The decorator.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            """
            Resolves the IAP identity and attaches it to the request.

            :param request: The incoming request.
            :return: The wrapped handler's response.
            :raises HTTPException: 401 or 403 when the identity is rejected.
            """
            headers = {key.lower(): value for key, value in request.headers.items()}
            try:
                identity = resolve_request_identity(headers)
            except IdentityError as err:
                logger.warning(
                    "identity rejected method=%s path=%s reason=%s",
                    request.method,
                    request.url.path,
                    err.detail,
                )
                raise HTTPException(
                    status_code=err.status, detail=f"Auth Error: {err.detail}"
                ) from err

            request.state.user = identity

            if iscoroutinefunction(func):
                return await func(request, *args, **kwargs)
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


class IdentityMiddleware:
    """
    ASGI middleware that resolves the caller for protected ``/api/`` paths.

    On success it sets ``scope["state"]["user"]`` (``request.state.user``) and
    logs one line. On failure it answers with the contract's status and detail
    and logs the reason without the email.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not is_protected_path(scope["path"]):
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]
        method: str = scope.get("method", "")
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        try:
            identity = resolve_request_identity(headers)
        except IdentityError as err:
            logger.warning(
                "identity rejected method=%s path=%s reason=%s",
                method,
                path,
                err.detail,
            )
            response = JSONResponse({"detail": err.detail}, status_code=err.status)
            await response(scope, receive, send)
            return

        scope.setdefault("state", {})["user"] = identity
        logger.info(
            "request method=%s path=%s email=%s", method, path, identity["email"]
        )
        await self.app(scope, receive, send)
