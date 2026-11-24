"""
Stands in for Cloud Run on this computer, so the server can start jobs locally.

The server's ``gcp_runjob.start_job`` asks Cloud Run to run a job. With
``USE_EMULATOR`` it asks this instead, and each run is ``python main.py <job>``
here with the same input, reporting to the Firestore emulator. ``make emulator``
starts it. Only for this computer: it isn't deployed (``.gcloudignore``).

Usage::

    uv run --package job_service python emulator.py
"""

import itertools
import json
import logging
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app_settings import settings
from jobs import NAME_RE

logger = logging.getLogger("job_emulator")

JOB_DIR = Path(__file__).resolve().parent
# Cloud Run's "run a job" call: POST /v2/projects/<p>/locations/<l>/jobs/<job>:run
RUN_PATH_RE = re.compile(r"^/v2/(projects/[^/]+/locations/[^/]+)/jobs/([^/:?]+):run")
counter = itertools.count(1)


def module_name(cloud_run_job: str, namespace: str | None) -> str:
    """
    Turn a job's name at Google back into its module in ``jobs/``.

    :param cloud_run_job: Such as ``myapp-summarize-file``
    :param namespace: The project's NAMESPACE, or None
    :return: Such as ``summarize_file``
    """
    # cloud_run_name() turns the namespace's _ into - too
    prefix = f"{namespace}-".replace("_", "-") if namespace else ""
    return cloud_run_job.removeprefix(prefix).replace("-", "_")


def overrides_env(body: dict[str, Any]) -> dict[str, str]:
    """
    Read the variables a ``:run`` request sets for the run.

    :param body: The request's JSON
    :return: Variable names and values
    """
    env = {}
    for container in body.get("overrides", {}).get("containerOverrides", []):
        for var in container.get("env", []):
            env[var["name"]] = var.get("value", "")
    return env


def start(name: str, env: dict[str, str]) -> subprocess.Popen[bytes]:
    """
    Run one job in the background, as Cloud Run would.

    :param name: A module name in ``jobs/``
    :param env: Variables for the run, such as ``JOB_PAYLOAD``
    :return: The running process
    :side effects: Starts ``python main.py <name>``
    """
    run_env = os.environ | env | {"CLOUD_RUN_TASK_ATTEMPT": "0", "MAX_RETRIES": "0"}
    process = subprocess.Popen(
        [sys.executable, "main.py", name], cwd=JOB_DIR, env=run_env
    )
    # Collect its exit so finished runs don't linger
    threading.Thread(target=process.wait, daemon=True).start()
    return process


class Handler(BaseHTTPRequestHandler):
    """Answers the one Cloud Run call the server makes."""

    def do_POST(self) -> None:
        """
        Start the job named in the path and answer like Cloud Run.

        :side effects: Starts the job as a process
        """
        match = RUN_PATH_RE.match(self.path)
        if not match:
            self.reply(404, {"error": {"code": 404, "message": "Not a :run call"}})
            return
        parent, cloud_run_job = match.groups()
        name = module_name(cloud_run_job, settings.namespace)
        if not NAME_RE.match(name) or not (JOB_DIR / "jobs" / f"{name}.py").exists():
            message = f"No job {name!r} in job_service/jobs/"
            self.reply(404, {"error": {"code": 404, "message": message}})
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        start(name, overrides_env(body))
        execution = f"{parent}/jobs/{cloud_run_job}/executions/local-{next(counter)}"
        logger.info("Started %s as %s", name, execution)
        self.reply(
            200,
            {
                "name": f"{parent}/operations/local-{next(counter)}",
                "done": False,
                "metadata": {
                    "@type": "type.googleapis.com/google.cloud.run.v2.Execution",
                    "name": execution,
                },
            },
        )

    def reply(self, status: int, data: dict[str, Any]) -> None:
        """
        Send a JSON answer.

        :param status: The HTTP status
        :param data: The body
        :side effects: Writes the response
        """
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        """
        Quiet http.server's own request log; starts are logged instead.

        :param format: Unused
        :param args: Unused
        """


def main() -> None:
    """
    Listen on ``CLOUD_RUN_EMULATOR_HOST`` (default ``127.0.0.1:8090``).

    :side effects: Serves until stopped
    """
    host, _, port = (
        os.environ.get("CLOUD_RUN_EMULATOR_HOST") or "127.0.0.1:8090"
    ).rpartition(":")
    server = ThreadingHTTPServer((host, int(port)), Handler)
    logger.info("Jobs emulator on %s:%s", host, port)
    server.serve_forever()


if __name__ == "__main__":
    main()
