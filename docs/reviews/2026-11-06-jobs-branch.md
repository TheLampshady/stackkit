# Review: background jobs, shared clients and shared settings

**Date:** 2026-11-06 · **Branch:** `claude/zen-hamilton-6dpcrm` · **Against:** `main`

Six commits: `ee6d1f2` (rename `service/` to `api_service/`), `bb8c749` (shared Google clients), `1dd065c` (the `job_service` module), `a2cee6b` (interview questions 7 and 7b), `3031e5c` (shared `CoreSettings`), `68e5012` (the jobs CLI).

Two passes: a correctness review of the diff, then a review against the template's constitution (`template/.specify/memory/constitution.md`, 3.11.0). Every finding below was fixed on the branch unless it's under "Open questions" or "Left as is".

## Correctness

| # | Where | Problem | Fix |
|---|---|---|---|
| 1 | `job_service/commands/schedule.py` | Re-running `schedule` for a timer that exists called `gcloud scheduler jobs update http` with `--headers`, which only `create` takes, so a timer could never be changed. | `timer_args` passes `--update-headers` on update. Tested for both actions. |
| 2 | `template/Makefile` | The new `sync:` rule came before `setup:`, so bare `make` ran `sync` instead of `setup`. | The rule moved below `setup`. |
| 3 | `job_service/commands/listing.py` | `runs` with no job queried every job in `jobs/`; the first one not deployed made gcloud fail and ended the command. | `runs_to_list` shows only the jobs that are online, and refuses a named job that isn't. |
| 4 | `skills/create/scripts/bootstrap.py`, `template/Makefile` | Adding `jobs` to a project made before `shared/` merged in `typecheck-jobs: sync` with no `sync` rule, so `make check` failed. | Service targets depend on `$(SYNC)`, which only projects with `shared/` define. Checked by hand (below). |
| 5 | `skills/create/scripts/status.py` | `secret_names` read only `api_service/` and `agent_service/`, so a job's secrets never reached the checklist. | It reads every `*_service/app_settings.py`, plus the old `service/`. |
| 6 | `template/shared/sync.sh` | A copy newer than the shared file counted as "edited directly". `git pull` and checkout make files newer, so a teammate's commit could stop every `make check`. | A copy is edited by hand only if it's newer *and* has uncommitted changes. Checked by hand in a scratch repo: a pull, an edit-sync-edit-sync, and a hand edit. |
| 7 | `shared/gcp_services/clients/gcp_vertex.py` | Gemini got the file's type as given (`text/plain; charset=utf-8`), while the Claude path cleaned it up first. | One `media_type()` for both. |
| 8 | `job_service/commands/listing.py` | A cancelled run showed as "succeeded". | `execution_state` returns `cancelled`. |
| 9 | `job_service/commands/common.py` | `job_id` accepted an uppercase `NAMESPACE` that Cloud Run rejects. Job `a` with timer `b` and job `a_b` got the same timer id. | `job_id` checks the name against Cloud Run's rule. Timer ids are `<job id>_<timer name>`; the job id has no `_`, so ids can't collide. |
| 10 | `job_service/commands/*.py` | Command docstrings had no `:param:` or `:side effects:` fields (template `AGENTS.md`). | Added after a `\f`, which Typer's help leaves out. |

Finding 9 changes timer names at Google from `<job>-<name>` to `<job>_<name>`. That's a breaking change, made outright because nothing has shipped yet (constitution: "No Backwards Compatibility Before First Release"). A named timer created before this change has to be removed by hand.

## Against the constitution

