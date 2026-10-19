import logging

from app_settings import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)


def add_cors_middleware(app: FastAPI) -> None:
    """
    Adds CORS middleware to the FastAPI application.

    Configures allowed origins, credentials, methods, and headers for cross-origin requests.
    Intended for both local development and deployed instances.

    :param app: FastAPI application instance to which the middleware will be added.
    :side effects: Modifies the FastAPI app by adding CORS middleware.
    """

    # CORS for deployed instances
    logger.info("Routing: Adding CORS middleware for deployed instance")
    origins = [
        f"https://{settings.project_id}.uc.r.appspot.com",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    allow_origin_regex = None
    if not settings.is_gae:
        # Allow dynamic Cloud Run subdomains in non-production (not GAE)
        allow_origin_regex = r"https://.+\.run\.app$"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def handle_utility_routes(app: FastAPI) -> None:
    """
    Handles the frontend for the FastAPI application.
    If a separate front-end URL is provided, it redirects all paths to that URL.

    If a single-page application (SPA) build exists in the static directory, serves it via
    ``app.frontend()``: real files are served directly, browser navigations to unknown paths
    fall back to ``index.html`` for client-side routing, and everything else gets a 404.

    :param app: FastAPI application instance
    :side effects: Registers routes on the FastAPI app.
    """

    @app.get("/_ah/warmup")
    async def warmup() -> str:
        """
        Served stub function returning no content. Used by App Engine to warm up instances.

        :return: String indicating warmup status.
        """
        return "Warmed Up!"

    if settings.front_end_url:
        logger.info(f"Routing: Adding redirect for FE: {settings.front_end_url}")

        @app.get("/{full_path:path}")
        async def frontend(full_path: str) -> RedirectResponse:
            """
            Redirects all unmatched routes to the configured frontend URL.

            :param full_path: Path to append to the frontend URL.
            :return: RedirectResponse to the frontend URL.
            """
            full_path = full_path or ""
            new_url = f"{settings.front_end_url.strip('/')}/{full_path}"
            return RedirectResponse(new_url)

    elif settings.static_dir.is_dir():
        logger.info(f"Routing: Using local static files from {settings.static_dir}")
        # Low-priority routes: API path operations are matched first. Path lookups are
        # normalised and confined to static_dir, and index.html is only served for
        # browser navigation requests so missing assets/API calls get a real 404.
        app.frontend("/", directory=settings.static_dir, fallback="index.html")
