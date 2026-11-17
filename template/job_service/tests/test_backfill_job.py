"""Runs the backfill job with input."""

from unittest import mock

from jobs import backfill

from main import run


def test_backfill_job_logs_its_input(monkeypatch):
    monkeypatch.setenv("JOB_PAYLOAD", '{"db": "main"}')
    info = mock.MagicMock()
    monkeypatch.setattr(backfill.logger, "info", info)
    run("backfill")
    # The job hands its input to the log; the message's wording is copy
    assert {"db": "main"} in info.call_args.args