| Principle | Problem | Fix |
|---|---|---|
| Reuse Before You Write | The job-name pattern was in `main.py` and `commands/common.py`; `"JOB_PAYLOAD"` was in `jobs/__init__.py` and `commands/common.py`. | Both live in `jobs/__init__.py`, which is deployed; the CLI imports them from there. |
| Reuse Before You Write | Cleaning up a file's type was written only for Claude (correctness #7). | `media_type()`. |
| Test Economy 6: decision logic in pure functions | Which timers to set, the arguments for a timer, the `list` rows and which jobs `runs` covers were all decided inside command bodies. | `timers_to_set`, `timer_args`, `job_rows` and `runs_to_list`, each tested directly. The CLI tests check wiring only. |
| Test Economy 1 and 8: one place per behavior, find the owner | `jobs.payload()` was tested in `test_cli.py`. `timer_id` was checked in two tests. The schedule CLI tests re-checked validation. | `payload()` moved to `test_jobs.py`. The `timer_id` checks were merged into one test. Validation is tested once, on `timers_to_set`. |
| Change-Tolerant 1: app data isn't test data | A test pinned the shipped `job_service.toml`: one timer for `example`, none for `backfill`, a `6h` timeout. CLI tests read the shipped file too. | `test_shipped_toml_is_valid` checks invariants on every record: known jobs, valid settings, valid timers, unique timer ids. CLI tests use their own config. |
| Change-Tolerant 5: outcomes, not call sequences | The example job's test asserted the logger and `db.collection` were each called once. | It asserts the collection and the record written. |
| Copy-Resilient Tests | `match=` on messages ("key=value", "JSON object", "Name the file", "can't read"), `"No timers" in output`, and a whole log message. | Exception types and values from the test's input. |
| Required Test Coverage | `list`, `runs`, the schedule update path and Gemini's file handling had no tests. | Covered through the new pure functions. |
| One knob per fact | The region could be set in `job_service.toml` as well as `REGION`, which the other services' Makefiles read. | The toml key is gone. `REGION` in `.env` (or `--region`) is the only setting. |
| Platform defaults over explicit flags | `--http-method=POST` restated gcloud's default. | Dropped. `--tasks` and `--time-zone` stay: an update keeps the old value when a flag is left off, so removing one from the toml wouldn't reset it. |
| Living docs | The constitution named `VALID_DOMAINS` in `fb_auth.py`, agents in `api_service/agents/`, and `SECRET_KEY_NAMES` in `gcp_secrets.py`. All three moved. | Patched to 3.11.1. |

## Open questions for the owner

The constitution asks for these to be raised, not decided ("Ask before inventing infrastructure"):

1. **Google APIs for jobs.** Nothing enables `cloudscheduler.googleapis.com` (or the Cloud Run and Cloud Build APIs) before the first `deploy-job` or `schedule-job`. That relies on gcloud offering to enable them, and under `--quiet` the offer may be declined. Should `gcp` provisioning enable them, or should the docs list them as a setup step?
2. **`roles/run.invoker` for the Compute Engine default account, project-wide.** Timers start jobs as that account. A project-wide grant also lets anything running as that account invoke every Cloud Run service in the project, including an IAP-protected server. Grant it per job instead, or use a dedicated timer account? The constitution's "no custom service accounts unless asked" favours the per-job grant.

## Left as is

- **Import-time secrets** (Import-Time Safety). `job_service/app_settings.py` calls `load_secrets` at import on Google, as `api_service` and `agent_service` do. With the `"TODO"` placeholder, each start looks up a secret named `TODO` and logs a warning. It's the boilerplate's pattern ("Do not change what works"), so it should change for every service at once or not at all.
- **Environment reads outside `Settings`** (Settings-Driven Configuration). `cli.py` reads `PROJECT_ID`, `NAMESPACE` and `REGION` directly, and `jobs.payload()` and `task_share()` read `JOB_PAYLOAD` and `CLOUD_RUN_TASK_*`. The CLI is developer tooling that runs outside the service, and those variables are per-run input from Cloud Run, not configuration. A line in the constitution saying so would settle it.
- **Fewest moving parts.** The jobs CLI (six Typer commands and a toml) is more machinery than a documented `gcloud` command. It's what `68e5012` set out to build; it's noted here so that the choice is deliberate.
- **The backfill test reads the log call.** Logging its input is all that job does. The test checks that the input appears in the log call's arguments, not the wording.

## Verification

- `job_service`: 60 tests pass; `ruff check`, `ruff format --check` and `ty check` are clean.
- `make test-bootstrap` passes.
- Fix 4, by hand: a project built by the stackkit at `a61a4a6` (an API, no `shared/`), then `--add database,jobs`. The Makefile, `AGENTS.md` and `Readme.md` come back as conflicts with diffs, because the older files differ from the current template next to where the jobs lines go. That's the designed path: `create` applies such diffs by hand. With the Makefile diff applied, `make typecheck-jobs test-jobs` passes. With the old `typecheck-jobs: sync` it would stop at "No rule to make target 'sync'". `make test-bootstrap` still adds only a database to the older project, because a case that ends in hand merges can't run unattended.
