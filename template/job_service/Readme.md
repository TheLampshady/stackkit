# Background jobs

Work that runs, finishes and exits: a nightly summary, pulling data from another
site, AI reading a batch of documents. Each job runs on Cloud Run jobs, for up
to 24 hours, by hand or on a timer. There's no web server and no Docker: Google
builds each job from this folder.

## What's in this folder

| File | What it is |
|------|------------|
| `jobs/` | **Your work.** One file per job, each with a `main()`. `example.py` is the pattern to copy. |
| `main.py` | Runs one job by name (`python main.py example`) and exits. Google runs it too, with `JOB_NAME` saying which job. |
| `job_service.toml` | **How each job is put online:** timeout, retries, CPU, memory, and its timers with their inputs. Only `cli.py` reads it. Ships with two jobs: `example` on a timer and `backfill` with none. |
| `cli.py`, `commands/` | The command line for deploying, running and scheduling jobs. Run `make cli ARGS="--help"`. |
| `app_settings.py` | What the job's code reads at run time (project, secrets), built on `gcp_services/base_settings.py`. |
| `gcp_services/` | This folder's own copy of the Google clients (database, storage, AI) and the settings every service has. Another service's copy is separate: a fix both need goes in each. |
| `Makefile` | Short `make` commands that call `cli.py`. |
| `Procfile` | Tells Google's build how to start the job (`python main.py`). |
| `pyproject.toml` | This folder's Python packages. |
| `tests/` | Tests, run with Google's services mocked. |
| `.gcloudignore` | Files left out of what's sent to Google. |
| `emulator.py` | Stands in for Cloud Run on this computer, so the server's `start_job` runs jobs here. `make emulator` starts it; it isn't deployed. |

Every job is the same hosting: one folder, built the same way. A job is a Cloud
Run job at Google named `<NAMESPACE>-<name>` (dashes for `_`) that runs `jobs/<name>.py`.
A timer is a separate Google Scheduler entry that starts one job, named after the job
plus `_<timer name>` when it has one; deleting a timer leaves
the job, and a job can have several timers.

## Add a job

1. Copy `jobs/example.py` to `jobs/<name>.py` (lowercase letters, digits and `_`).
2. Put the work in its `main()`, plain or `async`.
3. Add a test in `tests/` that calls `run("<name>")` with Google's services mocked,
   like `tests/test_example_job.py`.

Shared Google clients (the database, file storage, AI) come from `gcp_services/`.

Two more examples to copy. `jobs/backfill.py` has no timer and reads its input with
`payload()`. `jobs/summarize_file.py` reads a file from the project's storage bucket
(folder `jobs` unless `--payload folder=...`), asks the AI model about it, and saves
the answer, with the file, instruction, model and token counts, in the
`file_summaries` collection:

```bash
make start-job JOB=summarize_file ARGS="--payload file=report.pdf"
make run-job JOB=summarize_file ARGS="--payload file=report.pdf --payload instruction='Who signed it?'"
```

## Giving a job input (a payload)

A run can carry input, such as `db=zach`. The job reads it with `payload()`:

```python
from jobs import payload


async def main() -> None:
    db = payload().get("db")
```

It's `{}` when the run was given none. Give input these ways, all landing in
`payload()`: `--payload key=value` (repeat for more), `--json file.json`, or a
`payload = { ... }` on a timer in `job_service.toml`. With both flags,
`--payload` keys win over the file.

## Run it

```bash
make run-job JOB=<name>                                  # on this computer
make start-job JOB=<name> ARGS="--payload db=zach"       # at Google, now
make start-job JOB=<name> ARGS="--json input.json --wait"  # wait until it ends
```

Locally it uses the project's `.env` and, with a database, the emulator (`make emulator`
in another terminal). `run --local` / `--remote` is the same switch the make
targets pick for you; remote is the default for `cli.py run`. To try a job split
across tasks, set `CLOUD_RUN_TASK_INDEX` and `CLOUD_RUN_TASK_COUNT`; `jobs.task_share()`
reads them. A local run reads `PROJECT_ID` from `.env`; `--project-id` only
changes which project the Google commands use.

## Put it online

From the project root, with `PROJECT_ID` in `.env`. Each step is separate: deploy,
start and schedule can happen in any order, and a manual start doesn't disturb a timer.

