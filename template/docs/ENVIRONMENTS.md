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
- Java, at the version in [step 5](#5-install-java-for-emulators) (for Firebase emulators)

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

The standalone CLI brings its own Node, so there's no Node version to manage:

```bash
curl -sL https://firebase.tools | bash
firebase login   # only needed for cloud commands, not the emulators
```

If you installed it with npm instead, it needs Node 20 or newer. On an older Node, run
`npm uninstall -g firebase-tools` and use the command above.

#### 5. Install Java (for emulators)

The Firebase CLI refuses Java older than 21 (since CLI v15). The emulators only need a Java
runtime, and the smallest free choices are:

```bash
# Ubuntu 22.04+ / WSL: the runtime alone, no desktop parts
sudo apt-get update && sudo apt-get install -y openjdk-21-jre-headless

# macOS: Eclipse Temurin, a free OpenJDK build (no symlink needed)
brew install --cask temurin@21
```

Check with `java -version`. If it still shows an older version on Ubuntu, pick 21 with
`sudo update-alternatives --config java`. On Debian 12 or older Ubuntu, which don't package
Java 21, install [Eclipse Temurin 21](https://adoptium.net/installation/linux/).

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

All of these are read in `gcp_services/base_settings.py`, which each service's `app_settings.py` builds on (`FRONT_END_URL` is only in `api_service/app_settings.py`).

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

<!-- stackkit:begin gae -->
**Deployment**: App Engine
<!-- stackkit:end gae -->
<!-- stackkit:begin cloud_run -->
**Deployment**: Cloud Run
<!-- stackkit:end cloud_run -->

### Environment Variables

Cloud environment variables are:
- Auto-detected: `K_SERVICE`, `GAE_INSTANCE`, `GAE_ENV`, `GOOGLE_CLOUD_PROJECT`
- Declared in `api_service/app.yaml` under `env_variables`
- Loaded from Secret Manager at startup when `IS_GCP` is true

| Variable | Source |
|----------|--------|
| `PROJECT_ID` | Auto-detected from `GOOGLE_CLOUD_PROJECT` |
| `NAMESPACE` | `api_service/app.yaml` `env_variables` (interpolated from `.env` at deploy time) |
| `GOOGLE_CLOUD_LOCATION` | Environment / Default: `us-central1` |

### Google Cloud Access

Setting the project up in Google Cloud and putting it online need permissions on the Google Cloud project. There are three ways to have them:

1. **The Owner role** on the project. It's a basic role (Google also calls these legacy roles) that covers every step below.
2. **The specific roles** for the steps you do, listed below.
3. **Someone who has them**, such as an admin or a friend with Owner, does those steps for you.

| Step | Command | Roles, if not Owner |
|------|---------|---------------------|
<!-- stackkit:begin api -->
| Grant the server's accounts their roles | `make -C gcp setup-iam` | Project IAM Admin (`roles/resourcemanager.projectIamAdmin`) |
<!-- stackkit:end api -->
<!-- stackkit:begin auth_iap -->
| Set up team sign-in | `make -C gcp iap-prepare` and the steps after it ("IAP First-Time Setup" in `docs/CLOUD.md`) | Owner: the setup needs it |
<!-- stackkit:end auth_iap -->
<!-- stackkit:begin database -->
| Create the database | `make -C gcp provision` | Cloud Datastore Owner (`roles/datastore.owner`) |
<!-- stackkit:end database -->
<!-- stackkit:begin storage -->
| Create the file bucket | `make -C gcp provision` | Storage Admin (`roles/storage.admin`) |
<!-- stackkit:end storage -->
<!-- stackkit:begin api -->
| Add keys to Secret Manager | `gcloud secrets create` | Secret Manager Admin (`roles/secretmanager.admin`) |
<!-- stackkit:end api -->
<!-- stackkit:begin gae -->
| Put it online on App Engine | `make deploy-app` | The App Engine deploy roles below |
<!-- stackkit:end gae -->
<!-- stackkit:begin cloud_run -->
| Put it online on Cloud Run | `make deploy-cr` | The Cloud Run deploy roles below |
<!-- stackkit:end cloud_run -->

<!-- stackkit:begin api -->
On new projects, the server's own accounts have no access until `setup-iam` runs: Google no longer gives default service accounts the Editor role.
<!-- stackkit:begin cloud_run -->
On Cloud Run, a deploy before that fails with a permission error, because the build account is missing Cloud Run Builder.
<!-- stackkit:end cloud_run -->
<!-- stackkit:end api -->

<!-- stackkit:begin cloud_run -->
#### Deploy roles: Cloud Run

| Role | Name | Purpose | Scope |
|------|------|---------|-------|
| Cloud Run Source Developer | `roles/run.sourceDeveloper` | To deploy from source | Project |
| Service Usage Consumer | `roles/serviceusage.serviceUsageConsumer` | To use the project's APIs | Project |
| Service Account User | `roles/iam.serviceAccountUser` | To deploy as the server's account | The Compute Engine default service account, or Project |
| Cloud Run Admin | `roles/run.admin` | Only for a public service (no team sign-in): to let anyone open it. Source Developer can't, so without it the deploy succeeds but visitors are turned away | Project |

The Compute Engine default service account (`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`) builds the source and needs Cloud Run Builder (`roles/run.builder`); `make -C gcp setup-iam` grants it.

<!-- stackkit:end cloud_run -->
<!-- stackkit:begin gae -->
#### Deploy roles: App Engine

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

<!-- stackkit:end gae -->
### Deployment

<!-- stackkit:begin gae -->
```bash
make deploy-app   # App Engine
```
<!-- stackkit:end gae -->
<!-- stackkit:begin cloud_run -->
```bash
make deploy-cr    # Cloud Run
```
<!-- stackkit:end cloud_run -->

## Secrets Management

**Method**: GCP Secret Manager, loaded into `os.environ` at startup by `load_secrets()` — and only when running on GCP (`IS_GCP`). Locally, the same values go in `.env`; nothing is fetched.

The list of secrets to load is `SECRET_KEY_NAMES` in each service's `app_settings.py` (`api_service/`, `agent_service/`, `job_service/`). It currently holds the placeholder `["TODO"]` — no real secret is wired up yet.

### Adding New Secrets

1. Create secret in GCP Console or via CLI:
   ```bash
   gcloud secrets create SECRET_NAME --replication-policy="automatic"
   echo -n "secret-value" | gcloud secrets versions add SECRET_NAME --data-file=-
   ```

2. Add the name to `SECRET_KEY_NAMES` in the `app_settings.py` of each service that reads it.

3. Add the same name to the `SECRETS` array in `gcp/bin/setup_iam.sh` and re-run it — the server's service account has no access to a new secret until you do.

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
