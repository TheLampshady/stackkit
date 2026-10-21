# Bootstrap choices

Every decision the `bootstrap` interview makes, and what each one does to the project `create` builds. The interview wording and defaults live in `skills/bootstrap/SKILL.md`; the module footprints live in `template/stackkit.toml`. This page explains the effects. If those files change, update it.

## At a glance

| # | Question (plain words) | Default | Becomes | Effect |
|---|------------------------|---------|---------|--------|
| 1 | What should this do, and who is it for? | none | the brief | Supplies the defaults for every later question |
| 2 | What should we call it? | 2–3 words from the brief | `--display-name`, `--name` (kebab-case) | Renames placeholders, sets `NAMESPACE` and the default folder |
| 3 | Will people open it in a web browser? | yes if the brief mentions people, a site, a page or a dashboard | no → `--remove frontend` | Keeps or drops the React app |
| 4 | Should it have an AI assistant that acts on its own? | no, unless the brief asks for AI that acts or chats | no → `--remove agents` | Keeps or drops the ADK agent service |
| 5 | Who can sign in: anyone, or only your organization? | anyone | `VALID_DOMAINS` | Sets which email domains may sign in |
| 6 | Do you have a Google Cloud project already? | not yet | `PROJECT_ID`, `USE_EMULATOR` | Runs on local emulators or connects to real GCP |
| 7 | Where should I put it? | `~/projects/<kebab-name>` | `--dest` | Sets where the project is created |
| — | *(not asked)* | — | `--remove notebooks,http_tests` | Developer-only modules are dropped |
| — | *(not asked)* | — | `NAMESPACE=<kebab-name>` | Names the GCP resources |

## The questions

### 1. The brief

Nothing is written from the brief directly. It sets the default the interview offers for every later question, and any question the brief already answers is skipped (the skill says what it assumed).

Some briefs steer the plan:

- **"Just an API", or a backend for someone else's app:** no frontend.
- **A chatbot people talk to in the browser:** keep both frontend and agents.
- **An internal team tool:** suggest organization-only sign-in at question 5.
- **Something the stack can't do** (a phone app, a game, hardware): say so plainly, then offer the closest thing it can build, such as the backend a phone app would talk to.
- **Two different apps:** build the first and offer the second afterwards. Each run makes one project.

### 2. Name

Becomes two values, both from `[values]` in `stackkit.toml`:

| Value | Replaces | Where |
|-------|----------|-------|
| `--name` (`bakery-orders`) | `stackkit-app` | every `pyproject.toml`, `uv.lock`, `main.py`, `.run/Service.run.xml`, `Readme.md` |
| `--display-name` (`Bakery Orders`) | `Stackkit App` | API title in `service/app.py`, the frontend header (`HomePage.tsx`) and its test |

