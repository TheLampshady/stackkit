# stackkit-app

> Personal development platform with FastAPI backend, Firebase services, and Vertex AI integration.

This project provides a cloud-native backend service designed for rapid development with local Firebase emulators and seamless GCP deployment. It includes pre-configured AI/ML capabilities via Vertex AI and Google's Agent Development Kit (ADK).

---

## Quick Start

Get the project running locally in three steps. The setup uses Firebase emulators so you can develop without cloud costs or an internet connection.

### 1. Install

Installs Python dependencies via [uv](https://docs.astral.sh/uv/), configures git hooks for code quality, and sets up the commit message template.

```bash
make setup
```

### 2. Configure

Create your local environment file. `.env` controls which GCP project you target, whether Firebase emulators are used, and the `NAMESPACE` that names your cloud resources (Firestore DB, Storage bucket).

```bash
cp .env.sample .env
# Set PROJECT_ID and NAMESPACE, then choose USE_EMULATOR
```

Deployed instances load their secrets from Secret Manager at startup (`SECRET_KEY_NAMES` in `api_service/app_settings.py`). Locally, put the same values in `.env` — there is no pull step.

> **Need help?** See [Environment Setup](./docs/ENVIRONMENTS.md) for detailed configuration including GCloud CLI setup and Firebase initialization.

### 3. Run

Start two terminal sessions - one for Firebase emulators (auth, database, storage) and one for the FastAPI server. The emulators must be running before the API server starts.

```bash
make emulator  # Terminal 1: Start Firebase emulators
make run       # Terminal 2: Start FastAPI server
```

`make run` branches on `FRONT_END_URL`: set it (e.g. `http://localhost:5173`) and the Vite dev server runs alongside the API with FastAPI redirecting to it; leave it unset and the frontend is built into `api_service/static/` and served by FastAPI itself.

**Local URLs**:
- **API**: http://localhost:8000 — FastAPI backend with auto-generated docs at `/api/docs` and `/api/scalar`
- **Frontend (dev)**: http://localhost:5173 — Vite dev server, proxies `/api` to port 8000 (only when `FRONT_END_URL` is set)
- **Emulator UI**: http://localhost:8060 — Visual interface for Firebase Auth, Firestore, and Storage

---

## Common Commands

Daily development commands. All commands use `make` targets defined in the root Makefile.

| Command | Description |
|---------|-------------|
| `make setup` | Install dependencies (uv sync), git hooks, commit template, `bun install` |
| `make run` | Start backend, plus the Vite dev server when `FRONT_END_URL` is set |
| `make run-be` / `make run-fe` | Start just the FastAPI server / just the Vite dev server |
| `make emulator` | Start Firebase emulators (Auth:8071, Firestore:8070, Storage:9199, UI:8060) |
| `make check` | Run full quality suite: lint → format → typecheck → test (backend + frontend) |
| `make lint` | ruff `--fix` on Python, ESLint on the frontend |
| `make format` | ruff formatter |
| `make typecheck` | `ty` on `api_service/` and `agent_service/`, `tsc -b` on the frontend |
| `make test` | pytest for `api_service/` and `agent_service/`, Vitest for the frontend |
| `make hooks` | Run pre-commit across all files |
| `make sync` | Copy `shared/gcp_services/` into each `*_service/` (run, test, build and deploy do it first) |
| `make build` | Build the frontend and copy `frontend/dist/` into `api_service/static/` |
| `make deploy-app` | Build, then deploy the service to App Engine |
| `make deploy-cr` | Build, then deploy the service to Cloud Run |

**Agents** — the ADK agents in `agent_service/` deploy separately:

| Command | Description |
|---------|-------------|
| `make adk-web` / `make adk-api` | Run the ADK web UI / API server against `agent_service/agents/` |
| `make deploy-agent` | Deploy to Agent Engine via `agent_service/deploy.py` |
| `make deploy-agent-cr` | Deploy the agents to Cloud Run via `adk deploy` |

Every `-be` / `-fe` variant of the quality targets can be run on its own (`make lint-fe`, `make test-be`, …). Infrastructure targets — Firestore rules, indexes, bucket CORS, IAM, the `gcp` CLI — live in `gcp/Makefile`; see the [Cloud Guide](./docs/CLOUD.md).

---

## Tech Stack

The project uses a modern Python backend with Google Cloud services for auth, data persistence, and AI capabilities.

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | FastAPI + Gunicorn | Async API framework with production WSGI server |
| **Frontend** | React 19 + Vite + Tailwind v4 + shadcn/ui | SPA built to `api_service/static/`, served by FastAPI |
| **Authentication** | Firebase Auth | User management, JWT tokens, domain whitelisting |
| **Database** | Firestore | NoSQL document database with real-time sync |
| **Storage** | Cloud Storage | File uploads and static asset hosting |
| **AI/ML** | Vertex AI + Google ADK | Model inference and agent orchestration |
| **Secrets** | Secret Manager | Secure credential storage |
| **Deployment** | App Engine, Cloud Run, Agent Engine | Managed serverless hosting for the service and the agents |
| **Packaging** | uv workspace | Python packages — `api-service`, `agents`, `gcp`, `notebooks` — under one lockfile |

---

## Project Structure

Each folder serves a specific purpose in the development and deployment workflow.

The repo is a uv workspace: `api_service/`, `agent_service/`, `gcp/` and `notebooks/` are each a package with its own `pyproject.toml` and `Makefile`, sharing the root lockfile.

| Folder | Purpose |
|--------|---------|
| `api_service/` | **Main application** — FastAPI backend (entry: `app.py`), API routes, GCP clients, tests |
| `api_service/api/` | Route definitions (`router.py`) and app wiring — CORS, static mount, SPA fallback (`config_app.py`) |
| `shared/gcp_services/` | **Shared code** for GCP/Firebase integrations: edit it here; every `*_service/` keeps a copy, refreshed by `make sync` |
| `agent_service/` | **Agents deploy unit** — self-contained ADK agents with their own settings and GCP services |
| `agent_service/agents/` | Google ADK agent definitions (each agent has `agent.py` + `prompt.py`) |
| `gcp/` | **Infrastructure** — Firebase emulator configs, Firestore rules/indexes, IAM scripts, and the `gcp` CLI |
| `frontend/` | **Frontend** — React SPA (Vite + Tailwind v4 + shadcn/ui), built to `api_service/static/` during deploy |
| `notebooks/` | **Experimentation** — Jupyter notebooks for Gemini, ADK and Vertex AI prototyping (`make -C notebooks lab`). `custom_model/` has its own `pyproject.toml` for the Vertex prediction image, compiled with `make -C notebooks requirements` |
| `http_tests/` | PyCharm HTTP client requests for hitting the API by hand |
| `frontend/app.yaml`, `frontend/app-spa.yaml` | Standalone App Engine templates for static-site hosting (multi-page / SPA) — not part of the main deploy |

---

## Documentation

Detailed guides for different aspects of the project. Start with Architecture for system understanding, Environments for setup, and Troubleshooting when things go wrong.

| Document | What You'll Learn |
|----------|-------------------|
| **[Architecture](./docs/ARCHITECTURE.md)** | System design, service diagrams, data models, module explanations, and design decisions |
| **[Environments](./docs/ENVIRONMENTS.md)** | Prerequisites, local setup, environment variables, Firebase emulator configuration, GCloud CLI management |
| **[Cloud](./docs/CLOUD.md)** | GCP project setup, Firebase configuration, API enablement, deployment process, monitoring |
| **[Troubleshooting](./docs/TROUBLESHOOTING.md)** | Common errors, port conflicts, Docker issues, Firebase auth problems, test failures |

---

## Testing

Tests use pytest with `pytest-asyncio` for async support. Network access is **blocked by default** via `pytest-socket` to ensure tests don't make external calls.

`api_service/` and `agent_service/` each carry their own pytest config and are run as separate processes — the root has no pytest config, so run them from inside the package.

```bash
make test                                                   # service + agents + frontend
cd service && uv run --all-groups pytest tests -v           # backend only
cd service && uv run --all-groups pytest tests/test_api.py::test_name -v   # single test
cd agent_service && uv run --all-groups pytest tests -v     # agents only
cd frontend && bun run vitest run src/pages/HomePage.test.tsx  # single frontend test
```

**Filter tests by marker** (markers are defined in `api_service/pyproject.toml`):

| Command | Description |
|---------|-------------|
| `uv run --all-groups pytest tests -m "not slow"` | Skip tests marked as slow |
| `uv run --all-groups pytest tests -m "not integration"` | Skip integration tests |

**Enable network for specific tests** (in test code):

```python
@pytest.mark.enable_socket
def test_external_api(): ...
```

---

## Deployment

The service and the agents are separate deploy units with separate targets.

```bash
make deploy-app     # Service → App Engine
make deploy-cr      # Service → Cloud Run
make deploy-agent   # Agents  → Agent Engine
```

**What `make deploy-app` does:**
1. `make build-fe` — `bun run build` in `frontend/`
2. `make build-be` — exports `api_service/requirements.txt` from the lockfile
3. copies `frontend/dist/` into `api_service/static/`
4. `gcloud app deploy api_service/app.yaml --no-promote` — new version is deployed but does not take traffic until you migrate it

> See [Cloud Guide](./docs/CLOUD.md) for full deployment instructions, rollback procedures, and monitoring setup.
