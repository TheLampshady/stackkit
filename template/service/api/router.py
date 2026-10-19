from fastapi import APIRouter, Request
from gcp_services.clients.fb_auth import firebase_auth_required
from gcp_services.clients.gcp_services import bucket, db
from pydantic import BaseModel


class TextForm(BaseModel):
    text: str


api_router = APIRouter(
    prefix="/api",
)


@api_router.get("/")
@firebase_auth_required()
async def home(request: Request) -> dict[str, str]:
    return {"message": "Hello, World!"}


@api_router.post("/query/")
async def query(request: TextForm) -> dict[str, str]:
    # return the param "text" from the request body
    return {"message": request.text}


@api_router.get("/healthcheck/")
async def healthcheck(request: Request) -> dict[str, bool]:
    return {"success": True}


@api_router.get("/file-list/")
async def file_list(request: Request) -> dict[str, list[str]]:
    blobs = bucket.list_blobs()
    file_names = [blob.name for blob in blobs]
    return {"file_names": file_names}


@api_router.get("/db-list/")
async def db_list(request: Request) -> dict[str, list[str]]:
    collections = db.collections()
    db_ids = [collection.id async for collection in collections]
    return {"db_ids": db_ids}
