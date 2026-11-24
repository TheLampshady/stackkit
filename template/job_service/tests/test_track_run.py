"""Runs the server starts report back to their job_runs entry."""

import asyncio
from unittest import mock

import pytest
from gcp_services.clients import gcp_runjob

from main import run


@pytest.fixture
def saved(monkeypatch):
    """Catch what track_run saves instead of writing to Firestore."""
    set_status = mock.AsyncMock()
    finish_run = mock.AsyncMock()
    monkeypatch.setattr(gcp_runjob, "set_status", set_status)
    monkeypatch.setattr(gcp_runjob, "finish_run", finish_run)
    monkeypatch.setenv("JOB_RUN_ID", "r1")
    return set_status, finish_run


def fake_job(monkeypatch, error: Exception | None = None) -> None:
    """Make the example job's main() succeed, or raise ``error``."""
    main = mock.Mock(side_effect=error)
    monkeypatch.setattr("jobs.example.main", main)


def test_done(monkeypatch, saved):
    set_status, finish_run = saved
    fake_job(monkeypatch)
    run("example")
    assert set_status.call_args.args == ("r1", "running")
    assert finish_run.call_args.args == ("example", "r1", "done")


def test_last_try_failed(monkeypatch, saved):
    _, finish_run = saved
    fake_job(monkeypatch, ValueError("bad input"))
    with pytest.raises(ValueError):
        run("example")
    assert finish_run.call_args.args == ("example", "r1", "failed")
    assert "bad input" in finish_run.call_args.kwargs["error"]


def test_a_try_cloud_run_repeats_is_retrying(monkeypatch, saved):
    set_status, finish_run = saved
    monkeypatch.setenv("MAX_RETRIES", "1")
    monkeypatch.setenv("CLOUD_RUN_TASK_ATTEMPT", "0")
    fake_job(monkeypatch, ValueError("flaky"))
    with pytest.raises(ValueError):
        run("example")
    assert set_status.call_args.args == ("r1", "retrying")
    finish_run.assert_not_called()


def test_exit_with_an_error_code_fails(monkeypatch, saved):
    _, finish_run = saved
    fake_job(monkeypatch, SystemExit(1))
    with pytest.raises(SystemExit):
        run("example")
    assert finish_run.call_args.args == ("example", "r1", "failed")


def test_exit_0_is_done(monkeypatch, saved):
    _, finish_run = saved
    fake_job(monkeypatch, SystemExit(0))
    with pytest.raises(SystemExit):
        run("example")
    assert finish_run.call_args.args == ("example", "r1", "done")


def test_a_plain_main_may_call_asyncio_run(monkeypatch, saved):
    _, finish_run = saved

    async def save() -> None: ...

    monkeypatch.setattr("jobs.example.main", lambda: asyncio.run(save()))
    run("example")
    assert finish_run.call_args.args == ("example", "r1", "done")


def test_a_failed_save_after_the_work_doesnt_fail_the_run(monkeypatch, saved):
    _, finish_run = saved
    finish_run.side_effect = RuntimeError("Firestore is down")
    monkeypatch.setattr(gcp_runjob, "SAVE_TRIES", 2)
    monkeypatch.setattr(gcp_runjob.asyncio, "sleep", mock.AsyncMock())
    fake_job(monkeypatch)
    run("example")  # doesn't raise, so Cloud Run won't run the job again
    assert finish_run.call_count == 2
