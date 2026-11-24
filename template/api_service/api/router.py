from fastapi import APIRouter, Request

# stackkit:begin api
# stackkit:begin jobs
# stackkit:begin database
# stackkit:begin auth_iap,auth_firebase
from fastapi.exceptions import HTTPException

# stackkit:end auth_iap,auth_firebase
# stackkit:end database
# stackkit:end jobs
# stackkit:end api
# stackkit:begin database,storage
from gcp_services.clients import gcp_services

# stackkit:end database,storage
# stackkit:begin auth_firebase
from gcp_services.clients.fb_auth import firebase_auth_required

# stackkit:end auth_firebase
# stackkit:begin api
# stackkit:begin jobs
# stackkit:begin database
# stackkit:begin auth_iap,auth_firebase
from gcp_services.clients.gcp_runjob import JobBusyError, get_run, start_job

# stackkit:begin auth_iap
from gcp_services.clients.iap_auth import iap_auth_required

# stackkit:end auth_iap
# stackkit:end auth_iap,auth_firebase
# stackkit:end database
# stackkit:end jobs
# stackkit:end api
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
# stackkit:begin api
# stackkit:begin jobs
# stackkit:begin database
# stackkit:begin auth_iap,auth_firebase
# Background work the server starts: copy these for your own jobs. Users can't
# start a job themselves; the server's endpoints decide when, then call start_job.
# Keep a sign-in on them: an open start endpoint lets anyone run up the bill.
@api_router.post("/example-runs/", status_code=202)
# stackkit:begin auth_iap
@iap_auth_required()
# stackkit:end auth_iap
# stackkit:begin auth_firebase
@firebase_auth_required()
# stackkit:end auth_firebase
async def start_example_run(request: Request) -> dict[str, str]:
    """
    Start the example background job and answer at once with its run id.

    :param request: The incoming request
    :return: ``run_id``, for ``GET /api/runs/<run_id>``
    :raises HTTPException: 429 when the job already has its limit of runs going
    :side effects: Starts the ``example`` job (job_service/jobs/example.py)
    """
    try:
        run_id = await start_job("example", {}, owner=request.state.user["email"])
    except JobBusyError as error:
        raise HTTPException(429, "Busy: try again shortly") from error
    return {"run_id": run_id}


@api_router.get("/runs/{run_id}")
# stackkit:begin auth_iap
@iap_auth_required()
# stackkit:end auth_iap
# stackkit:begin auth_firebase
@firebase_auth_required()
# stackkit:end auth_firebase
async def run_status(request: Request, run_id: str) -> dict[str, str | None]:
    """
    How a background run is going: queued, running, retrying, done or failed.

    :param request: The incoming request
    :param run_id: The id ``start_job`` returned
    :return: The run's ``job``, ``status`` and ``error``
    :raises HTTPException: 404 when there's no such run, or it isn't the caller's
    """
    run = await get_run(run_id)
    if run is None or run.get("owner") != request.state.user["email"]:
        raise HTTPException(404, "No such run")
    return {"job": run["job"], "status": run["status"], "error": run.get("error")}


# stackkit:end auth_iap,auth_firebase
# stackkit:end database
# stackkit:end jobs
# stackkit:end api
