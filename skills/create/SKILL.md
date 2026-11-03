---
name: create
description: Second half of stackkit's bootstrap. Builds, tidies and checks a project from a plan the bootstrap skill's interview has already confirmed. Invoke only from the bootstrap skill, right after the person says yes to the plan.
user-invocable: false
allowed-tools:
  - Bash(uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py *)
  - Bash(uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/check.py *)
  - Read
  - Grep
  - Glob
  - Edit
  - NotebookEdit
---

# create

Build the project the person just agreed to. The plan is the one confirmed in the conversation; don't ask anything new. Everything here runs in this one reply: the `allowed-tools` above are approved only for the turn this skill is invoked in, so finish all four steps before you write anything that invites a reply. If you have to stop and come back in a later turn (say, after a fix), invoke this skill again first.

Talk to the person in the same plain words as the interview. Commands, paths and errors are for you, not them.

Run no shell commands but the two scripts below. Look at files with Read, Grep and Glob, and change them with Edit (NotebookEdit for `.ipynb`): those are approved for this turn, while any other command (`ls`, `cat`, `grep`, `sed`) stops to ask the person, who can't judge it.

The template lives at `${CLAUDE_PLUGIN_ROOT}/template/`. Never edit it.

## 1. Create the project

```bash
uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py \
  --dest <folder> --name <kebab-name> --display-name "<Display Name>" \
  --remove <comma-separated modules> \
  --env NAMESPACE=<kebab-name> [--env VALID_DOMAINS=<domain>]
```

Pass `VALID_DOMAINS` only for a team-only project. It prints JSON: `removed` lists every module removed, including the ones the script removed on its own because nothing kept needs them. An `error` key means nothing was written. If the module list is impossible (the error names what needs what), the interview's mapping went wrong: fix the list to match what the person agreed and run it again. If only the person can fix it (the folder is taken, say), tell them and stop.

## 2. Tidy the docs

`leftover_refs` lists lines in the new project that still mention removed parts, almost all in `Readme.md`, `AGENTS.md` and `docs/`. Edit each so it no longer mentions them: delete rows and sentences about the removed part, and reword the rest. Touch prose only, and only files inside the new project. If a hit is in code, stop and tell the developer who maintains stackkit, because the template's manifest is missing something.

If the plan lists secret names, add each one to two places in the new project, with Edit: the `SECRET_KEY_NAMES` list in `service/app_settings.py` (replacing the `"TODO"` placeholder; do the same in `agent_service/app_settings.py` if it exists) and the `SECRETS=()` array in `gcp/bin/setup_iam.sh`. Add a blank `NAME=` line for each to `.env.sample` and `.env`. Never write a real value. Tell the person at hand-over that they will need to put the keys in `.env` for testing, and that whoever looks after their Google Cloud adds them to Secret Manager. Never create an API key for Claude or Gemini: they need none.

If the project kept `auth_iap`, tell them at hand-over, in plain words, that sign-in is set up once per Google Cloud project, and that stackkit doesn't do it. Tailor the "IAP First-Time Setup" section of `docs/CLOUD.md` with Edit to the answer at 5d: (b) already set up → keep only `make iap-grant`; (c) they do it → keep the full order; (a) someone else or don't know → keep the full order and the "Handing this to an admin" note, and give them that note in your reply to forward, filled in with the project's name and the people to let in (5b, with client emails). If 5b was yes, mention that clients are added one by one with `make iap-grant MEMBER=user:<email>`. Never run these commands and never ask for the OAuth client secret.

## 3. Prove it works

```bash
uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/check.py --dest <folder>
```

It runs `git init` (when git is installed), `uv lock`, `uv sync`, `bun install` (when the frontend was kept) and `make check`, and stops at the first failure. Always use the script, not those commands one by one: each separate command would ask the person for permission.

If `ok` is false, read `failed` and `output`. Fix it only if the bootstrap caused it (a leftover reference, a missed rename), then run the script again. Anything else, tell the person plainly that the project was created but one check failed, and show the developer-facing error separately. **Never call a failing project done.**

## 4. Hand over

Tell them in three or four plain sentences:
- where the project is and what it can do now
- how to start it: `make run`, then open http://localhost:8000. If it kept `database` or `storage`, saving only works while the local database copy runs too: `make emulator` in a second window.
- what's not done yet: stackkit sets up the base, not the features, so the brief's own screens (and sign-up and login, for customer accounts) come next. It runs on this computer for now. Putting it on the internet is handled outside stackkit, by whoever looks after their Google Cloud; the project is named so it can sit alongside other apps in a shared Google Cloud project. Don't offer to deploy it.

## Rules

- **No deploys, nothing billable.** stackkit doesn't manage deploys. Don't create cloud projects, enable billing, deploy, or change access permissions, even if asked; say it's handled outside stackkit.
- **Edit only the new project.** The broad file-tool approval is for its docs, nothing else.
