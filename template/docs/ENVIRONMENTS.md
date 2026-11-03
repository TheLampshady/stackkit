# Environments

## Overview

| Environment | URL | Purpose |
|-------------|-----|---------|
| Local | http://localhost:8000 | Development with emulators |
| Cloud (App Engine) | [TODO: Add URL] | Production deployment |

## Local Development

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [GCloud CLI](https://cloud.google.com/sdk/docs/install)
- [Firebase CLI](https://firebase.google.com/docs/cli)
- Java 11+ (for Firebase emulators)

### System Setup

#### 1. Install Homebrew (macOS)

Visit [brew.sh](https://brew.sh/) and follow installation instructions.

#### 2. Install Python

```bash
brew install pyenv
pyenv init
# Follow profile instructions from pyenv init
pyenv install 3.13
```

#### 3. Install GCloud CLI

Download from [Google Cloud SDK](https://cloud.google.com/sdk/docs/install).

Authenticate:
```bash
gcloud auth login
gcloud auth application-default login
```

Optionally set quota project:
```bash
gcloud auth application-default set-quota-project <PROJECT_ID>
```

#### 4. Install Firebase CLI

```bash
curl -sL https://firebase.tools | bash
firebase login
```

#### 5. Install Java (for emulators)

```bash
brew install java11

# M1/M2 Macs require additional symlink:
sudo ln -sfn /opt/homebrew/opt/openjdk@11/libexec/openjdk.jdk \
     /Library/Java/JavaVirtualMachines/openjdk-11.jdk
```

### Project Setup

```bash
# Clone and setup — uv sync, git hooks, commit template, bun install
make setup
```

### Environment Variables

Create `.env` from sample:
```bash
cp .env.sample .env
```

All of these are read in `service/app_settings.py` (and its twin in `agent_service/`).

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PROJECT_ID` | GCP project ID. Falls back to `GOOGLE_CLOUD_PROJECT` | - | Yes |
| `NAMESPACE` | Names your GCP resources — feeds `FIRESTORE_DB_NAME` and the bucket name | - | Yes, in practice |
| `USE_EMULATOR` | Use Firebase emulators. Anything but `0`/`false`/`no`/empty is true | `true` locally, `false` on GCP | No |
| `FIRESTORE_DB_NAME` | Firestore database name | value of `NAMESPACE` | No |
| `FIRESTORE_BUCKET_NAME` | Storage bucket name | `{PROJECT_ID}-{NAMESPACE}` | No |
| `FRONT_END_URL` | Vite dev server URL. When set, `make run` starts Vite and FastAPI redirects unmatched routes to it | - | No |
| `GOOGLE_CLOUD_LOCATION` | Region for Vertex AI | `us-central1` | No |
| `VERSION` | App Engine / Cloud Run version name used by the deploy targets | `main` | No |

Set automatically by the platform, never in `.env`: `K_SERVICE` (Cloud Run), `GAE_INSTANCE` / `GAE_ENV` / `GAE_VERSION` (App Engine). `IS_GCP` can be set by hand to force cloud mode.

### Local Services

| Service | Command | Port |
|---------|---------|------|
| FastAPI | `make run` / `make run-be` | 8000 |
| Vite dev server | `make run-fe` (or `make run` with `FRONT_END_URL` set) | 5173 |
| Firebase Auth Emulator | `make emulator` | 8071 |
| Firestore Emulator | `make emulator` | 8070 |
| Storage Emulator | `make emulator` | 9199 |
| Emulator UI | `make emulator` | 8060 |

`make emulator` seeds from `gcp/firestore_data`; `make emulator-empty` (run from `gcp/`) starts with a clean database.

To work locally on the data in the cloud, stop the emulator (Ctrl+C, and wait for it to finish saving) and run `make -C gcp sync-db`. It copies the database `.env` points at (`FIRESTORE_DB_NAME`, else `NAMESPACE`) into `gcp/firestore_data`, into the emulator's `(default)` database that the app reads locally, and asks before replacing anything. Uploaded files are not copied.

### Local URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/api/docs |
| API Reference (Scalar) | http://localhost:8000/api/scalar |
| Frontend dev server | http://localhost:5173 |
| Emulator UI | http://localhost:8060 |

### PyCharm Run Configurations

#### 1. Emulator (Shell Script)

- **Type**: Shell Script
- **Script path**: `gcp/bin/emulator.sh`
- **Working directory**: `gcp/`

#### 2. Frontend (npm)

- **Type**: npm
- **Package manager**: bun
- **Command**: run
- **Scripts**: dev
- **Working directory**: `frontend/`

#### 3. Backend (uv)

- **Type**: uv
- **Script**: `uvicorn app:app --reload`
- **Arguments**: `--directory service`
- **Working directory**: Project root

Run all three configurations together using PyCharm's compound run configuration or run them individually as needed.

## Cloud (GCP)

**Deployment**: App Engine

### Environment Variables

Cloud environment variables are:
- Auto-detected: `K_SERVICE`, `GAE_INSTANCE`, `GAE_ENV`, `GOOGLE_CLOUD_PROJECT`
- Declared in `service/app.yaml` under `env_variables`
- Loaded from Secret Manager at startup when `IS_GCP` is true

| Variable | Source |
|----------|--------|
| `PROJECT_ID` | Auto-detected from `GOOGLE_CLOUD_PROJECT` |
| `NAMESPACE` | `service/app.yaml` `env_variables` (interpolated from `.env` at deploy time) |
| `GOOGLE_CLOUD_LOCATION` | Environment / Default: `us-central1` |

### IAM Roles for Deployment

To deploy the application to App Engine, your deploying Google Cloud account (or service account) requires the following IAM roles:

| Role | Name | Purpose | Scope |
|------|------|---------|-------|
| App Engine Deployer | `roles/appengine.deployer` | To deploy new versions and configs | Project |
| Cloud Build Editor | `roles/cloudbuild.builds.editor` | To run the build container under the hood | Project |
| Storage Object Admin | `roles/storage.objectAdmin` | To list, upload, and clean up source files | Staging bucket (`gs://staging.<PROJECT_ID>.appspot.com`) |
| Service Account User | `roles/iam.serviceAccountUser` | To act as the build service account during Cloud Build | Project or specific Service Account |

> [!TIP]
> To follow the principle of least privilege, grant the **Storage Object Admin** (or `roles/storage.objectUser` if available in your organization) role specifically on the staging bucket resource instead of project-wide.

To grant these roles using the `gcloud` CLI (replacing `<PROJECT_ID>` and `<USER_EMAIL>` with your actual values):

```bash
# 1. Grant App Engine Deployer
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="user:<USER_EMAIL>" \
    --role="roles/appengine.deployer"

# 2. Grant Cloud Build Editor
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="user:<USER_EMAIL>" \
    --role="roles/cloudbuild.builds.editor"

# 3. Grant Service Account User (Project-wide - easiest method)
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="user:<USER_EMAIL>" \
    --role="roles/iam.serviceAccountUser"

# 4. Grant Storage Object Admin (specifically on the GAE staging bucket)
gcloud storage buckets add-iam-policy-binding gs://staging.<PROJECT_ID>.appspot.com \
    --member="user:<USER_EMAIL>" \
    --role="roles/storage.objectAdmin"
```

### Deployment

```bash
make deploy-app
```

## Secrets Management

**Method**: GCP Secret Manager, loaded into `os.environ` at startup by `load_secrets()` — and only when running on GCP (`IS_GCP`). Locally, the same values go in `.env`; nothing is fetched.

The list of secrets to load is `SECRET_KEY_NAMES` in `service/app_settings.py`. It currently holds the placeholder `["TODO"]` — no real secret is wired up yet.

### Adding New Secrets

1. Create secret in GCP Console or via CLI:
   ```bash
   gcloud secrets create SECRET_NAME --replication-policy="automatic"
   echo -n "secret-value" | gcloud secrets versions add SECRET_NAME --data-file=-
   ```

2. Add the name to `SECRET_KEY_NAMES` in `service/app_settings.py`.

3. Add the same name to the `SECRETS` array in `gcp/bin/setup_iam.sh` and re-run it — the App Engine service account has no access to a new secret until you do.

4. For local runs, put the value in `.env` directly.

## Managing GCloud Configurations

For multiple GCP projects:

```bash
# Create new configuration
gcloud config configurations create myproject
gcloud config set account email@example.com
gcloud config set project my-project-id

# List configurations
gcloud config configurations list

# Switch configuration
gcloud config configurations activate myproject

# View current config
gcloud config list
```

## Firebase Project Setup

### Initialize Firebase

```bash
firebase init
```

Select emulators: `firestore`, `authentication`, `storage`

Configure ports:
```
Firestore: 8070
Auth: 8071
Storage: 9199
Emulator UI: 8060
```

### Multiple Firebase Projects

```bash
firebase use --add
# Select project and assign alias
```

## Related Documentation

- [README.md](../Readme.md) - Project overview
- [CLOUD.md](./CLOUD.md) - Infrastructure details
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Environment issues
