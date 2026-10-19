from fastapi import APIRouter, Request

# stackkit:begin database,storage
from gcp_services.clients import gcp_services

# stackkit:end database,storage
# stackkit:begin auth_firebase
from gcp_services.clients.fb_auth import firebase_auth_required

# stackkit:end auth_firebase
from pydantic import BaseModel


class TextForm(BaseModel):
    text: str


api_router = APIRouter(
    prefix="/api",
)


@api_router.get("/")
# stackkit:begin auth_firebase
@firebase_auth_required()
# stackkit:end auth_firebase
async def home(request: Request) -> dict[str, str]:
    return {"message": "Hello, World!"}


@api_router.post("/query/")
async def query(request: TextForm) -> dict[str, str]:
    # return the param "text" from the request body
    return {"message": request.text}


@api_router.get("/healthcheck/")
async def healthcheck(request: Request) -> dict[str, bool]:
    return {"success": True}


# stackkit:begin storage
@api_router.get("/file-list/")
async def file_list(request: Request) -> dict[str, list[str]]:
    blobs = gcp_services.bucket.list_blobs()
    file_names = [blob.name for blob in blobs]
    return {"file_names": file_names}


# stackkit:end storage
# stackkit:begin database
@api_router.get("/db-list/")
async def db_list(request: Request) -> dict[str, list[str]]:
    collections = gcp_services.db.collections()
    db_ids = [collection.id async for collection in collections]
    return {"db_ids": db_ids}


# stackkit:end database
