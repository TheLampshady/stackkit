"""Runs the example job with Google's services mocked."""

from unittest import mock

from jobs import example

from main import run


def test_example_job_runs(monkeypatch):
    # stackkit:begin database
    db = mock.MagicMock()
    db.collection.return_value.add = mock.AsyncMock()
    monkeypatch.setattr("gcp_services.clients.gcp_services.db", db)
    # stackkit:end database
    info = mock.MagicMock()
    monkeypatch.setattr(example.logger, "info", info)
    run("example")
    info.assert_called_once()
    # stackkit:begin database
    db.collection.assert_called_once_with("job_runs")
    # stackkit:end database
