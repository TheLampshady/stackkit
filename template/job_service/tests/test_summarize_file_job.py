"""Runs the summarize_file job with storage, the model and the database mocked."""

from unittest import mock

import pytest
from gcp_services.clients.gcp_vertex import StructuredReply
from jobs import summarize_file

from main import run


@pytest.fixture
def services(monkeypatch):
    blob = mock.MagicMock()
    blob.content_type = "application/pdf"
    blob.download_as_bytes.return_value = b"%PDF fake"
    bucket = mock.MagicMock()
    bucket.name = "demo-bucket"
    bucket.get_blob.return_value = blob
    db = mock.MagicMock()
    db.collection.return_value.add = mock.AsyncMock()
    reply = StructuredReply(
        parsed=None,
        raw_json={"summary": "A report.", "key_points": ["one"]},
        input_tokens=10,
        output_tokens=5,
        latency_ms=120,
        model="gemini-test",
    )
    vertex = mock.MagicMock()
    vertex.generate_structured = mock.AsyncMock(return_value=reply)
    monkeypatch.setattr(summarize_file, "bucket", bucket)
    monkeypatch.setattr(summarize_file, "db", db)
    monkeypatch.setattr(summarize_file, "vertex", vertex)
    return bucket, db, vertex


def test_reads_the_file_asks_the_model_and_saves(monkeypatch, services):
    bucket, db, vertex = services
    monkeypatch.setenv("JOB_PAYLOAD", '{"file": "report.pdf"}')
    run("summarize_file")

    bucket.get_blob.assert_called_once_with("jobs/report.pdf")
    args, kwargs = vertex.generate_structured.call_args
    assert args[0] == summarize_file.DEFAULT_INSTRUCTION
    assert kwargs["files"][0].mime_type == "application/pdf"
    assert kwargs["files"][0].data == b"%PDF fake"

    db.collection.assert_called_once_with("file_summaries")
    saved = db.collection.return_value.add.call_args.args[0]
    assert saved["file"] == "jobs/report.pdf"
    assert saved["response"]["summary"] == "A report."
    assert saved["model"] == "gemini-test"
    assert saved["size_bytes"] == len(b"%PDF fake")


def test_folder_instruction_and_model_come_from_the_input(monkeypatch, services):
    bucket, _, vertex = services
    monkeypatch.setenv(
        "JOB_PAYLOAD",
        '{"file": "a.pdf", "folder": "/inbox/", "instruction": "Who signed?", "model": "m"}',
    )
    run("summarize_file")
    bucket.get_blob.assert_called_once_with("inbox/a.pdf")
    args, kwargs = vertex.generate_structured.call_args
    assert args[0] == "Who signed?"
    assert kwargs["model"] == "m"


def test_needs_a_file_name(monkeypatch, services):
    monkeypatch.delenv("JOB_PAYLOAD", raising=False)
    with pytest.raises(ValueError):
        run("summarize_file")


def test_missing_file_is_reported(monkeypatch, services):
    bucket, db, _ = services
    bucket.get_blob.return_value = None
    monkeypatch.setenv("JOB_PAYLOAD", '{"file": "nope.pdf"}')
    with pytest.raises(FileNotFoundError, match="jobs/nope.pdf"):
        run("summarize_file")
    db.collection.return_value.add.assert_not_called()
