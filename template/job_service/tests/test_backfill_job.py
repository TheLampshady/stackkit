"""Runs the backfill job with input."""

from unittest import mock

from jobs import backfill

from main import run


def test_backfill_job_logs_its_input(monkeypatch):
    monkeypatch.setenv("JOB_PAYLOAD", '{"db": "main"}')
    info = mock.MagicMock()
    monkeypatch.setattr(backfill.logger, "info", info)
    run("backfill")
    info.assert_called_once_with("Backfill job started with input %s", {"db": "main"})
