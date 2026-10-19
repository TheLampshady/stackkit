import logging
from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any

from app_settings import settings
from fastapi import HTTPException, Request

from .gcp_services import auth_client

logger = logging.getLogger(__name__)

VALID_DOMAINS = settings.valid_domains


def firebase_auth_required(is_admin: bool = False) -> Callable[..., Any]:
    """
    Decorator to secure FastAPI handlers with Firebase Authentication.
    Optionally checks if the user has admin privileges.
    Attaches a user object to the request.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            """
            Processes the auth bearer token and attaches the user object to the request.
            - Verifies Firebase Auth Tokens
            :param request:
            :param args:
            :param kwargs:
            :return:
            """

            # Extract the token from the Authorization header
            auth_header = request.headers.get("Authorization") or ""
            try:
                user = _get_user(auth_header)
            except Exception as e:
                logger.warning(e)
                raise HTTPException(
                    status_code=401, detail="Auth Error: Invalid or expired token"
                ) from e

            # Check for admin privileges if required
            if not _verify_email(user["email"], is_admin):
                raise HTTPException(
                    status_code=403, detail="Auth Error: Account not valid"
                )

            # Attach user object to the request
            request.state.user = user

            # Call the original function
            if iscoroutinefunction(func):
                return await func(request, *args, **kwargs)
            else:
                return func(request, *args, **kwargs)

        return wrapper

    return decorator


def _get_user(auth_header: str) -> dict[str, Any]:
    """
    Extracts the user details from the Firebase token in the header.

    :param auth_header:
    :return:
    """

    # Verify the ID token with Firebase
    decoded_token = _get_claim_from_headers(auth_header)
    email = decoded_token.get("email")
    if not email:
        raise ValueError("No email found in token")

    # Retrieve user details from Firebase
    firebase_user = auth_client.get_user(decoded_token["uid"])

    return {
        "uid": decoded_token["uid"],
        "email": firebase_user.email,
        "display_name": firebase_user.display_name,
        "admin": decoded_token.get("admin", False),
        "claims": decoded_token,
    }


def _get_claim_from_headers(auth_header: str) -> dict[str, Any]:
    """
    Verifies the Auth token and returns the claims.
        - the auth bearer token from the Authorization header
        - Verifies the token

    The frontend client will need to use the emulator for the audience to match

    https://google-auth.readthedocs.io/en/stable/reference/google.oauth2.id_token.html # noqa
    :param auth_header: string with token at the end.
    :return: claims object
    """
    if not auth_header:
        raise ValueError("Unauthorized")

    id_token = auth_header.split("Bearer ").pop()
    claims: dict[str, Any] = auth_client.verify_id_token(id_token)
    if not claims:
        raise ValueError("Unauthorized")
    return claims


def _verify_email(email: str, is_admin: bool = False) -> bool:
    """
    Performs checks on the email for access.

    An empty ``VALID_DOMAINS`` list means no domain restriction.

    :param email: The caller's email address.
    :param is_admin: Whether the endpoint requires admin privileges.
    :return: True when the account may access the endpoint.
    """
    email = email.strip().lower()
    local, sep, domain = email.rpartition("@")
    if not (sep and local and domain):
        return False
    if VALID_DOMAINS and domain not in VALID_DOMAINS:
        return False

    return not is_admin
