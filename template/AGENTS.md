# AGENTS.md

Guidance for coding agents (Claude Code, Gemini, Copilot and others) working in this repository.

## Build & Development Commands

```bash
# Setup
make setup              # All: uv sync + git hooks + commit template + bun install

# Development
make run                # Both: starts FastAPI + Vite dev server in parallel
make run-be             # Backend: FastAPI server (port 8000)
make run-fe             # Frontend: Vite dev server (port 5173, proxies /api to 8000)
make emulator           # Start Firebase emulators (auth:8071, firestore:8070, UI:8060, storage:9199)

# Code Quality (all have -be / -fe variants, bare runs both)
make lint               # Both
make format             # Both
make typecheck          # Both
make test               # Both
make check              # Both: lint, format, typecheck, test
make hooks              # Run pre-commit on all files

# Single test
uv run pytest service/tests/test_api.py::test_name -v          # Backend
cd frontend && bun run vitest run src/lib/api.test.ts           # Frontend

# Skip slow/integration tests
uv run pytest -m "not slow"
uv run pytest -m "not integration"

# Build & Deploy
make build              # Build frontend + copy dist/ to service/static/
make build-fe           # Build frontend only (frontend/dist/)
make build-be           # Export requirements.txt
make deploy-app         # Build + deploy to App Engine

# Agents
make adk-web            # Sync GCP services + start ADK web UI (agents)
make adk-api            # Sync GCP services + start ADK API server (agents)
make deploy-agent       # Sync + deploy to Agent Engine via deploy.py
make deploy-agent-cr    # Sync + deploy to Cloud Run via adk deploy
make sync-agents        # Copy shared GCP service files to agent_service/

# Cloud Setup (run once per project, or when secrets change)
bash gcp/bin/setup_iam.sh   # Grant the server's service accounts their roles (reads PROJECT_ID from .env; needs Owner or Project IAM Admin)
```

## Architecture

**Stack**: FastAPI + Firebase (Auth/Firestore/Storage) + Vertex AI + Google ADK
**Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui + React Router + TanStack Query

### Directory Structure
- `frontend/` - React SPA (Vite + Tailwind v4 + shadcn/ui)
- `service/` - FastAPI backend (entry: `app.py`)
- `service/gcp_services/` - GCP service modules (source of truth, synced to agent_service/)
- `service/gcp_services/clients/` - Pre-configured Firebase clients (`db`, `auth_client`, `bucket`)
- `agent_service/` - ADK agents deploy unit (self-contained with own settings + GCP services)
- `agent_service/agents/` - Google ADK agent definitions (each folder: `agent.py` + `prompt.py`)
- `agent_service/gcp_services/` - Synced subset of service/gcp_services/ (Firestore only, no auth/storage)
- `agent_service/deploy.py` - Agent Engine deployment via vertexai.agent_engines
- `gcp/` - Firebase emulator orchestration and deployment tooling
- `notebooks/` - ML experimentation with Vertex AI

### Dual-Mode Configuration (`service/app_settings.py`)
- **Local**: Uses emulators when `USE_EMULATOR=true` in `.env`
- **Cloud**: Auto-detects GCP (via `K_SERVICE`, `GAE_INSTANCE` env vars), loads secrets from Secret Manager
- Settings cascade: `.env` -> environment variables -> GCP defaults
- **Namespace**: Set `NAMESPACE` env var to name GCP resources (Firestore DB name, Storage bucket as `{project_id}-{namespace}`)

### Firebase Client Access
Always import pre-configured clients from `gcp_services.py`:
```python
from gcp_services.clients.gcp_services import db, bucket, auth_client
```
Clients auto-detect emulator mode via `settings.use_emulator`.

### Route Structure
All API routes go through `service/api/router.py` via `api_router` (prefix: `/api`). App entry point is `service/app.py`.

### Authentication
Two options in `service/gcp_services/clients/`, both attach the caller to `request.state.user`
and check the email against `settings.valid_domains` (`VALID_DOMAINS` env: domains or full addresses,
comma separated, default blank; blank disables the check and allows any account):

- **Firebase Auth** (`fb_auth.py`): `@firebase_auth_required()` extracts the Bearer token,
  validates it with Firebase Auth, checks the domain, attaches a `user` dict.
- **IAP** (`iap_auth.py`): `@iap_auth_required()` per endpoint, or `IdentityMiddleware` for all
  `/api/` paths. Verifies `x-goog-iap-jwt-assertion` against the service's IAP audience
  (`IAP_AUDIENCE` or derived from Cloud Run metadata). Locally `LOCAL_USER_EMAIL` is the identity.

### ADK Agents
- Define agents using `Agent()` class from `google.adk`
- Must export `root_agent` in each agent module
- Deploy with `make deploy-agent` (Agent Engine) or `make deploy-cr` (Cloud Run)

## Coding Standards

- Python type hints required for all function params and return types
- Use reStructuredText docstrings with `:param:`, `:return:`, `:raises:`, `:side effects:` (omit if None)
- Never use `:type:` or `:rtype:` fields
- Always include `__init__.py` in new Python directories
- Async/await for all database operations (using `firestore_async`)
- Commit message format: `[TASK] :: One Sentence Summary`

## Testing

Tests use pytest-asyncio with mocked Firebase/GCP services. **Network is blocked by default** via pytest-socket - tests that make external calls will fail unless explicitly allowed.

Key fixtures in `conftest.py`:
- `async_client` - AsyncClient for endpoint testing
- `mock_firebase_auth` - Mocked auth client with valid token
- `mock_gcp_services` - Combined Firestore and Storage mocks
- `auth_headers` - Standard Bearer token headers

To allow network in specific tests:
```python
@pytest.mark.enable_socket
def test_with_network(): ...


@pytest.mark.allow_hosts(["127.0.0.1", "api.example.com"])
def test_with_specific_hosts(): ...
```

Note: `pythonpath` is set to `service/` in pyproject.toml, so test imports use `from api.xxx` not `from service.api.xxx`.

### Pre-commit Hooks
Config at `.config/.pre-commit-config.yaml` (not default location).

**Backend hooks** (trigger on Python files): ruff check/format, ty typecheck, pytest.
**Frontend hooks** (trigger on `frontend/` ts/tsx files): ESLint, tsc typecheck, Vitest.
**General hooks**: yaml/json checks, large file detection, trailing whitespace, private key detection.

## JetBrains Run Configurations

Shared run configs live in `.run/` and appear in PyCharm / IntelliJ automatically:

- **Service** — FastAPI app (`service/app.py`, working dir `service/`)
- **FB Emulator** — `gcp/bin/emulator.sh` in a terminal
- **sync-db** — `make -C gcp sync-db`
<!-- stackkit:begin frontend -->
- **Frontend** — `bun run dev` in `frontend/`
<!-- stackkit:end frontend -->

## Tools
Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.

Prefer `make` targets first, then `bun` / `uv` commands; only fall back to your own commands when neither covers the task.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

## Active Technologies
- Python 3.13 (matches root pyproject.toml) + google-adk >=1.28.0, firebase-admin, google-cloud-logging, google-cloud-secret-manager, pydantic-settings, python-dotenv (001-agents-gcp-services)
- Firestore (async client) — emulator locally (port 8070), production via GCP credentials (001-agents-gcp-services)

## Recent Changes
- 001-agents-gcp-services: Added Python 3.13 (matches root pyproject.toml) + google-adk >=1.28.0, firebase-admin, google-cloud-logging, google-cloud-secret-manager, pydantic-settings, python-dotenv
