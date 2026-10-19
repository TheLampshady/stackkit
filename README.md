# stackkit

> Turn a plain-language idea into a working, slim web app — set up by Claude, from a short interview.

A non-technical person describes what they want. The `bootstrap` skill asks a few plain questions, copies a runnable template, removes the parts the project doesn't need, fills in its name and settings, and runs the project's checks before handing it over. The new project has no link back to stackkit: it's theirs to change.

## What's in here

| Path | What it is |
|------|------------|
| `skills/bootstrap/` | The skill people start: the interview and its questions (`SKILL.md`), ending in a plan they confirm |
| `skills/create/` | The skill `bootstrap` hands the plan to: the scripts that build the project (`scripts/bootstrap.py`) and check it runs (`scripts/check.py`). Hidden from the `/` menu. |
| `template/` | The stack itself — a normal, runnable project with every module in (FastAPI, React, Firestore, Cloud Storage, IAP, Vertex AI, ADK agents, App Engine and Cloud Run). Copy it by hand any time. |
| `template/stackkit.toml` | Which parts are optional, what each one touches, and the placeholder values the bootstrap replaces. Deleted from every new project. |
| `docs/research/` | Research charter and findings behind the design |

## Requirements

Claude Code, plus `uv` and `make`; `bun` if the project keeps the web page; the Firebase CLI and Java if it keeps the database or file storage. `git` is optional. The skill checks for these and asks before installing anything. Native Windows needs WSL for now.

## Install

**Claude Code:**
```bash
claude plugin marketplace add TheLampshady/stackkit
claude plugin install stackkit@stackkit-marketplace
```

Then say "set up a new project" (or `/stackkit:bootstrap`).

## What the interview decides

Each answer keeps or removes a module, so the project is only as big as the brief:

| Answer | Module |
|--------|--------|
| People open it in a browser | `frontend` (React) |
| It remembers things between visits | `database` (Firestore) |
| People upload or keep files | `storage` (Cloud Storage) |
| Only the team uses it | `auth_iap` (Identity-Aware Proxy) |
| Customers have their own accounts | `auth_firebase` (Firebase Auth; login screens are built later, by other kits) |
| It uses AI: one job when asked / an assistant that acts | `ai` (Gemini/Claude on Vertex AI) / plus `agents` (ADK) |
| None of the above, and nothing behind the scenes | no `api`: a static site |
| Its own web address / Google's address | `gae` (App Engine) / `cloud_run` (Cloud Run) |
| Always answers instantly (costs more) / a short wait after quiet spells | `always_on` (one instance kept running) / scale to zero |

Some modules are never asked about: `firebase` (the app and its local emulator) and `gcp` (the tooling folder) go once nothing kept needs them. `notebooks` is for developers.

## How optional parts are removed

Each optional module is listed in `template/stackkit.toml` with its folders. Anything it adds to shared files (the Makefile, pre-commit config, `pyproject.toml`, `.env.sample`) sits between comment markers:

```make
# stackkit:begin agents
TEST_TARGETS += test-agents
# stackkit:end agents
```

The template runs as-is with the markers in place. The bootstrap deletes the blocks for removed modules, strips the rest of the markers, and reports any prose that still mentions a removed part so Claude can rewrite it.

A module can also `require` others (the bootstrap refuses a combination that can't work), name JSON keys to delete (JSON can't hold markers), and list fallback files that only matter without it. The header of `stackkit.toml` describes each field.

**Adding an optional module:** put its folder in `template/`, wrap its additions to shared files in markers with its name, and add a `[modules.<name>]` table to `stackkit.toml`. Mark only imports of files the module deletes; an import that just goes unused is cleaned up by the new project's `make check`. Then run `make test-bootstrap`.

## Development

```bash
make help            # list targets
make lint            # scripts and template must be ruff-clean as they stand
make test-bootstrap  # lint, build sample projects into a temp dir, run `make check` in each
make claude          # reinstall this repo as a local Claude plugin
```

## License

[MIT](LICENSE)
