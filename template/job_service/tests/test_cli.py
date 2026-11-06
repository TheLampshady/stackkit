"""Tests for the jobs CLI. Nothing here calls Google: commands run with --dry-run."""

import json
import subprocess

import pytest
import typer
from cli import app
from commands import common
from commands.listing import execution_state, job_rows, runs_to_list
from commands.schedule import timer_args, timers_to_set
from typer.testing import CliRunner

runner = CliRunner()

CONFIG = {
    "defaults": {"timeout": "30m"},
    "jobs": {
        "example": {
            "timeout": "5m",
            "schedules": [{"cron": "0 6 * * *", "payload": {"db": "a"}}],
        },
        "backfill": {"memory": "2Gi"},
    },
}


@pytest.fixture(autouse=True)
def project(monkeypatch):
    monkeypatch.setenv("PROJECT_ID", "demo")
    monkeypatch.delenv("NAMESPACE", raising=False)
    monkeypatch.delenv("REGION", raising=False)
    monkeypatch.delenv("JOB_PAYLOAD", raising=False)
    # The CLI reads this config, not the shipped job_service.toml
    monkeypatch.setattr("cli.load_config", lambda: CONFIG)


def invoke(*args: str):
    return runner.invoke(app, ["--env-file", "/nonexistent", *args])


def timer(job: str = "example", name: str | None = None, **payload) -> common.Timer:
    return common.Timer(job, name, "0 6 * * *", "Etc/UTC", payload)


STATE = common.State(project_id="demo", namespace="shop", region="europe-west1")


# ---- names at Google ----


def test_job_id_uses_namespace_and_dashes():
    assert common.job_id("", "nightly_sync") == "nightly-sync"
    assert common.job_id("shop", "nightly_sync") == "shop-nightly-sync"


@pytest.mark.parametrize("namespace", ["Shop", "my shop", "x" * 60])
def test_job_id_refuses_names_cloud_run_wont_take(namespace):
    with pytest.raises(typer.BadParameter):
        common.job_id(namespace, "example")


def test_timer_id_adds_the_name():
    assert common.timer_id("shop", timer(name="morning_run")) == (
        "shop-example_morning_run"
    )
    assert common.timer_id("shop", timer()) == "shop-example"


def test_timer_ids_of_different_jobs_never_collide():
    # Job a with timer b, and job a_b with no timer name
    assert common.timer_id("", timer("a", "b")) != common.timer_id("", timer("a_b"))


# ---- job_service.toml ----


def test_settings_precedence():
    got = common.deploy_settings(CONFIG, "example")
    assert got["timeout"] == "5m"
    assert got["retries"] == common.BUILT_IN["retries"]
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
    assert (first.name, first.payload) == ("morning", {"db": "a"})
    assert (second.name, second.time_zone) == (None, "Europe/London")


@pytest.mark.parametrize(
    "entry", [{"name": "morning"}, {"cron": "0 6 * * *", "name": "Bad Name"}]
)
def test_timers_need_a_cron_and_a_good_name(entry):
    with pytest.raises(typer.BadParameter):
        common.timers_for({"jobs": {"example": {"schedules": [entry]}}}, "example")


def test_shipped_toml_is_valid():
    config = common.load_config()
    jobs = config.get("jobs", {})
    assert set(jobs) <= set(common.known_jobs())
    ids = []
    for job in jobs:
        settings = common.deploy_settings(config, job)
        assert int(settings["retries"]) >= 0
        assert int(settings["tasks"]) >= 1
        ids += [common.timer_id("", t) for t in common.timers_for(config, job)]
    assert len(ids) == len(set(ids))


# ---- input ----


def test_payload_merges_file_and_pairs(tmp_path):
    file = tmp_path / "in.json"
    file.write_text('{"db": "file", "n": 3}')
    assert common.build_payload(["db=zach"], file) == {"db": "zach", "n": 3}


@pytest.mark.parametrize("pair", ["nokey", "=x"])
def test_payload_pair_needs_key_and_equals(pair):
    with pytest.raises(typer.BadParameter):
        common.build_payload([pair], None)


def test_payload_file_must_be_an_object(tmp_path):
    file = tmp_path / "in.json"
    file.write_text("[1]")
    with pytest.raises(typer.BadParameter):
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


# ---- timers ----


