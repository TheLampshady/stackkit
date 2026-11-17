"""
Reads a file from Cloud Storage, asks Gemini about it, and saves the answer.

The file is named in the run's input. It's read from the project's storage
bucket, in the ``jobs`` folder unless the input says another::

    make start-job JOB=summarize_file ARGS="--payload file=report.pdf"
    make run-job   JOB=summarize_file ARGS="--payload file=report.pdf --payload folder=inbox"

Input (``--payload key=value``):

- ``file``: the file's name in the folder. Required.
- ``folder``: the folder in the bucket. Default ``jobs``.
- ``instruction``: what to ask. Default: summarize it and list the key points.
- ``model``: a model id. Default is the project's ``DEFAULT_TEXT_MODEL``.

Each run adds one document to the ``file_summaries`` collection: the file, the
instruction, the model's answer, and what the call cost. Copy this file to make
a job that reads a file and asks a model something about it.
"""

import asyncio
import logging
import mimetypes
from datetime import UTC, datetime

from gcp_services.clients.gcp_services import bucket, db
from gcp_services.clients.gcp_vertex import FileInput, vertex
from pydantic import BaseModel, Field

from jobs import payload

logger = logging.getLogger(__name__)

DEFAULT_FOLDER = "jobs"
DEFAULT_INSTRUCTION = (
    "Summarize this file in a short paragraph and list its key points."
)
COLLECTION = "file_summaries"


class FileSummary(BaseModel):
    """The shape of the model's answer."""

    summary: str = Field(description="A short summary of the file")
    key_points: list[str] = Field(description="The most important points, one each")


async def main() -> None:
    """
    Read the named file, ask the model about it, and save the answer.

    :raises ValueError: If the input has no ``file``
    :raises FileNotFoundError: If the file isn't in the bucket
    :side effects: Reads the file from Cloud Storage, makes a model call, and
        adds a document to ``file_summaries``
    """
    options = payload()
    name = str(options.get("file") or "").strip("/")
    if not name:
        raise ValueError("Name the file: --payload file=<name in the bucket>")
    folder = str(options.get("folder") or DEFAULT_FOLDER).strip("/")
    instruction = str(options.get("instruction") or DEFAULT_INSTRUCTION)
    path = f"{folder}/{name}"

    blob = await asyncio.to_thread(bucket.get_blob, path)
    if blob is None:
        raise FileNotFoundError(f"{path} isn't in the bucket {bucket.name}")
    data = await asyncio.to_thread(blob.download_as_bytes)
    mime_type = (
        blob.content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
    )
    logger.info("Read %s (%s, %s bytes)", path, mime_type, len(data))

    reply = await vertex.generate_structured(
        instruction,
        FileSummary,
        model=options.get("model") or None,
        files=[FileInput(data=data, mime_type=mime_type)],
    )

    await db.collection(COLLECTION).add(
        {
            "file": path,
            "bucket": bucket.name,
            "mime_type": mime_type,
            "size_bytes": len(data),
            "instruction": instruction,
            "response": reply.raw_json,
            "model": reply.model,
            "input_tokens": reply.input_tokens,
            "output_tokens": reply.output_tokens,
            "latency_ms": reply.latency_ms,
            "created_at": datetime.now(UTC),
        }
    )
    logger.info("Saved the answer for %s to %s", path, COLLECTION)
