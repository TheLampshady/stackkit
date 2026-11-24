# Modules: the map

Start here when you lose track. Every project stackkit makes is the template
with some modules taken out. This page lists them all in plain words, and says
where each one's files are.

`template/stackkit.toml` is where these facts are kept. Change this page whenever
a module is added, renamed or changes what it needs; `make test-bootstrap`
fails if a module is missing here.

## Words

| Word | Means |
|---|---|
| **Module** (or part) | An optional feature a project can have, such as `database` or `jobs`. Every module is a choice made in the interview, except the automatic ones. |
| **Automatic module** | Never asked about (`implicit` in the manifest). It comes and goes with the modules that need it. |
| **Folder** | Where code lives. Some modules own a whole folder (`jobs` owns `job_service/`). Others are a few files plus some marked lines in shared files. |
| **Service** | A `*_service/` folder that deploys to Google on its own: `api_service` (the server), `job_service` (background jobs), `agent_service` (AI agents). |
| **Marker** | A comment pair, `stackkit:begin <module>` … `stackkit:end <module>`, around the lines a module adds to a shared file. When the module is removed, the lines between go. |
| **Manifest** | `template/stackkit.toml`: each module's files, markers, what it needs, and words that mustn't survive its removal. Deleted from every project. |
| **`SAMPLE_SPECS`** | The test list in the root `Makefile`. Each entry is `name:modules-to-remove`, and `make test-bootstrap` builds that project and checks it. `all-modules:` removes nothing. Between them, every module is tested both kept and removed. |
| **`shared/gcp_services/`** | The single source for the Google clients. `make sync` copies it into each service, because each deploys only its own folder. |

## The modules

"Needs" means it can't be kept without those; "one of" means at least one of them.

| Module | What it is | How it's chosen | Needs | Its own files |
|---|---|---|---|---|
| `api` | The server (FastAPI). Without it, the project is a static site. | Asked: questions 2, 7 and 7b | `gcp`, `iam` | `api_service/` |
| `frontend` | A web page people open in a browser (React). | Asked: question 2 | | `frontend/` |
| `database` | Saves records between visits (Firestore). | Asked: question 3 | `firebase`; one of `api`, `jobs` | `gcp/firestore.rules`, `gcp/bin/sync_db.sh` and other database scripts |
| `storage` | Keeps uploaded files such as photos and PDFs (Cloud Storage). | Asked: question 4 | `firebase`; one of `api`, `jobs` | `gcp_services/clients/gcp_storage.py`, `gcp/storage.rules`, `gcp/cors.json` |
| `auth_iap` | Team-only access: Google's sign-in in front of the whole app. | Asked: question 5 | | `gcp_services/clients/iap_auth.py`, `gcp/bin/setup_iap.sh` |
| `auth_firebase` | Accounts people sign up for (Firebase Auth), server side only. | Asked: question 5 | `api`, `firebase` | `gcp_services/clients/fb_auth.py` |
| `ai` | One-off AI calls (Gemini or Claude on Vertex AI). | Asked: question 6 | one of `api`, `jobs` | `gcp_services/clients/gcp_vertex.py` |
| `agents` | AI assistants that hold a conversation and act (Google ADK). | Asked: question 6b | `ai`, `database`, `iam` | `agent_service/` |
| `jobs` | Background work that runs, finishes and exits: by hand, on a timer, or started by the server (Cloud Run jobs). | Asked: questions 7 and 7b | `gcp`, `iam` | `job_service/` |
| `gae` | Hosting on App Engine: its own web address, no streaming. | Asked: question 8 | `gcp`; one of `api`, `frontend` | `api_service/app.yaml`, `frontend/app.yaml`, `gcp/dispatch.yaml` |
| `cloud_run` | Hosting the server on Cloud Run: scales to zero, streams replies. | Asked: question 8 | `api` | `api_service/Procfile` |
| `always_on` | Keeps one server running so visits never wait. Costs more. | Asked: question 9 | `api` | none: settings in `api_service/Makefile` and `app.yaml` |
| `http_tests` | Hand-run requests for the PyCharm HTTP client. | Comes with `api` | `api` | `http_tests/` |
| `notebooks` | Jupyter notebooks for AI experiments. For developers. | Removed unless a developer asks | `ai` | `notebooks/` |
| `firebase` | The Firebase app and its local emulator, shared by the database, storage and accounts. | Automatic: kept while `database`, `storage` or `auth_firebase` is | `gcp` | `gcp_services/clients/gcp_services.py`, `gcp/firebase.json`, `gcp/bin/emulator.sh` |
| `iam` | The script that grants each service's Google account its roles. | Automatic: kept while a service needs it | | `gcp/bin/setup_iam.sh` |
| `gcp` | The `gcp/` tooling folder: emulator, setup scripts, App Engine helpers. | Automatic: kept while anything needs it | | `gcp/` |

**Files that need several modules** are listed under each of them, and go when
any one is removed. For example, the server starting jobs (`start_job` in
`gcp_services/clients/gcp_runjob.py`, and `job_service/emulator.py`, which runs
them locally) is listed under `api`, `jobs` and `database`, so a project gets it
exactly when it has all three. Lines inside shared files work the same way, with
one marker inside another.

Besides its own files, almost every module adds marked lines to shared files:
the root `Makefile`, `.env.sample`, `pyproject.toml` files, `gcp/bin/setup_iam.sh`
and the docs. To find all of one module's lines, search the template for
`stackkit:begin <module>`.

## How a project gets its modules

1. **The interview** (`skills/stackkit/SKILL.md`) asks the questions above and
   works out which modules to remove. [`INTERVIEW.md`](INTERVIEW.md) diagrams it.
2. **`bootstrap.py`** copies the template, removes those modules (their files and
   marked lines), and removes any automatic module that's no longer needed.
   With `--add`, it puts modules back into an existing project instead.
3. **`check.py`** installs the project and runs its checks.

[`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) covers each step in detail.
