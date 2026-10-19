---
name: bootstrap
description: Set up a new project from a plain-language idea. Interviews a non-technical person in everyday words, then creates a working web app (FastAPI backend, Firebase, optional React frontend and AI agents) with only the parts they need, and checks that it runs before handing it over. Use when someone asks to: start a new project, set up an app, make me a website/tool/backend, turn my idea into an app, bootstrap a repo, create a project from stackkit.
allowed-tools: Bash(uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py *)
---

# bootstrap

Turn a non-techie's brief into a working project. The person you're talking to may never have used a terminal. Everything you say to them is in plain words: no tool names, no jargon, one question at a time, and a sensible default offered with every question so they can just say "yes".

The template lives at `${CLAUDE_PLUGIN_ROOT}/template/`. Never edit it. You copy from it with the bundled script, which does the copying, removal and renaming. You don't do those by hand.

## Steps

### 1. Check the computer is ready

Check quietly for `uv`, `make`, and `git` (and `bun` later, only if the project keeps the frontend). Don't list them to the person.

- **Missing `uv`, `make` or `bun`:** tell them in one sentence that a couple of free tools need installing, and ask before installing each one. Show the command you'll run. Never install anything without a yes.
- **Native Windows without WSL:** this setup needs `make`, which Windows doesn't have. Tell them plainly that it currently needs WSL (a free Windows feature) and offer to walk them through turning it on. Don't work around it.
- **No `git`:** fine. Carry on and skip the git steps below.

### 2. Interview

Read `references/questions.md` and follow it. It maps each plain question to a module or value. Ask one at a time, in order, and skip any the brief already answered.

### 3. Confirm

Play the plan back in plain words before creating anything, for example: "I'll make **Bakery Orders** in `~/projects/bakery-orders`: a website your customers open in a browser, sign-in for anyone with a Google account, and no AI agents. Sound right?" Change it until they say yes.

### 4. Create the project

```bash
uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py \
  --dest <folder> --name <kebab-name> --display-name "<Display Name>" \
  --remove <comma-separated modules> \
  --env PROJECT_ID=<id or empty> --env NAMESPACE=<kebab-name> \
  --env VALID_DOMAINS=<domains or empty> --env USE_EMULATOR=<true|false>
```

It prints JSON. An `error` key means nothing was written: fix the input (or ask the person) and run it again.

### 5. Tidy the docs

`leftover_refs` lists lines in the new project that still mention removed parts, almost all in `Readme.md`, `AGENTS.md` and `docs/`. Edit each so it no longer mentions them: delete rows and sentences about the removed part, and reword the rest. Touch prose only. If a hit is in code, stop and tell the developer who maintains stackkit, because the template's manifest is missing something.

### 6. Prove it works

In the new folder:

```bash
git init -q                      # only if git is installed
uv lock && uv sync --all-extras --all-groups
cd frontend && bun install && cd ..   # only if the frontend was kept
make check
```

If `make check` fails, read the error. Fix it only if the bootstrap caused it (a leftover reference, a missed rename). Anything else, tell the person plainly that the project was created but one check failed, and show the developer-facing error separately. **Never call a failing project done.**

`make setup` needs git, so skip it when git is missing. The commands above cover the same installs.

### 7. Hand over

Tell them in three or four plain sentences:
- where the project is and what it can do now
- how to start it: `make run`, then open http://localhost:8000
- what's not done yet: putting it on the internet needs a Google Cloud account and can cost money, so it's a separate step you'll do together and only with their go-ahead

## Rules

- **Nothing billable, nothing silent.** Don't create cloud projects, enable billing, deploy, or change access permissions during a bootstrap, even if asked mid-interview. Note it as the next step.
- **No employer or personal information** from anyone but the person in front of you goes into the project.
- **One project per run.** If they describe two different apps, make the first and offer the second after.