The kebab-case name also becomes `NAMESPACE` (see [Always, without asking](#always-without-asking)) and the default folder at question 7.

### 3. Browser page → `frontend` module

**Yes (keep):** the React + Vite app in `frontend/` stays, and the `frontend` marker blocks stay in the root `Makefile`, `.env.sample` and the pre-commit config.

- `make setup`, `build`, `lint`, `format`, `typecheck`, `test` and `check` also run their `-fe` targets.
- `make build` builds the frontend into `service/static/`, so the FastAPI service serves the page at http://localhost:8000.
- `make run` builds the frontend and then serves it from the backend. If `FRONT_END_URL` is set in `.env`, it runs the backend and the Vite dev server side by side instead, which gives hot reload.
- `create`'s `check.py` runs `bun install` before `make check`, so the interview's computer check also needs `bun`.

**No (remove):** `frontend/` and `.run/Frontend.run.xml` are deleted, and every `stackkit:begin frontend` … `stackkit:end frontend` block is stripped. The project is the FastAPI backend alone, `make run` just starts it, and `bun` isn't needed.

### 4. AI assistant → `agents` module

**Yes (keep):** `agent_service/` stays as a uv workspace member. It holds Google ADK agents that run on their own and are deployed separately from the main service.

- Root `make` gains `adk-web` and `adk-api` (run the agents locally), `deploy-agent` and `deploy-agent-cr` (deploy them), and `sync-agents`.
- `make typecheck`, `test` and `check` also cover the agents (`typecheck-agents`, `test-agents`).
- Pre-commit hooks for `agent_service` stay.
- LLM calls always go through Vertex AI with the runtime's credentials, never an API key (`GOOGLE_GENAI_USE_VERTEXAI=true` in `app_settings.py`). Running the agents for real therefore needs a GCP project (question 6).

**No (remove):** `agent_service/` is deleted and dropped from the workspace `members` in `pyproject.toml`, and its marker blocks are stripped from the `Makefile` and pre-commit config.

### 5. Who can sign in → `VALID_DOMAINS`

Both sign-in paths read this value: Firebase Auth (`service/gcp_services/clients/fb_auth.py`) and IAP (`iap_auth.py`).

| Answer | `.env` | Effect |
|--------|--------|--------|
| Anyone (default) | `VALID_DOMAINS=` | Any Google account can sign in |
| Only my organization | `VALID_DOMAINS=<their domain>` | Only emails at that domain are accepted; everyone else is rejected after signing in |

The value is a comma-separated list, so more domains can be added to `.env` later.

### 6. Google Cloud project → `PROJECT_ID`, `USE_EMULATOR`

| Answer | `.env` | Effect |
|--------|--------|--------|
| Not yet / not sure (default) | `PROJECT_ID=`, `USE_EMULATOR=true` | Everything runs on this computer. Firestore, Auth and Storage point at the Firebase emulators (`fb_config.py`), started with `make emulator`. No cloud account and no cost. |
| Yes | `PROJECT_ID=<id>`, `USE_EMULATOR=false` | The service talks to the real Firestore database, Storage bucket and Auth in that project, using the computer's Google credentials. |

Either way, the bootstrap creates no cloud resources. Once `PROJECT_ID` is set, `make -C gcp provision` creates the `NAMESPACE` database and bucket, and the deploy targets work. Those are later steps the person agrees to separately.

> **Gap to check:** the handover tells the person to use `make run`, but `make run` doesn't start the emulators, so with `USE_EMULATOR=true` anything that touches Firestore, Auth or Storage needs `make emulator` running alongside it.

### 7. Folder → `--dest`

This is where the project is created. The folder must not already exist: `bootstrap.py` returns an `error` and writes nothing, and the skill asks the person to pick another.

## Always, without asking

- **`notebooks` removed:** deletes `notebooks/` (Jupyter for AI/ML experiments), drops it from the workspace and strips its marker block in `pyproject.toml`. Keep it only if the person is a developer and asks.
- **`http_tests` removed:** deletes `http_tests/` (hand-run requests for the PyCharm HTTP client). Same exception.
- **`NAMESPACE=<kebab-name>`:** names the GCP resources: the Firestore database (unless `FIRESTORE_DB_NAME` overrides it), the bucket `{PROJECT_ID}-{NAMESPACE}`, and the Cloud Run service name on deploy.

## What every project gets regardless

Whatever the answers, `create` does the following:

1. **Copy and prune** (`bootstrap.py`): copies the template, deletes the removed modules' `paths`, drops their workspace members, strips their marker blocks, renames the placeholders, writes `.env` from `.env.sample` with the four keys, and deletes `stackkit.toml`.
2. **Tidy the docs:** fixes the prose lines listed in `leftover_refs` that still mention removed modules, mostly in `Readme.md`, `AGENTS.md` and `docs/`.
3. **Prove it runs** (`check.py`): `git init` (if git is installed), `uv lock`, `uv sync`, `bun install` (if the frontend is kept), then `make check`. A project that fails is never called done.
4. **Hand over:** says where the project is, how to start it (`make run`, http://localhost:8000), and that putting it online needs a Google Cloud account, may cost money, and is a separate step.

Whatever the answers, the bootstrap never creates cloud projects, enables billing, deploys or changes access permissions.

## Combinations

| Frontend | Agents | What they get | Typical brief |
|----------|--------|---------------|---------------|
| ✓ | ✗ | Web app + API (**most common**) | "A site where customers place orders" |
| ✓ | ✓ | Web app + API + agents | "A chat assistant on our website" |
| ✗ | ✗ | API only | "A backend for a phone app" |
| ✗ | ✓ | API + agents, no page | "An AI that processes requests on its own" |

`make test-bootstrap` builds four sample projects (all modules, no agents, no frontend, nothing optional) to cover these shapes.
