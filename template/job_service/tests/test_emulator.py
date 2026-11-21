"""The local stand-in for Cloud Run reads the server's :run call like Google."""

from emulator import RUN_PATH_RE, module_name, overrides_env


def test_reads_the_job_from_the_path():
    match = RUN_PATH_RE.match(
        "/v2/projects/p/locations/l/jobs/shop-summarize-file:run?x"
    )
    assert match is not None
    assert match.groups() == ("projects/p/locations/l", "shop-summarize-file")
    assert module_name("shop-summarize-file", "shop") == "summarize_file"
    assert module_name("summarize-file", None) == "summarize_file"


def test_reads_the_run_variables():
    body = {
        "overrides": {
            "containerOverrides": [
                {
                    "env": [
                        {"name": "JOB_RUN_ID", "value": "r1"},
                        {"name": "JOB_PAYLOAD", "value": "{}"},
                    ]
                }
            ]
        }
    }
    assert overrides_env(body) == {"JOB_RUN_ID": "r1", "JOB_PAYLOAD": "{}"}
