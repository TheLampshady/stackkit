"""Tests for the jobs CLI. Nothing here calls Google: commands run with --dry-run."""

import json
import subprocess

import pytest
from cli import app
from commands import common
from commands.listing import execution_state
from jobs import payload
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def project(monkeypatch):
    monkeypatch.setenv("PROJECT_ID", "demo")
    monkeypatch.delenv("NAMESPACE", raising=False)
    monkeypatch.delenv("REGION", raising=False)
    monkeypatch.delenv("JOB_PAYLOAD", raising=False)


def invoke(*args: str):
    return runner.invoke(app, ["--env-file", "/nonexistent", *args])


def test_job_id_uses_namespace_and_dashes():
    assert common.job_id("", "nightly_sync") == "nightly-sync"
    assert common.job_id("shop", "nightly_sync") == "shop-nightly-sync"


def test_payload_merges_file_and_pairs(tmp_path):
    file = tmp_path / "in.json"
    file.write_text('{"db": "file", "n": 3}')
    assert common.build_payload(["db=zach"], file) == {"db": "zach", "n": 3}


@pytest.mark.parametrize("pair", ["nokey", "=x"])
def test_payload_pair_needs_key_and_equals(pair):
    with pytest.raises(Exception, match="key=value"):
        common.build_payload([pair], None)


def test_payload_file_must_be_an_object(tmp_path):
    file = tmp_path / "in.json"
    file.write_text("[1]")
    with pytest.raises(Exception, match="JSON object"):
        common.build_payload([], file)


def test_env_flag_avoids_delimiters_in_value():
    flag = common.env_flag("JOB_PAYLOAD", '{"a": "x@y", "b": 1}')
    assert flag.startswith("--update-env-vars=^#^JOB_PAYLOAD=")


def test_run_body_sets_the_payload_variable():
    body = json.loads(common.run_body({"db": "zach"}))
    env = body["overrides"]["containerOverrides"][0]["env"][0]
    assert env["name"] == "JOB_PAYLOAD"
    assert json.loads(env["value"]) == {"db": "zach"}
    assert common.run_body({}) == "{}"


def test_settings_precedence():
    config = {
        "defaults": {"timeout": "30m", "memory": "1Gi"},
        "jobs": {"example": {"timeout": "5m", "schedules": []}},
    }
    got = common.deploy_settings(config, "example")
    assert got["timeout"] == "5m"
    assert got["memory"] == "1Gi"
    assert got["retries"] == 1
    assert "schedules" not in got


def test_timers_read_from_config():
    config = {
        "jobs": {
            "example": {
                "schedules": [
                    {"name": "morning", "cron": "0 6 * * *", "payload": {"db": "a"}},
                    {"cron": "0 8 * * 1", "time_zone": "Europe/London"},
                ]
            }
        }
    }
    first, second = common.timers_for(config, "example")
    assert common.timer_id("shop", first) == "shop-example-morning"
    assert common.timer_id("shop", second) == "shop-example"
    assert second.time_zone == "Europe/London"
    assert first.payload == {"db": "a"}


def test_shipped_toml_has_one_job_on_a_timer_and_one_without():
    config = common.load_config()
    assert set(config["jobs"]) <= set(common.known_jobs())
    assert len(common.timers_for(config, "example")) == 1
    assert common.timers_for(config, "backfill") == []
    assert common.deploy_settings(config, "backfill")["timeout"] == "6h"


def test_timer_id_adds_the_name():
    named = common.Timer("example", "morning_run", "0 6 * * *", "Etc/UTC", {})
    plain = common.Timer("example", None, "0 6 * * *", "Etc/UTC", {})
    assert common.timer_id("shop", named) == "shop-example-morning-run"
    assert common.timer_id("shop", plain) == "shop-example"


def test_run_remote_is_the_default_and_passes_payload():
    result = invoke("run", "example", "--payload", "db=zach", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "gcloud run jobs execute example" in result.output
    assert "--project=demo" in result.output
    assert "db" in result.output and "zach" in result.output


def test_project_id_flag_beats_env():
    result = invoke("--project-id", "other", "run", "example", "--dry-run")
    assert "--project=other" in result.output


def test_run_local_runs_main_with_payload(monkeypatch):
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("commands.run.subprocess.run", fake_run)
    result = invoke("run", "example", "--local", "--payload", "db=zach")
    assert result.exit_code == 0, result.output
    assert seen["command"][1:] == ["main.py", "example"]
    assert json.loads(seen["env"]["JOB_PAYLOAD"]) == {"db": "zach"}


def test_run_unknown_job_is_refused():
    assert invoke("run", "no_such_job", "--dry-run").exit_code != 0


def test_deploy_dry_run_uses_defaults_and_flags():
    result = invoke(
        "deploy", "example", "--timeout", "2h", "--memory", "2Gi", "--dry-run"
    )
    assert result.exit_code == 0, result.output
    assert "gcloud run jobs deploy example" in result.output
    assert "--task-timeout=2h" in result.output
    assert "--max-retries=1" in result.output
    assert "--memory=2Gi" in result.output
    assert "JOB_NAME=example" in result.output


def test_schedule_with_cron_sends_payload_body():
    result = invoke(
        "schedule", "example", "--cron", "0 6 * * *", "--name", "zach",
        "--payload", "db=zach", "--dry-run",
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "scheduler jobs create http example-zach" in result.output
    assert "JOB_PAYLOAD" in result.output
    assert "jobs/example:run" in result.output


def test_schedule_uses_the_timers_in_the_toml():
    result = invoke("schedule", "example", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "scheduler jobs create http example " in result.output
    assert "--schedule=0 6 * * *" in result.output
    assert "JOB_PAYLOAD" in result.output


def test_schedule_all_skips_jobs_without_timers():
    result = invoke("schedule", "--all", "--dry-run")
    assert result.exit_code == 0, result.output
    assert result.output.count("scheduler jobs create http") == 1


def test_schedule_a_job_with_no_timer_needs_a_cron():
    result = invoke("schedule", "backfill", "--dry-run")
    assert result.exit_code != 0
    assert "No timers" in result.output


def test_schedule_flags_need_a_cron():
    assert invoke("schedule", "example", "--name", "x", "--dry-run").exit_code != 0


def test_schedule_name_is_checked():
    result = invoke("schedule", "example", "--cron", "* * * * *", "--name", "Bad Name")
    assert result.exit_code != 0


def test_unschedule_deletes_the_named_timer():
    result = invoke("unschedule", "example", "--name", "zach", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "scheduler jobs delete example-zach" in result.output


def test_payload_helper_reads_the_variable(monkeypatch):
    assert payload() == {}
    monkeypatch.setenv("JOB_PAYLOAD", '{"db": "zach"}')
    assert payload() == {"db": "zach"}
    monkeypatch.setenv("JOB_PAYLOAD", "[1]")
    with pytest.raises(TypeError):
        payload()


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ({"runningCount": 1}, "running"),
        ({}, "pending"),
        ({"completionTime": "t", "succeededCount": 1}, "succeeded"),
        ({"completionTime": "t", "failedCount": 1}, "failed"),
    ],
)
def test_execution_state(status, expected):
    assert execution_state({"status": status}) == expected
