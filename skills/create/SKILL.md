---
name: create
description: Second half of stackkit's bootstrap. Builds, tidies and checks a project from a plan the bootstrap skill's interview has already confirmed - a new project, a project moved onto stackkit, or parts added to an existing stackkit project. Invoke only from the bootstrap skill, right after the person says yes to the plan.
user-invocable: false
allowed-tools:
  - Bash(uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py *)
  - Bash(uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/check.py *)
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - NotebookEdit
---

# create

Build what the person just agreed to: a new project, a project moved onto stackkit, or parts added to their stackkit project. The plan is the one confirmed in the conversation; don't ask anything new until the hand-over. Everything here runs in this one reply: the `allowed-tools` above are approved only for the turn this skill is invoked in, so finish every step before you write anything that invites a reply. If you have to stop and come back in a later turn (say, after a fix), invoke this skill again first.

Talk to the person in the same plain words as the interview, following its "Describe what a thing does, never what it's called" list. Commands, paths, script output, file formats and errors are for you, not them: tell them what happened and what it means, never what a script printed.

Run no shell commands but the two scripts below. Look at files with Read, Grep and Glob, and change them with Edit and Write (NotebookEdit for `.ipynb`): those are approved for this turn, while any other command (`ls`, `cat`, `grep`, `sed`) stops to ask the person, who can't judge it.

The template lives at `${CLAUDE_PLUGIN_ROOT}/template/`. Never edit it.

## 1. Create the project, or add to it

**New or moved project:**

```bash
uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py \
  --dest <folder> --name <kebab-name> --display-name "<Display Name>" \
  --remove <comma-separated modules> \
  --env NAMESPACE=<kebab-name> [--env VALID_DOMAINS=<domain>] \
  [--convert] [--copy <old path>=<path in new project> ...]
```

Pass `VALID_DOMAINS` when question 5 was (b) a staff area or (c) team-only without outsiders: the email ending or the addresses from 5c, comma separated. When moving an existing project, pass one `--copy` for each file or folder on the move list; it copies them in last, leaving out `.env` files, installs and caches, and lists them under `carried`. Each target must sit inside one of the project's folders (`frontend/public/images`, not `images` or `legacy/images`); the script refuses anything else so the project keeps stackkit's layout. Pass `--convert` when the person chose to turn the existing folder itself into the new project: the script moves everything but `.git` to the `old_files` folder it reports, builds the project in its place, and reads `--copy` sources from there, so give them as the old paths. It reports `removed`, every module removed, including the ones the script removed on its own because nothing kept needs them. An `error` key means nothing was written. If the module list is impossible (the error names what needs what), the interview's mapping went wrong: fix the list to match what the person agreed and run it again. If only the person can fix it (the folder is taken, say), tell them and stop.

**Adding to an existing stackkit project:**

```bash
uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/bootstrap.py \
  --dest <project> --add <comma-separated modules> \
  [--display-name "<Display Name>"] [--env VALID_DOMAINS=<domain or addresses>] \
  [--copy <other project path>=<path in the project> ...]
```

