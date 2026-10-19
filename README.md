# stackkit

> Turn a plain-language idea into a working, slim web app — set up by Claude, from a short interview.

A non-technical person describes what they want. The `bootstrap` skill asks a few plain questions, copies a runnable template, removes the parts the project doesn't need, fills in its name and settings, and runs the project's checks before handing it over. The new project has no link back to stackkit: it's theirs to change.

## What's in here

| Path | What it is |
|------|------------|
| `skills/bootstrap/` | The skill: the interview (`SKILL.md`, `references/questions.md`) and the script that builds the project (`scripts/bootstrap.py`) |
| `template/` | The stack itself — a normal, runnable project (FastAPI + Firebase + Vertex AI, optional React frontend and ADK agents). Copy it by hand any time. |
| `template/stackkit.toml` | Which parts are optional, what each one touches, and the placeholder values the bootstrap replaces. Deleted from every new project. |
| `docs/research/` | Research charter and findings behind the design |

## Requirements

Claude Code, plus `uv` and `make` (and `bun` if the project keeps the frontend). `git` is optional. The skill checks for these and asks before installing anything. Native Windows needs WSL for now.

## Install

**Claude Code:**
```bash
claude plugin marketplace add TheLampshady/stackkit
claude plugin install stackkit@stackkit-marketplace
```

Then say "set up a new project" (or `/stackkit:bootstrap`).

## How optional parts are removed

Each optional module is listed in `template/stackkit.toml` with its folders. Anything it adds to shared files (the Makefile, pre-commit config, `pyproject.toml`, `.env.sample`) sits between comment markers:

```make
# stackkit:begin agents
TEST_TARGETS += test-agents
# stackkit:end agents
```

The template runs as-is with the markers in place. The bootstrap deletes the blocks for removed modules, strips the rest of the markers, and reports any prose that still mentions a removed part so Claude can rewrite it.

**Adding an optional module:** put its folder in `template/`, wrap its additions to shared files in markers with its name, and add a `[modules.<name>]` table to `stackkit.toml`. Then run `make test-bootstrap`.

## Development

```bash
make help            # list targets
make test-bootstrap  # build sample projects into a temp dir and run `make check` in each
make claude          # reinstall this repo as a local Claude plugin
```

## License

[MIT](LICENSE)
