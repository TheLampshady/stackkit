"""Runs the example job with Google's services mocked."""

# stackkit:begin database
from unittest import mock

# stackkit:end database
from main import run


def test_example_job_runs(monkeypatch):
    # stackkit:begin database
    db = mock.MagicMock()
    db.collection.return_value.add = mock.AsyncMock()
    monkeypatch.setattr("gcp_services.clients.gcp_services.db", db)
    # stackkit:end database
    run("example")
    # stackkit:begin database
    assert db.collection.call_args.args[0] == "job_runs"
    assert db.collection.return_value.add.call_args.args[0]["job"] == "example"
    # stackkit:end database