Pass `--display-name` when the project has no web page yet and one is being added. The script renders the template with the project's parts and with the added ones, and applies the difference. It prints `added` (with anything the added parts need), `new_files` (copied in), `updated` (shared files the project hadn't changed), `merged` (files the project had changed, merged with the new part's lines) and `env_added` (blank keys added to `.env`). Everything there is done. A new server brings its request examples with it (`http_tests`).

`conflicts` lists what it couldn't merge, untouched. For each one with a `diff`, make that change by hand with Edit: add the diff's `+` lines and remove its `-` lines, keeping the project's own changes around them. "No longer used, but the project changed it" means the file only mattered before the addition: move anything the person added there to where it now belongs, and tell them it can be deleted. "The project already has a file here": compare the two and keep both behaviours. An `error` means nothing was changed.

## 2. Tidy the docs

The script has already deleted the table rows, list items and example-code lines that only described removed parts. Where that left a whole table or code example empty, the script removed it too and lists the spot in `doc_blocks_emptied`: reword or remove the heading or sentence that introduced it. `leftover_refs` lists what's left that still mentions a part the project doesn't have: prose and headings, almost all in `Readme.md`, `AGENTS.md` and `docs/`. When adding to a project, it also catches docs left over from its first build. Edit each so it no longer mentions them: delete sentences about the missing part, and reword the rest. Touch prose only, and only files inside the new project. If a hit is in code, stop and tell the developer who maintains stackkit, because the template's manifest is missing something.

If the plan lists secret names (a service can have several, like Twilio's account ID, token and sending number), add each one to two places in the new project, with Edit: the `SECRET_KEY_NAMES` list in each `*_service/app_settings.py` the project has (`api_service`, `agent_service`, `job_service`; replacing the `"TODO"` placeholder) and the `SECRETS=()` array in `gcp/bin/setup_iam.sh`. Add a blank `NAME=` line for each to `.env.sample` and `.env`. Never write a real value. Tell the person at hand-over that they will need to put the keys in `.env` for testing, and that the keys go into Google's locked store when it's put online (the hand-over's note says how). Never create an API key for Claude or Gemini: they need none.

If the project kept `auth_iap`, tell them at hand-over, in plain words, that Google sign-in is set up once per Google Cloud account, and that stackkit doesn't do it. Tailor the "IAP First-Time Setup" section of `docs/CLOUD.md` with Edit: 5d yes (already set up) → keep only `make iap-grant`; otherwise keep the full order, and when question 12 was (a) or (c) also the "Handing this to an admin" note, filled in with the project's name and the people to let in (5b, with client emails), to go into the hand-over note. If 5b was yes, mention that clients are added one by one with `make iap-grant MEMBER=user:<email>`. Never run these commands and never ask for the OAuth client secret.

If question 5 was (b), a staff area: build it now, because the person agreed to it and the base has no sign-in screen. Protect each staff route on the server with `@firebase_auth_required()`; add a small sign-in screen for staff with Google sign-in from Firebase's web library (add it to `frontend/package.json`), which sends the signed-in staff member's token with each staff request; and put the staff pages behind it. The public pages stay open. `VALID_DOMAINS` decides who counts as staff.

Build each piece of background work in the plan as a first version, by what starts it and how long it takes (questions 7 and 7b):

- **Quick, on a timer, with a server:** a server route that does the work when called, protected so only staff or Google's timer can call it, and a make target that calls it by hand (`make reminders`).
- **Long, or a project with no server:** a job. Copy `job_service/jobs/example.py` to `job_service/jobs/<name>.py`, put the work in its `main()`, and add a test like `tests/test_example_job.py`. On a timer, note the time in the hand-over: `make schedule-job JOB=<name> SCHEDULE="<cron>" TIME_ZONE=<zone>` sets it once it's online. Delete the example job once a real one exists, keeping its test pattern.
- **Long, and a person waits:** a job as above, started by a server route. The route saves a "working on it" record in the database and returns at once; the job updates the record when done, and the page checks the record until it's finished. Online, the route starts the job through Cloud Run's API (the `google-cloud-run` library: `JobsClient.run_job` with an environment override carrying the record's id), which needs `roles/run.developer` for the server's account, granted next to its other roles in `gcp/bin/setup_iam.sh`. On this computer (`settings.is_local`), the route runs the job's `main()` as a background task instead, so it works without Google.
- **Another website sending something** (a payment notice): a server route that receives it and checks it really came from that service, as its instructions describe.
- **A reaction to a new file or record:** stackkit doesn't have this part yet. Build it by hand, following `${CLAUDE_PLUGIN_ROOT}/skills/create/reactions.md`, and say at hand-over that it's a first version outside the parts stackkit tests.

Say at hand-over what each one does, how to run it by hand, and that a timer at Google runs the scheduled ones once it's online.

## 3. Move the code across

When moving a project, or adding a feature from another project, a doc or a list of points. A feature they described in a doc or points (with no code to copy) is built as a first version from that description, using the parts just added. Follow `${CLAUDE_PLUGIN_ROOT}/skills/create/moving.md`: it lists where each part goes and how to adapt it, with a full mapping for Next.js. The old code is in the old folder, the `old_files` folder after `--convert`, or the other project; read it with Read, Grep and Glob. Follow the decisions the person made in the interview exactly.

The copied code is already in place. Adapt it with Edit so the project's own make targets run it (`make run`, `make build`, `make check`), and write only the glue with Write: routes in `App.tsx`, FastAPI routes for the old server code, Firestore models, make targets for the old scripts, and the dependencies the moved code imports. Follow the new project's `AGENTS.md` (its folders, routes, clients and coding standards). Everything lands in stackkit's folders; never recreate the old layout, add a top-level folder, or keep the old code as a `legacy/` copy. Content (text, prices, menus) comes across word for word, and old tests come along on Vitest or pytest.

Never change the old files (the old folder, or `old_files` after `--convert`), and never copy a key's value, even if one is written in its code: secret names only, as in step 2. Don't move live data. If something turns out not to fit, or breaks in a way you can only fix by changing what it does for its users (a library that won't run in the browser, a feature with no equivalent here), don't guess and don't drop it quietly: leave it out, keep the rest working, and add it to the "Needs your decision" list for the hand-over, with what it does now and two or three options. Fixes that keep the behaviour the same (an import, a type, a renamed setting) are yours to make.

## 4. Prove it works

```bash
uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/scripts/check.py --dest <folder>
```

It runs `git init` (when git is installed), `uv lock`, `uv sync`, `bun install` (when the frontend was kept), `make check` and `make build`, and stops at the first failure. Always use the script, not those commands one by one: each separate command would ask the person for permission.

If `ok` is false, read `failed` and `output`. Fix it only if the bootstrap or the move caused it (a leftover reference, a missed rename, moved code that doesn't lint, typecheck, test or build yet), then run the script again. Anything else, tell the person plainly that the project was created but one check failed, and show the developer-facing error separately. **Never call a failing project done.**

## 5. Hand over

Tell them in three or four plain sentences, then print the summary below:
- where the project is and what it can do now
- when adding: what was added, that their own changes were kept, and which files were fitted together with them (`merged` and the conflicts you resolved), so they can look them over. If the project is in git, say the changes aren't saved yet
- when moving a project: what came across, anything that didn't, and where the old files are (the untouched old folder, or `<folder>-before-stackkit` after converting), so they can compare and delete them when they're happy. After converting, if the folder has git history, say the change is ready to save as one step but not saved yet; don't commit it
- how to start it: `make run`, then open http://localhost:8000. If it kept `database` or `storage`, saving only works while the local database copy runs too: `make emulator` in a second window.
- with background work: how to run each one by hand (`make run-job JOB=<name>`); with only background work, that replaces `make run` and the web address.
- who puts it online, from question 12: (a) or (c) → end the hand-over with a short, ready-to-send note for that person: what the project needs at Google (from the summary's checklist), the access it takes ("Google Cloud Access" in `docs/ENVIRONMENTS.md`), and the commands. (b) → give them those steps directly, starting with the access they need.
- what's not done yet: stackkit sets up the base, not the features, so the brief's own screens (and sign-up and login, for customer accounts) come next. When moving a project, the moved app is already there; what's left is only what didn't come across. It runs on this computer for now. Putting it on the internet is done outside stackkit, by whoever they named at question 12; the project is named so it can sit alongside other apps in a shared Google Cloud project. Don't offer to deploy it.

### The summary

Then print the project's summary: the checklist of what's left to set up and the estimated monthly cost, printed in the chat. Build it from `status` in `check.py`'s output, exactly as "The summary" in `${CLAUDE_PLUGIN_ROOT}/skills/status/SKILL.md` describes, with costs from `${CLAUDE_PLUGIN_ROOT}/skills/create/costs.md`. Don't install anything yourself: the person runs the commands it lists. It ends by telling them they can ask for the status again any time to refresh it.

### Needs your decision

If the move left anything on the "Needs your decision" list, put it after the summary, last, since it asks them something: one line per item, then ask about the first with AskUserQuestion, the recommended option first. Once they answer, make the change and check again in the next turns (invoke this skill again first, so its permissions apply), then ask about the next.

## Rules

- **No deploys, nothing billable.** stackkit doesn't manage deploys. Don't create cloud projects, enable billing, deploy, or change access permissions, even if asked; say it's handled outside stackkit.
- **Change only the project being built or added to.** The broad file-tool approval is for it, nothing else. Read old projects and other projects, but never change them.
