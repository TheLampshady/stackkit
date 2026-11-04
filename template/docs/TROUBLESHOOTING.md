# Troubleshooting

## Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| Port already in use | Previous process running | `lsof -i tcp:PORT && kill PID` |
| Firebase emulator fails | Java missing or too old | [Install Java](./ENVIRONMENTS.md#5-install-java-for-emulators) |
| Can't access Firebase project | Auth expired | `firebase logout && firebase login` |
| Tests fail with network error | Socket disabled | Add `@pytest.mark.enable_socket` |
| Docker socket error | Docker config issue | Enable Docker socket in settings |
| Blank tab / API network errors after idle (IAP only) | IAP session expired, redirect blocked | See [IAP Sessions](./CLOUD.md#iap-sessions-and-long-open-tabs) |

## Development Environment

### Installation Issues

#### Dependencies won't install

**Symptom**: `make setup` fails

**Solutions**:
```bash
# Ensure uv is installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear cache and retry
rm -rf .venv
make setup
```

#### Python version mismatch

**Symptom**: Wrong Python version errors

**Solution**: Ensure Python 3.13+:
```bash
pyenv install 3.13
pyenv local 3.13
```

### Runtime Issues

#### Port already in use

**Symptom**: `Error: That port is already in use`

**Solution**:
```bash
# Find process using port
lsof -i tcp:8000

# Kill the process
kill <PID>

# Force kill if needed
kill -9 <PID>
```

#### Firebase emulator won't start

**Symptom**: Emulator fails to start

**Check**:
1. Java is new enough for the Firebase CLI: `java -version` (see [Install Java](./ENVIRONMENTS.md#5-install-java-for-emulators))
2. Ports are free: 8060, 8070, 8071, 9199
3. The Firebase CLI runs: `firebase --version`

### Firebase Issues

#### Cannot access Firebase project

**Symptom**: Permission denied or project not found

**Solution**:
```bash
firebase logout
firebase login
```

#### Emulator data not persisting

**Symptom**: Data lost on emulator restart

**Note**: Emulator data is ephemeral by default. Use export/import for persistence:
```bash
firebase emulators:export ./emulator-data
firebase emulators:start --import=./emulator-data
```

## Docker Issues

### Docker socket connection error

**Symptom**: PyCharm/tools cannot connect to Docker

**Solution** (macOS):
1. Open Docker Desktop
2. Settings → Advanced
3. Enable "Enable default Docker socket (Requires password)"

### Port binding fails

**Symptom**: `Bind for xxxx:port failed`

**Solution**:
```bash
# Check what's using the port
docker ps
lsof -i tcp:5432

# Kill non-Docker process
lsof -i tcp:5432 | grep LISTEN | cut -d ' ' -f2 | xargs kill
```

### Docker requires sign-in

**Symptom**: Docker prompts for login unexpectedly

**Solution** (corporate environments):
```bash
sudo rm "/Library/Application Support/com.docker.docker/registry.json"
```
Note: This file may return on restart.

### Clean up Docker resources

```bash
# Remove stopped containers and unused images
docker system prune -a

# Nuclear option - remove everything
docker rm $(docker ps -aq)
docker rmi $(docker images -aq)
```

## Testing Issues

### Tests fail with network error

**Symptom**: `pytest-socket` blocks network calls

**Solution**: Tests are network-blocked by default. To allow network:

```python
@pytest.mark.enable_socket
def test_with_network(): ...


@pytest.mark.allow_hosts(["127.0.0.1", "api.example.com"])
def test_with_specific_hosts(): ...
```

### Tests pass locally, fail in CI

**Check**:
1. Environment variables in CI config
2. Mock fixtures are properly applied
3. Async test handling with `pytest-asyncio`

### `pytest` from the repo root collects nothing

**Symptom**: `uv run pytest` at the root finds no tests, or import errors on `api.*` / `gcp_services.*`

**Cause**: There is no pytest config at the root. `api_service/` and `agent_service/` each define their own `pythonpath`, `testpaths`, and socket settings, and both ship a package named `gcp_services` — running them in one process collides.

**Solution**: run each from inside its package.
```bash
cd service && uv run --all-groups pytest tests
cd agent_service && uv run --all-groups pytest tests
```
`make test` does this for you, plus the frontend.

### "was edited directly" from make

**Symptom**: `make run`, `make check` or a deploy stops with `<folder>/gcp_services/<file> was edited directly`

**Cause**: each `*_service/gcp_services/` is a copy of `shared/gcp_services/`, refreshed before every run, test, build and deploy. That copy was changed by hand, so refreshing it would lose the change.

**Solution**: make the same change in `shared/gcp_services/<file>`, then `make sync`. Edits in `shared/` reach every service.

## GCloud CLI Issues

### Multiple accounts/projects

Manage configurations:
```bash
# Create new configuration
gcloud config configurations create myproject
gcloud config set account email@example.com

# List all configurations
gcloud config configurations list

# Switch configuration
gcloud config configurations activate myproject

# View current config
gcloud config list
```

### Application default credentials

**Symptom**: Auth errors when running locally

**Solution**:
```bash
gcloud auth application-default login

# If quota errors occur
gcloud auth application-default set-quota-project <PROJECT_ID>
```

## Deployment Issues

### Deployment fails

**Debug steps**:
1. Check `app.yaml` syntax
2. Verify service account permissions
3. Check logs: `gcloud app logs tail`

### Static files missing after deploy

**Solution**:
```bash
make build  # Builds frontend + copies frontend/dist/ to api_service/static/
make deploy-app
```

### Blank page or network errors after a tab sits open (IAP only)

Only applies to deployments behind Identity-Aware Proxy. The IAP session expired and
IAP is redirecting script and API requests to Google sign-in, which the browser blocks.
Reloading the page fixes it once. For the permanent fix, see
[IAP Sessions and Long-Open Tabs](./CLOUD.md#iap-sessions-and-long-open-tabs).

## Debug Commands

| Purpose | Command |
|---------|---------|
| Check Python version | `python --version` |
| Check uv version | `uv --version` |
| Check Firebase login | `firebase login:list` |
| Check GCloud account | `gcloud config list` |
| View app logs | `gcloud app logs tail` |
| Test API locally | `curl http://localhost:8000/api/healthcheck/` |
| Check which App Engine version serves you | `cd gcp && make cli ARGS="split-cookie <app-url>"` |

## Logs

| Log Type | Location | Command |
|----------|----------|---------|
| Local API | Terminal | (stdout) |
| App Engine | Cloud Logging | `gcloud app logs tail` |
| Firebase Emulator | Terminal / Emulator UI | http://localhost:8060 |

## Getting Help

| Issue Type | Where to Go |
|------------|-------------|
| Firebase issues | [Firebase Support](https://firebase.google.com/support) |
| GCP issues | [GCP Support](https://cloud.google.com/support) |
| FastAPI issues | [FastAPI GitHub](https://github.com/tiangolo/fastapi/issues) |

## Related Documentation

- [README.md](../Readme.md) - Project overview
- [ENVIRONMENTS.md](./ENVIRONMENTS.md) - Environment setup
- [CLOUD.md](./CLOUD.md) - Deployment guide
