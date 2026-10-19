#!/usr/.config/env python
import logging

from api.config_app import add_cors_middleware, handle_utility_routes
from api.router import api_router

# Required for loading
from app_settings import settings
from fastapi import FastAPI

# stackkit:begin firebase
from gcp_services.clients.gcp_services import *

# stackkit:end firebase
from pydantic import BaseModel
from scalar_fastapi import get_scalar_api_reference

logger = logging.getLogger(__name__)


class TextForm(BaseModel):
    text: str


# Docs live under /api so the frontend's dev proxy forwards them and IAP protects them in deploys
app = FastAPI(
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS for deployed instances
if not settings.is_local:
    add_cors_middleware(app)


# API routes take priority over the SPA frontend registered below
app.include_router(api_router)


@app.get("/api/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="stackkit-app API",
    )


handle_utility_routes(app)

if __name__ == "__main__":
    import uvicorn

    logger.info("Running: FastAPI app locally with uvicorn")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
