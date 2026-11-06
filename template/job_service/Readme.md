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
| `app_settings.py` | What the job's code reads at run time (project, secrets). Shared with the other services through `gcp_services/`. |
| `gcp_services/` | A copy of `../shared/gcp_services/` (database, storage, AI clients). Never edit it here; edit `shared/` and run `make sync`. |
| `Makefile` | Short `make` commands that call `cli.py`. |
| `Procfile` | Tells Google's build how to start the job (`python main.py`). |
| `pyproject.toml` | This folder's Python packages. |
| `tests/` | Tests, run with Google's services mocked. |
| `.gcloudignore` | Files left out of what's sent to Google. |

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

## Limits

Set in `job_service.toml` (`[defaults]` for every job, `[jobs.<name>]` for one), or
with a flag on `deploy` (`--timeout`, `--retries`, `--tasks`, `--cpu`, `--memory`).
A flag beats the job's table, which beats `[defaults]`, which beats the built-in
values: one run stops after 60 minutes (24 hours at most), and is retried once if
it fails, so a job should be safe to run twice. `make -C gcp setup-iam` gives the
job its access, and lets Google's timer start it.
