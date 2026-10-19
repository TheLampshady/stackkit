# AGENTS.md

Guidance for coding agents working in this repository. stackkit is a Claude Code plugin. Two parts, edited differently:

- **`skills/bootstrap/`** — the plugin. `SKILL.md` drives the interview; `scripts/bootstrap.py` (standard library only, run via `uv run --no-project`) does the copy, removal and renaming.
- **`template/`** — the product: the stack every new project is copied from. It has its own `AGENTS.md` for working *inside* it. It must stay runnable as-is (`make check` passes in a plain copy), so never add render syntax to it.

## Rules

- **No employer information** anywhere in this repo or the template — no employer names, domains, emails, repos, or employer-specific formats, not even as defaults to be rewritten. Use `example.com` and blank defaults.
- **A module's footprint lives in `template/stackkit.toml` and in `stackkit:begin/end <name>` markers.** When you add or change anything a module touches in a shared file, wrap it in that module's markers and update its `refs`.
- **After any change to `template/` or the script, run `make test-bootstrap`.** It bootstraps three sample projects (all modules, no agents, no frontend) and runs `make check` in each.
- Research lives in `docs/research/`; its charter sets scope and constraints.
