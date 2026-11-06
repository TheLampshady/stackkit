# Reactions: building one by hand

A reaction runs on its own when a new file lands in the project's storage, or a record is created or changed in its database, by something other than the project's own server. stackkit has no part for this yet, so `create` builds a first version by hand from these notes. Something the server itself saves needs no reaction: do the follow-up in the server, or start background work if it's long.

Tell the person it's a first version outside the parts stackkit tests. Keep it small: one function per reaction.

## What to build

Cloud Functions for Firebase, in Python, deployed from source (no Docker). The local emulator runs them, so a reaction can be tried on this computer.

```
trigger_service/
├── main.py            one decorated function per reaction
├── requirements.txt   exported from the lockfile by `make -C trigger_service build`
├── venv/              made by uv (the Firebase CLI needs it here; gitignored)
├── Makefile           build (export requirements, make venv), deploy
└── tests/             call each function with a hand-built event
```

Give it its own `pyproject.toml` (package `trigger-service`) depending on `firebase-functions` and `firebase-admin`, and add it to the root `pyproject.toml` workspace `members`. Add `typecheck-triggers` and `test-triggers` targets to the root `Makefile`'s `CHECK_TARGETS`, like the jobs ones, so `check.py` covers it. Don't put it through `shared/sync.sh`'s copy of the shared clients unless the reaction needs them; a function starts with `initialize_app()` from `firebase_admin`.

```python
from firebase_admin import initialize_app
from firebase_functions import firestore_fn, storage_fn

initialize_app()


@firestore_fn.on_document_created(document="orders/{order_id}", database="<NAMESPACE>")
def on_new_order(event: firestore_fn.Event) -> None: ...


@storage_fn.on_object_finalized(bucket="<PROJECT_ID>-<NAMESPACE>")
def on_upload(event: storage_fn.CloudEvent) -> None: ...
```

- **The database and bucket are the project's own**, named by `NAMESPACE` (the database) and `<PROJECT_ID>-<NAMESPACE>` (the bucket), not the defaults. Pass them as above. The Firebase CLI registers Firestore reactions with that database name, and the emulator accepts it (checked with firebase-tools 15.35 and firebase-functions 0.6).
- **The venv:** the folder's `build` target runs `uv export --frozen --package trigger-service --no-dev --no-hashes --format requirements-txt > requirements.txt`, then `uv venv venv --python 3.13` and `uv pip install --python venv/bin/python -r requirements.txt`. The CLI loads functions from a uv-made venv; it doesn't need pip. Add `venv/` to `.gitignore`. `create` writes the target but doesn't run it (it runs no commands but its scripts); the person runs it once, and `make emulator` and the deploy target depend on it.
- **`gcp/firebase.json`:** add `"functions": [{ "source": "../trigger_service", "codebase": "<NAMESPACE>", "runtime": "python313" }]` and a `"functions": { "port": 5001 }` emulator entry. The codebase name keeps it apart from other apps in a shared Google Cloud project.
- **Run it here:** `make emulator` starts it with the database and storage emulators; saving a record or uploading a file in the emulator fires the reaction.
- **Put it online:** `firebase deploy --only functions:<NAMESPACE> --project <PROJECT_ID>`, as a `deploy` target in its Makefile. Whoever puts it online needs the Cloud Functions Developer role; the hand-over note says so.
- **Write it to run twice safely.** Google may deliver the same event more than once, and a reaction that writes to the collection it watches can set itself off again: check before writing.

## Not yet checked

That an event fires end to end in the emulator was not proven when these notes were written (the test sandbox blocked the CLI's local calls). `create` can't run the emulator, so the tests call each function with a hand-built event. In the hand-over, give the person the steps to try it for real (`make -C trigger_service build`, `make emulator`, then add a record or upload a file), and say that if nothing happens, the function still works when called by hand and the reaction needs a look.