@pytest.mark.parametrize(
    ("action", "flag"), [("create", "--headers="), ("update", "--update-headers=")]
)
def test_timer_args_name_the_header_flag_for_the_action(action, flag):
    args = timer_args(STATE, timer(db="zach"), "123", action)
    assert args[:5] == ["scheduler", "jobs", action, "http", "shop-example"]
    assert any(a.startswith(flag) for a in args)
    assert "--location=europe-west1" in args
    assert any("jobs/shop-example:run" in a for a in args)
    assert (
        "--oauth-service-account-email=123-compute@developer.gserviceaccount.com"
        in args
    )


def test_timers_to_set_from_flags():
    (only,) = timers_to_set(CONFIG, ["backfill"], "* * * * *", "x", None, {"a": 1})
    assert (only.job, only.name, only.payload) == ("backfill", "x", {"a": 1})
    assert only.time_zone == common.DEFAULT_TIME_ZONE


def test_timers_to_set_from_the_toml_skips_jobs_without_timers():
    timers = timers_to_set(CONFIG, ["backfill", "example"], None, None, None, {})
    assert [t.job for t in timers] == ["example"]


@pytest.mark.parametrize(
    ("names", "cron", "name", "payload"),
    [
        (["example", "backfill"], "* * * * *", None, {}),  # --cron with --all
        (["example"], "* * * * *", "Bad Name", {}),  # bad timer name
        (["example"], None, "x", {}),  # --name without --cron
        (["example"], None, None, {"a": 1}),  # input without --cron
        (["backfill"], None, None, {}),  # no timers in the toml
    ],
)
def test_timers_to_set_refuses(names, cron, name, payload):
    with pytest.raises(typer.BadParameter):
        timers_to_set(CONFIG, names, cron, name, None, payload)


# ---- listing ----


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ({"runningCount": 1}, "running"),
        ({}, "pending"),
        ({"completionTime": "t", "succeededCount": 1}, "succeeded"),
        ({"completionTime": "t", "failedCount": 1}, "failed"),
        ({"completionTime": "t", "cancelledCount": 1}, "cancelled"),
    ],
)
def test_execution_state(status, expected):
    assert execution_state({"status": status}) == expected


def test_job_rows_match_online_jobs_and_their_timers():
    timers = [
        {
            "name": "projects/p/locations/l/jobs/shop-example",
            "schedule": "0 6 * * *",
            "state": "PAUSED",
            "httpTarget": {"uri": "https://run/v2/.../jobs/shop-example:run"},
        }
    ]
    rows = {
        r[0]: r
        for r in job_rows(["example", "backfill"], "shop", {"shop-example"}, timers)
    }
    assert rows["example"][1] == "yes"
    assert "shop-example" in rows["example"][2] and "paused" in rows["example"][2]
    assert rows["backfill"][1:] == ("no", "-")


def test_runs_cover_only_online_jobs():
    jobs = ["backfill", "example"]
    assert runs_to_list(None, jobs, "shop", {"shop-example"}) == ["example"]
    assert runs_to_list("example", jobs, "shop", {"shop-example"}) == ["example"]
    with pytest.raises(typer.BadParameter):
        runs_to_list("backfill", jobs, "shop", {"shop-example"})


# ---- commands: wiring only ----


def test_run_remote_is_the_default_and_passes_payload():
    result = invoke("run", "example", "--payload", "db=zach", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "gcloud run jobs execute example" in result.output
    assert "--project=demo" in result.output
    assert "db" in result.output and "zach" in result.output


def test_project_id_flag_beats_env():
    result = invoke("--project-id", "other", "run", "example", "--dry-run")
    assert "--project=other" in result.output


def test_region_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("REGION", "europe-west1")
    result = invoke("run", "example", "--dry-run")
    assert "--region=europe-west1" in result.output


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


def test_deploy_dry_run_uses_config_and_flags():
    result = invoke("deploy", "example", "--memory", "2Gi", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "gcloud run jobs deploy example" in result.output
    assert "--task-timeout=5m" in result.output
    assert "--memory=2Gi" in result.output
    assert "JOB_NAME=example" in result.output


def test_schedule_sets_the_timers_from_flags_or_config():
    result = invoke("schedule", "example", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "scheduler jobs create http example " in result.output
    result = invoke(
        "schedule", "example", "--cron", "0 6 * * *", "--name", "zach",
        "--payload", "db=zach", "--dry-run",
    )  # fmt: skip
    assert "scheduler jobs create http example_zach" in result.output
    assert "zach" in result.output.split("--message-body=")[1]


def test_bad_schedule_flags_fail_the_command():
    assert invoke("schedule", "backfill", "--dry-run").exit_code != 0


def test_unschedule_deletes_the_named_timer():
    result = invoke("unschedule", "example", "--name", "zach", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "scheduler jobs delete example_zach" in result.output
