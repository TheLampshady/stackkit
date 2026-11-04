# Background jobs

Work that runs, finishes and exits: a nightly summary, pulling data from another
site, AI reading a batch of documents. Each job runs on Cloud Run jobs, for up
to 24 hours, by hand or on a timer. There's no web server and no Docker: Google
builds each job from this folder.

## Add a job

1. Copy `jobs/example.py` to `jobs/<name>.py` (lowercase letters, digits and `_`).
2. Put the work in its `main()`, plain or `async`.
3. Add a test in `tests/` that calls `run("<name>")` with Google's services mocked,
   like `tests/test_example_job.py`.

Shared Google clients (the database, file storage, AI) come from `gcp_services/`,
a copy of `../shared/gcp_services/`. Edit them there, never here.

## Run it on this computer

```bash
make run-job JOB=<name>
```

It uses the project's `.env` and, with a database, the emulator (`make emulator`
in another terminal). To try a job split across tasks, set `CLOUD_RUN_TASK_INDEX`
and `CLOUD_RUN_TASK_COUNT`; `jobs.task_share()` reads them.

## Put it online

From the project root, with `PROJECT_ID` in `.env`:

| Command | What it does |
|---------|--------------|
| `make deploy-job JOB=<name>` | Builds the folder at Google and creates or updates the job. It doesn't run yet. |
| `make start-job JOB=<name>` | Runs it once, now |
| `make schedule-job JOB=<name> SCHEDULE="0 6 * * *" TIME_ZONE=Europe/London` | Runs it on a timer (cron). Run again to change the time. |
| `make job-runs JOB=<name>` | Lists recent runs |

Each job is named `<NAMESPACE>-<name>` at Google. One run may take up to
`TASK_TIMEOUT` (60 minutes by default, 24 hours at most) and is retried once if it
fails, so a job should be safe to run twice. `make -C gcp setup-iam` gives the job
its access, and lets Google's timer start it.
