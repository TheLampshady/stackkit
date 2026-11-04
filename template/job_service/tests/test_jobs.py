"""Tests for the job runner and the example job."""

import pytest
from jobs import task_share

from main import run


def test_task_share_defaults_to_one_task(monkeypatch):
    monkeypatch.delenv("CLOUD_RUN_TASK_INDEX", raising=False)
    monkeypatch.delenv("CLOUD_RUN_TASK_COUNT", raising=False)
    assert task_share() == (0, 1)


def test_task_share_reads_cloud_run_variables(monkeypatch):
    monkeypatch.setenv("CLOUD_RUN_TASK_INDEX", "2")
    monkeypatch.setenv("CLOUD_RUN_TASK_COUNT", "5")
    assert task_share() == (2, 5)


@pytest.mark.parametrize("name", ["../app_settings", "Example", "os.path", ""])
def test_run_rejects_names_that_are_not_jobs(name):
    with pytest.raises(ValueError):
        run(name)


def test_run_unknown_job_fails():
    with pytest.raises(ModuleNotFoundError):
        run("no_such_job")
