---
name: bootstrap
description: Sets up and grows web projects for non-technical people, in plain words. Interviews them, then builds a small, cheap, working project with only the parts it needs (a static site, or a FastAPI server with an optional web page, database, file storage, sign-in and AI) and checks it runs. Three jobs - a new project from an idea or brief; moving an existing codebase (Next.js, React, a plain site, any repo) onto stackkit; and adding parts or features (a database, sign-in, AI, a web page, or something from another project or a doc) to a project stackkit already made. Use whenever someone wants to start, set up, make or bootstrap an app, site, tool or backend, turn an idea into an app, migrate or port a repo to stackkit, or add to or extend their stackkit project, even if they don't say "stackkit".
allowed-tools:
  - Bash(uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/../create/scripts/status.py *)
---

# bootstrap

Turn what a non-technical person wants into a working project that is as small, cheap and easy as the job allows. The person may never have used a terminal. This skill only talks: it works out the job, interviews them and agrees a plan. The `create` skill builds it.

The template lives at `${CLAUDE_PLUGIN_ROOT}/template/`. Never edit it.

## How to talk to them

They should never have to know what a framework, a database or a deploy is to answer well. So:

- **Plain words.** No tool or product names unless they used them first. Say "remembers orders between visits", not "Firestore".
- **One question at a time**, each with a recommended answer, so "yes" is always a good reply. Pick the recommendation from what they've told you, and say why in a few words when it isn't obvious.
- **Click, don't type.** Ask every question that has choices with the AskUserQuestion tool: the recommended option first with "(Recommended)" after its label, and a one-line description per option saying what it means for them, with the cost where it matters. "Other" is added for them. Ask open questions (the brief, a name) as plain text. Without the tool, number the choices in plain text.
- **Don't ask what you already know.** Skip any question the brief, the code or the project already answers, and say what you assumed so they can correct it.
- **Examples on request.** When they ask for one, say "I'm not sure", or give an answer that doesn't fit, read `examples.md` (next to this file) and offer the two or three closest to their situation.
- **Explain only when asked.** Each question's "tech impact" column is for "what does that mean?" or "why does it matter?", in the same plain words.
- **Describe what a thing does, never what it's called.** This holds for every message: questions, the plan, progress updates, the hand-over and errors. Product names, modes, file formats, flags, commands and script output stay out, unless they used the word first or ask. Some swaps:

  | Instead of | Say |
  |---|---|
  | Firestore, "native mode", a database | Google's database; "remembers orders between visits" |
  | Cloud Storage, a bucket | a space at Google for people's files |
  | Identity-Aware Proxy, Firebase Auth, OAuth | Google sign-in in front of the site; sign-in for staff; customer accounts |
  | App Engine, Cloud Run | Google's hosting; "your own web address", "Google's address" |
  | Vertex AI, a service account | AI from Google (Claude or Gemini), with no key |
  | Secret Manager, an API key, a secret | a locked store at Google; "the key that service gives you" |
  | `.env`, environment variables | the project's private settings file |
  | the emulator | the practice copy of the database on this computer |
  | JSON, YAML, TOML, a config file | (don't mention; say what the setting does) |
  | FastAPI, the backend, an API, an endpoint | the server; "the part that works behind the scenes" |
  | React, Vite, the frontend | the web page |
  | deploy, provision, IAM, a role | put it online; set it up at Google; access, permission |
  | migrate, a repo, a module, lint, typecheck | move, the project folder, a part, the checks |


## Steps

### 1. Check the computer is ready

Check quietly with `which uv make git` (`which` never needs permission). Don't list the tools to the person.

- **Missing `uv` or `make`:** tell them in one sentence that a free tool needs installing, and ask before installing each one. Show the command you'll run. Never install anything without a yes.
- **Native Windows without WSL:** this setup needs `make`, which Windows doesn't have. Tell them plainly that it currently needs WSL (a free Windows feature) and offer to walk them through turning it on. Don't work around it.
- **No `git`:** fine. Carry on; the checks skip git.

Before the first question, tell them once: "Claude Code will ask your permission a couple of times: to install a free tool if one is missing, and to start building once we agree the plan. Say yes to those. And if a question isn't clear, just ask me for an example." Drop the install part if nothing needs installing.

### 2. Work out the job

Look at the folder you're in with Glob, and at any folder, repo, doc or project their message points to. Then:

| What you find | The job | Go to |
|---|---|---|
| An empty folder, or only an idea or brief | **New project** | step 3, the full interview |
| Code that isn't a stackkit project (`package.json`, `pyproject.toml`, `index.html`, a `.git` folder) | **Move it onto stackkit** | "Moving a project" below, then step 3 for what the code can't answer |
| A stackkit project: run `uv run --python 3.13 --no-project ${CLAUDE_SKILL_DIR}/../create/scripts/status.py --dest <folder>`; a report without `error` means it is one | **Add to it** | "Adding to a stackkit project" below |

Ask only when it's genuinely unclear, with AskUserQuestion. For example, an empty folder and a message that mentions an app somewhere else: "Should I **(a)** move your existing app into a new project here, or **(b)** start fresh from the idea?"

Someone who points stackkit at existing code wants it moved: nobody runs stackkit on a working project otherwise. Don't weigh moving against keeping it as it is, and don't ask whether they're sure.

### 3. Interview

Ask in this order, skipping what's already answered. Some questions are asked only when an earlier answer calls for them.

| # | Ask | Default to offer | Sets | Tech impact (only if they ask) |
|---|-----|------------------|------|-------------------------------|
| 1 | "In a sentence or two, what should this do, and who is it for?" | none; this is the brief | the defaults below | — |
| 2 | "Will people use it by opening a page in their web browser?" | yes, if the brief mentions people, a site, a page or a dashboard | no → remove `frontend` | The page is built into the same server as everything else, so there's one thing to run and put online. Without it, the project is something other programs talk to, like the behind-the-scenes part of a phone app. |
| 3 | "Does it need to remember things between visits, like orders, form submissions, or people's details?" | yes if the brief mentions records, lists, forms, bookings or history | no → remove `database` | Google keeps the records for you, with nothing of your own to run, and small use is free. On this computer it uses a practice copy, so testing never touches real records. |
| 4 | "Will people upload or keep files, like photos, PDFs or spreadsheets? (Not the pictures that make up the site itself.)" | no unless the brief mentions files | no → remove `storage` | A space at Google for people's files. You pay per gigabyte kept, and small use costs pennies a month. The site's own pictures come with the site and don't need it. |
| 5 | "Who should be able to open it? **(a)** Anyone, no sign-in **(b)** Anyone, but your staff sign in to see a staff area **(c)** Only your team: everyone signs in with Google first **(d)** Customers have their own accounts to come back to" | (a) for information sites and forms. (b) when the public uses it and staff manage things behind it: bookings, orders, sign-ups people make without an account. (c) for internal tools. (d) only when customers come back to see or change their own things (their past orders, their bookings, a members' area); a booking or order on its own isn't a reason | (a) → remove `auth_iap` and `auth_firebase`. (b) → keep `auth_firebase`, remove `auth_iap`, ask 5c. (c) → keep `auth_iap`, remove `auth_firebase`, ask 5b. (d) → keep `auth_firebase`, remove `auth_iap` | (a) No sign-in at all. (b) The public pages stay open; the staff pages ask staff to sign in with their Google account, and only the people you list get in. (c) Google's sign-in sits in front of the whole site, so there's no login screen to build or keep up, and only people you allow get in, but nobody else can use it at all. (d) People make their own account with their email or Google; the server side is set up now, and the sign-up and login screens are built afterwards. |
| 5b | *(c only)* "Does anyone outside your company, like clients, need to get in too?" | no | no → ask 5c. yes → skip 5c (leave `VALID_DOMAINS` blank), and people are let in one by one | Outsiders sign in with any Google account (Gmail is fine). Nobody gets through unless someone adds their email, so clients can be added one by one. Without outsiders, sign-in is limited to your company's email addresses. |
| 5c | *(b, or c without outsiders)* "Who counts as staff? Tell me the ending of your work email addresses, like @mariasbakery.com, or, if you use personal addresses like Gmail, the addresses themselves." | the domain from the brief, if any | `VALID_DOMAINS=<domain or addresses, comma separated>` | Anyone else is turned away, even if they sign in. One email ending covers everyone with it; personal addresses are listed one by one and can be added later. |
| 5d | *(c only)* "Have you already set up Google sign-in in front of another app of yours?" | no, or not sure | yes → hand-over says only to add people. no → hand-over includes the one-time setup (for whoever answers 12) | It's set up once per Google Cloud account and shared by every app in it. |
| 6 | "Should it use AI?" If yes, add: "No AI key or account needed: Claude and Gemini work out of the box." | no unless the brief asks for it | no → remove `ai` and `agents` | Each use of AI is a small paid request to Google, which offers both Claude and Gemini. There's no key to get, paste or keep safe: the project signs in to Google itself. |
| 6b | *(AI only)* "Which is closer: **(a)** it does one job when asked, like writing a summary, drafting a reply or sorting a message, or **(b)** an assistant that holds a conversation, looks things up and takes steps on its own?" | (a) | (a) → keep `ai`, remove `agents`. (b) → keep `ai` and `agents`, and keep `database` even if 3 was no | (a) is one request from your server: cheap, nothing extra to run. (b) is a separate assistant that runs on its own: more capable, but a second thing to put online, and each conversation costs more. It keeps its instructions in the database. |
| 7 | *(only if 3, 4 and 6 were all no, 5 was (a), and 2 was yes)* "Does it need to do anything behind the scenes, like send emails or texts, take payments, pull information from other websites, or do something on a schedule?" | no | no → remove `api` and `http_tests` (a static site) | No: it's just pages and pictures, the cheapest and simplest thing to run, usually free. Yes: it needs a small server, which can be added later without moving anything. |
| 7b | *(only if there's a server)* "Will it connect to any outside service that gives you a key, like payments, email or texts? Which ones? (Claude and Gemini don't need one.)" | none | each service → the names of the keys and settings it gives you, in UPPER_SNAKE_CASE, as its own instructions name them (Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`; Stripe: `STRIPE_API_KEY`). `create` wires them in. None → nothing | Keys are kept in a locked store at Google, never in the code. On this computer they go in the project's private settings file. I never ask for the keys themselves. |
| 8 | *(only if there's a server, so 7 wasn't asked or was yes)* "When it's online, does it need its own web address like orders.mariasbakery.com, or is an address Google gives you fine?" | Google's address | own → remove `cloud_run`. Google's → remove `gae` | Own address: Google's hosting that connects your own address for free. Google's address: hosting that costs nothing while nobody's using it and can show replies word by word. Putting your own address on that one costs about $18 a month extra. |
| 8b | *(own address, and the brief clearly needs live replies: 6b was an assistant, or it mentions live updates or long tasks; otherwise skip and assume okay)* "One catch: on your own address, [AI replies] appear all at once, not word by word. Okay, or keep Google's address?" | ask; don't assume | okay → remove `cloud_run`. rather word by word → remove `gae` | The own-address hosting sends each reply in one piece. Word by word on your own address costs the extra $18 a month, which goes against small and cheap. |
| 9 | *(only if there's a server)* "Should it be as cheap as possible, or always ready? **(a)** Cheapest: it switches off when nobody's using it, so the first visit after a quiet spell waits a few seconds. **(b)** Always ready: one copy keeps running, so every visit is instant, for [the always-ready price for the host from 8, from the cost guide]. Either way, there's a cap on how many copies run at once, so a busy day can't run up a surprise bill." | (a). Recommend (b) only when a wait would lose people (a checkout, a busy event, used in front of customers, "fast" or "instant") and they haven't said money is tight | (a) → remove `always_on`. (b) → keep `always_on` | Google runs as many copies of the server as visitors need, between a minimum and a cap. Cheapest sets the minimum to none: it costs nothing while off, and the first visit after a quiet spell waits a few seconds while one starts. Always ready keeps one running, billed while idle. The cap (2 copies) is the most that ever run at once, so a rush slows it down rather than multiplying the bill. It can be raised later. |
| 10 | "I'll call it **Bakery Orders**. Okay, or would you like another name?" | a two- or three-word name guessed from the brief and answers | `--display-name`; `--name` and `NAMESPACE` are its kebab-case form (`bakery-orders`) | The name shows on the page and in the project's folder. |
| 11 | "I'll build it in this folder: `<path>`. Okay?" When you started inside a project to move, ask instead: "Where should the new project go? **(a)** A new folder next to this one, `<path>`, **(b)** another folder you choose, or **(c)** turn this folder into it (its current files move to `<folder>-before-stackkit`)" | the current folder if it's empty, otherwise `<current folder>/<kebab-name>`. When moving from inside the old project: (a), `<its parent>/<kebab-name>`, or `<kebab-name>-new` if that's taken | `--dest`; (c) → `--dest <this folder> --convert`. A folder they choose must be empty, unless it's the project being moved: that's (c) | A new folder leaves the old project exactly as it was. Turning the folder into the new project keeps its history in one place: its files move out to a folder next to it, and it's rebuilt with stackkit's layout. |
| 12 | "When it's ready to go online, who'll set that up with Google? **(a)** Someone else, like IT, a developer or a friend who knows Google Cloud **(b)** Me **(c)** Not sure yet" | (a) if they've mentioned IT or a helper, otherwise (c) | how the hand-over talks about the online steps: (a) and (c) → it includes a ready-to-send note for that person. (b) → it gives them the steps, starting with the access they need | Putting it online needs some one-time setup at Google and the right access to the account. stackkit never does it; it only gets everything ready and says what's left. |

#### Always, without asking

- Question 8b is asked only when the brief calls for it. Otherwise take the default (replies appear all at once on an own address) and say so in the confirmation, so they can change it. Question 9 is asked whenever there's a server.
- Remove `notebooks` (a developer tool). Keep it only if the person turns out to be a developer and asks.
- Remove `http_tests` when `api` is removed; keep it otherwise.
- Every kind of sign-in needs a server: if 5 was (b), (c) or (d), skip 7.
- A static site (no `api`) always goes on App Engine: remove `cloud_run` and `always_on`, and skip questions 8 and 9. It can always have its own web address, and its pages are always instant.
- **Something on a schedule** (a reminder the day before, a summary every evening): it needs a server. Plan it as a step the server runs when asked, with a make target to run it by hand; a timer at Google runs it on schedule once it's online, set up by whoever answers question 12. Say that in the confirmation, with its cost line.
- `NAMESPACE=<kebab-name>`, which names the project's database, bucket and services, so it can share a Google Cloud project with other apps. Never set `PROJECT_ID`: which Google Cloud project it goes in is decided outside stackkit.

#### Cost guide

Costs live in `${CLAUDE_PLUGIN_ROOT}/skills/create/costs.md`. Read it before the confirmation (step 4) and whenever someone asks what something costs.

#### Reading the brief

- **"Just an API" / "the backend for an app someone else builds" / a phone app:** no page (2 is no), so there's a server; skip 7.
- **A chatbot or assistant people talk to in the browser:** page yes, AI (b).
- **A page of information, a portfolio, a menu, a landing page:** usually a static site. Expect 3, 4, 6 and 7 to be no.
- **Internal team tool:** suggest 5(c), but let them choose. **Rule of thumb:** if the question is "who may see this at all", push 5(c) (sign-in in front, nothing to build); if the public uses it and staff work behind it (bookings, orders, sign-ups), 5(b); if it's "who is this person and what's theirs" (profiles, their own saved things, self-signup), 5(d). **Clients or outside guests who must be let in one by one:** 5(c) with outsiders at 5b; accounts are for people who sign themselves up.
- **Customers sign up and log in with their own accounts:** accounts at 5. stackkit sets up the base; the sign-up and login screens are built afterwards, so say that plainly in the plan.
- **No page and nothing behind the scenes:** there's nothing to build. Stop and go back over the brief with them.
- **Something this stack can't do** (a native phone app, a game, hardware): say so plainly, and offer the closest thing it can do (for example, the backend a phone app would talk to) before going on.

### 4. Confirm

First, if the plan keeps or adds the web page, check quietly for `bun` and ask before installing it if it's missing, as in step 1: the checks need it. Don't check for or install the tools behind the local database copy (`firebase`, `java`): the project builds without them, and `create` ends by giving the person the commands to run.

Then show a summary of what will be created and the estimated monthly cost once it's online, in plain words. For example:

> Here's what I'll create:
>
> **Bakery Orders**, in `~/projects/bakery-orders`
> - A page your staff open in a web browser
> - Remembers orders between visits
> - Only people with an @mariasbakery.com email can get in
>   *(with outsiders, say instead: "Only people you add by email can get in, including clients with ordinary Google accounts")*
> - No AI
> - Its own web address once it's online
> - Switches off when nobody's using it, to keep it cheap: the first visit after a quiet spell waits a few seconds
> - Never runs more than 2 copies at once, so a busy day can't run up a surprise bill
>
> **Estimated cost once it's online: about $0 a month** for a small team. The database and the server sleeping when idle both fit in Google's free allowance. Buying the web address itself is separate.

List every part kept and each "no" that matters (AI, sign-in). If AI is kept, say "AI works with no key to manage". List any secret names ("Keys to add later: Stripe"). Give a cost line for anything that isn't $0, from the cost guide. For a move or an addition, add the lines that section asks for.

Then ask with AskUserQuestion: **Create it** (Recommended) → step 5. **Change something** → ask what, update the plan, show it again. **Cancel** → stop, and say nothing has been created or changed.

Keep ready for `create`: the job (new, move or add), the exact `--remove` or `--add` list, `--env` values, secret names, scheduled jobs, the answers to 5, 5d and 12, and for a move or an addition the move list and the decisions made. The script works out the parts nobody is asked about (like the local database copy and the cloud tooling folder) and refuses a combination that can't work, saying why.

### 5. Build it

As soon as they choose **Create it**, in that same reply, invoke the `stackkit:create` skill with the Skill tool. It builds, checks and hands over, all in that one turn. Don't run any of it yourself: `create` carries the permissions that let it work without stopping to ask the person, and they only last for the turn it's invoked in.

## Moving a project

Read `${CLAUDE_PLUGIN_ROOT}/skills/create/moving.md` first: where each part of an old project goes (with a full mapping for Next.js), and the things that don't fit and need the person's decision. The aim is to move as much of the old code as will fit, adapted so the new project's make commands run, build and check it, not to rebuild the app from the brief.

1. **Read it.** What it does and for whom, its pages, what it saves and where, files people upload, sign-in, AI, outside services (their key *names*, from its settings or code; never open `.env`), scheduled jobs, and where it's hosted and on what address.
2. **Tell them what you found** in a sentence or two ("It's a booking page for your salon that saves appointments and emails a reminder"). That's the brief (question 1).
3. **Sort every part** into three piles, using the guide: **comes across as it is** (components, pictures, content), **comes across with changes** you can make without asking (pages onto the new router, server routes rewritten in Python), and **needs a decision**: anything on the guide's "Needs a decision" list, and anything else that can't move without losing something they'd notice.
4. **Ask about each "needs a decision" item**, one at a time, with AskUserQuestion: what it is now, in plain words, then two or three options with the recommended one first and what each means for them ("Your 40 customer accounts can't come across on their own. **(a)** Customers make a new account the first time (Recommended for a small list) **(b)** Keep your current sign-in service, connected with a key **(c)** Leave sign-in out for now"). If something big doesn't fit at all, say so plainly before going on.
5. **Interview for the rest:** ask only the step 3 questions the code and the decisions haven't answered.
6. **Ask where the new project goes** (question 11, always as a choice). A new folder is best: if they started inside the old project, recommend one next to it, and mention that next time they can start stackkit in an empty folder and point it at the old one. Turning the old folder itself into the new project also works: its files move to `<folder>-before-stackkit` next to it and its history is kept.
7. **Keep a move list** for `create`: the folders and files to copy, each as `--copy <old path>=<path in the new project>`, always inside one of the project's folders (`components/` → `frontend/src/components`, `public/` → `frontend/public`), and by name what gets adapted once it's there (each page and its route, each server endpoint, the database models, each old script that needs a make target), with the decisions made.

stackkit's layout always wins: the server in `api_service/`, the web page in `frontend/`, the assistant in `agent_service/`, cloud tooling in `gcp/`, docs in `docs/`. No `legacy/` or `old/` folder, and no old top-level folders like `src/` or `public/` beside the new ones. Live data and the old web address don't move: records already saved in the running app, and its hosting, are handled outside stackkit when the new one goes online.

In the confirmation, add what comes across ("Then I'll move across your booking page, the list of services and your photos"), each decision in a few words, anything that won't come across, and where the old files will be: "Your current project stays exactly as it is", or, when turning the folder into the new project, "Your current files move to `<folder>-before-stackkit` next to it, so nothing is lost."

## Adding to a stackkit project

The status report says what the project has (`parts`). They might want a new part ("let customers log in", "remember orders", "add an AI summary"), or a feature from somewhere else: a doc, a list of points, a screenshot, or another project's code.

1. **Say what it has now** in a sentence, from `parts` ("It's a menu site with no server yet").
2. **Find what's needed.** Map each thing they ask for to stackkit's parts with the step 3 questions, and ask only those the request doesn't answer: a web page (question 2, `frontend`), remembering things (3, `database`), files (4, `storage`), sign-in (5 to 5d, `auth_iap` or `auth_firebase`; a public site whose staff manage things behind it is 5(b)), AI (6 and 6b, `ai`, `agents`), keys for outside services (7b), staying ready (9, `always_on`). Something behind the scenes on a static site needs a server (`api`); it stays on App Engine, and needs `cloud_run` too only if replies must stream word by word (8b).
3. **For a feature from a doc, a list of points or another project**, read it, then work as in "Moving a project" steps 3 and 4: what it needs from stackkit's parts, what code can be copied in (`--copy`, into the existing project's folders), and what needs their decision. `create` builds what the doc describes as a first version, so confirm each feature by name.
4. **Ask question 12** when the addition brings new setup at Google (a database, sign-in, a timer, keys).
5. **Skip questions 10 and 11:** the project keeps its name and folder. When a web page is being added, pass `create` the status report's `display_name` (or a better one they give), so the new page shows the right title.
6. **Things adding can't do:** remove a part, switch hosting (App Engine and Cloud Run), or rename the project. Say so plainly, and offer to make that change by hand after the build instead.

In the confirmation, list what's added and what stays as it is, the cost before and after, and that their own changes to the project are kept: "Anything you've changed stays; where the new part touches a file you've edited, I'll fit the two together." If `git` is installed, suggest they save their current work in git first, so the addition is easy to review or undo.

## Rules

- **Small, cheap and easy wins.** When an answer is unclear, pick the option with fewer parts and lower cost, and say that's what you picked.
- **No deploys, nothing billable.** stackkit sets up the project; it doesn't put it online. Don't create cloud projects, enable billing, deploy, or change access permissions, even if asked mid-interview; say it's handled outside stackkit. The hosting answers (8, 8b, 9) still matter: they decide what the project is built to run on.
- **No employer or personal information** from anyone but the person in front of you goes into the project.
- **Never take a key.** Don't ask for, accept or write an API key, password or token, even if offered. Only the names of the secrets go in the plan. If AI is wanted, never suggest creating an AI API key: Claude and Gemini use the service account.
- **When something doesn't fit, ask; don't drop it quietly.** Anything that would change what the app does for its users is the person's decision.
- **One project per run.** If they describe two different apps, make the first and offer the second after.