| Command | What it does |
|---------|--------------|
| `make deploy-job JOB=<name>` | Builds the folder at Google and creates or updates the job. It doesn't run yet. `ALL=1` does every job. |
| `make start-job JOB=<name>` | Runs it once, now |
| `make schedule-job JOB=<name>` | Sets the timers listed for it in `job_service.toml`. `ALL=1` sets every timer. |
| `make schedule-job JOB=<name> SCHEDULE="0 6 * * *" TIME_ZONE=Europe/London` | Sets one timer without the toml. Add `ARGS="--name zach --payload db=zach"` to name it and give it input. |
| `make unschedule-job JOB=<name> ARGS="--name zach"` | Removes a timer (the job stays) |
| `make list-jobs` | Each job in `jobs/`, whether it's online, and its timers |
| `make job-runs JOB=<name> ARGS="--active"` | Recent runs, or only the ones in progress. Leave `JOB` off with `ALL=1` for every job that's online. |

Any other flag goes in `ARGS`, and `--dry-run` on a command that changes something
prints the `gcloud` commands without running them. Jobs and timers go in `REGION` from
`.env` (default `us-central1`), like the other services; `make list-jobs REGION=europe-west1`
overrides it for one command.
`NAMESPACE` must be lowercase letters, digits and `-`, as Cloud Run names are.

One job with several timers: add one `[[jobs.<name>.schedules]]` block per timer in
`job_service.toml`, each with a different `name`, its `cron` and its `payload`, then
`make schedule-job JOB=<name>`. A job with no block has no timer and is started by
hand, like `backfill`. Google holds the real state; the file is what `deploy` and
`schedule` push there, so run them again after editing it, and `make list-jobs`
shows what's online.

<!-- stackkit:begin api -->
<!-- stackkit:begin jobs -->
<!-- stackkit:begin database -->
## Started by the server

People never start a job themselves. The server's own endpoints decide when, then
call `start_job` from `gcp_services/clients/gcp_runjob.py`:

```python
from gcp_services.clients.gcp_runjob import JobBusyError, get_run, start_job

run_id = await start_job("summarize_file", {"file": "report.pdf"}, key=f"report:{uid}")
run = await get_run(run_id)  # run["status"]: queued, running, retrying, done or failed
```

- It answers at once with a run id; the job keeps going at Google. `/api/example-runs/` in `api_service/api/router.py` is the pattern. It comes only with a sign-in, and so should yours: an endpoint anyone can call lets anyone run up the bill.
- `owner`: who started it (the example saves the caller's email). The example's `GET /api/runs/<id>` shows a run only to its owner.
- Each run is a document in `job_runs`. The job keeps its `status` up to date itself (`main.py` does it for every job), and saves `failed` only after its last try.
- `key`: one run with that key at a time. Starting it again while one is going returns the same run id.
- `limit` (10 by default): runs of one job going at once. Past it, `start_job` raises `JobBusyError`; answer 429 (busy).
- `deadline` (2 hours by default): the job's timeout times its tries. A run not finished by then stopped without reporting back (out of time or memory), and `get_run` calls it `failed`. Change it when the job's timeout or retries do: the `backfill` example (6h, 1 retry) needs `deadline=timedelta(hours=12)`.
- Jobs put online before the server could start them need `make deploy-job` again, so they know their retry count (`MAX_RETRIES`).
- People can't read `job_runs` or `job_limits` (`gcp/firestore.rules` blocks them); the page asks the server.
- Locally, `make emulator` also starts `emulator.py`, which runs each job on this computer against the local database.

<!-- stackkit:end database -->
<!-- stackkit:end jobs -->
<!-- stackkit:end api -->
## Limits

Set in `job_service.toml` (`[defaults]` for every job, `[jobs.<name>]` for one), or
with a flag on `deploy` (`--timeout`, `--retries`, `--tasks`, `--cpu`, `--memory`).
A flag beats the job's table, which beats `[defaults]`, which beats the built-in
values: one run stops after 60 minutes (24 hours at most), and is retried once if
it fails, so a job should be safe to run twice. `make -C gcp setup-iam` gives the
job its access, and lets Google's timer start it.
