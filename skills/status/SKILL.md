---
name: status
description: Show where a project made with stackkit stands, printed in the chat - a checklist of what's left to set up (tools to install, keys for .env, the cloud database and file storage to create, sign-in setup) and its estimated monthly cost once it's online. Use when someone asks, in a stackkit project, for its status, a summary, a checklist, what's left to do or set up, what's missing, or what it will cost.
allowed-tools:
  - Bash(uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/../create/scripts/status.py *)
  - Read
---

# status

Print, in the chat, where the project stands: what's left to set up and what it will cost once it's online. Talk in the same plain words as the interview. This only looks: it never installs, creates or changes anything. Speak as the interview does (its "Describe what a thing does, never what it's called" list): no product names, file formats or script output.

## Steps

1. Run the report on the project (the current folder, unless they name another):

   ```bash
   uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/../create/scripts/status.py --dest <folder>
   ```

   An `error` means the folder isn't a stackkit project. Say so plainly, and offer to set one up or move it onto stackkit.
2. Read `${CLAUDE_PLUGIN_ROOT}/skills/create/costs.md` for the cost lines. Use the report's `display_name` as the project's name.
3. Print the summary below. Run nothing else.

## The summary

Plain words first. Where a step is for whoever puts it online, keep the exact name or command in brackets or code after the plain words, so they can act on it.

The `create` skill prints this same summary at the end of a build, from the `status` in `check.py`'s output. Keep the order and wording.

> **Bakery Orders**, checked 2026-11-03
>
> A page your staff open in a web browser, which remembers orders. Only people you let in can open it.
>
> **How it runs:** it switches off when nobody's using it, so the first visit after a quiet spell waits a few seconds, and it never runs more than 2 copies at once, so a busy day slows it down rather than running up the bill.
>
> **Still to do**
> - [x] Everything needed to run it on this computer is installed
> - [ ] Install Java, for the local database copy. Run once in a terminal:
>   ```
>   <the entry's run commands, one per line>
>   ```
> - [ ] Put your Stripe key in the project's private settings file (`.env`, as `STRIPE_API_KEY`), for testing. Whoever puts it online adds it to Google's locked store for keys (Secret Manager).
> - [ ] Put your Google Cloud project's ID in `.env` as `PROJECT_ID` (ask whoever's putting it online)
> - [ ] Google Cloud access: setting it up and putting it online needs the **Owner** role on the Google Cloud project (a basic role Google also calls legacy), or the specific roles for each step, or someone who has them, like an admin or a friend with Owner, to do those steps for you (not checked yet: PROJECT_ID is blank). The roles for each step are in "Google Cloud Access" in `docs/ENVIRONMENTS.md`.
> - [ ] Let Google build the server: it needs one permission it doesn't get by default (Cloud Run Builder, `roles/run.builder`). Someone with Owner runs `make -C gcp setup-iam` once. Without it, putting it online fails with a permission error.
> - [ ] Create the database `bakery-orders` in Google Cloud (not checked yet: PROJECT_ID is blank). Whoever puts it online runs `make -C gcp provision`.
> - [ ] Set up Google sign-in in front of the site, once per Google Cloud account (can't be checked from here; the steps are under "IAP First-Time Setup" in `docs/CLOUD.md`)
>
> **Cost once it's online: about $0 a month.** The database and the server sleeping when idle both fit in Google's free allowance. Buying a web address is separate.
>
> Ask for the status again any time to refresh this list.

Build it from the report, in this order, ticking what's done:

- **What it is:** one sentence from `parts`: a page in the browser (`frontend`), remembers things (`database`), keeps files (`storage`), who can get in (`auth_iap`: people you let in; `auth_firebase`: people with their own accounts; neither: anyone), AI (`ai`, `agents`).
- **How it runs:** from `scaling`, one sentence per host (usually one). `min` 0: switches off when nobody's using it, so the first visit after a quiet spell waits a few seconds. `min` 1 or more: always has that many copies ready, so visits never wait, billed while idle. Then the cap: "never runs more than <max> copies at once". If `max` is null, add an unticked line to the checklist: "Add a cap on how many copies run at once (in `<file>`), so a busy day can't run up the bill". Leave the section out when `scaling` is empty (a static site, whose pages are always instant).
- **Tools:** one unticked line per `tools` entry: "Install <tool>, for <needed_for>", then its `run` commands, in order, in one code block, to run once in a terminal (they may ask for the computer's password). Don't write commands or versions of your own: the script keeps them up to date. If `run` is empty, or a command fails because a package isn't found, point them to the Java and Firebase steps in the project's `docs/ENVIRONMENTS.md`. With no entries, one ticked line: everything needed is installed.
- **`.env`:** if it doesn't exist, one line: copy `.env.sample` to `.env`. Then one line per secret name: ticked if `set`, otherwise "Put your <service> key in the project's private settings file (`.env`, as `<NAME>`), for testing. Whoever puts it online adds it to Google's locked store for keys (Secret Manager)." Then `PROJECT_ID` if it's in `blank`. Leave out `VALID_DOMAINS` (blank lets any account in, which is intended). Mention any other blank key by name. Never print a value, even one you can see.
- **Google Cloud access:** from `access`, when it isn't empty. One line saying setting it up and putting it online needs the **Owner** role on the Google Cloud project (a basic role Google also calls legacy), or the specific roles for each step, or someone who has them (an admin, or a friend with Owner) to do those steps; point to "Google Cloud Access" in `docs/ENVIRONMENTS.md` for the roles. Ticked only when `checked` and every step's `can` is true; then say which account (`account`) was checked. When `checked` with some `can` false, add under it the steps that account can't do yet, each with its `roles`, and say they can ask for those roles or the Owner role, or have someone who has them do it. When not `checked`, add "(not checked yet: <reason>)".
- **Build account:** only when `access` has `build_account` (Cloud Run). Ticked when `ready` is true. Otherwise: "Let Google build the server: it needs one permission it doesn't get by default (Cloud Run Builder, `roles/run.builder`). Someone with Owner runs `<fix>` once." Say that without it, putting it online fails with a permission error, and add "(not checked yet: <reason>)" when `ready` is null.
- **Cloud:** one line per `cloud` entry: the database (`database`) or file storage (`storage`), by `name`. `exists` is ticked. `missing`: "Create … in Google Cloud. Whoever puts it online runs `<create>`." `unchecked`: the same, plus "(not checked yet: <reason>)".
- **Sign-in:** with `auth_iap`, the unticked IAP line above. With `auth_firebase`: "Turn on Google sign-in for staff or customers at Google (can't be checked from here; the steps are under 'Enable Firebase' in `docs/CLOUD.md`)."
- **Cost:** from `costs.md`, using its "Which rows apply" and "Adding it up".
- End with the line about asking again.

## Rules

- **Look, don't touch.** Never install anything, write `.env`, create cloud resources or deploy, even if asked here; say what to run and who runs it. Setup at Google is done by whoever puts it online.
- **Never show a secret.** The report only says `set` or `blank`; don't open `.env` to look.
