---
name: bootstrap
description: Set up a new project from a plain-language idea. Interviews a non-technical person in everyday words, then creates a working, small and cheap web project with only the parts they need (a static site, or a FastAPI backend with optional web page, database, file storage, team-only access and AI), and checks that it runs before handing it over. Use when someone asks to: start a new project, set up an app, make me a website/tool/backend, turn my idea into an app, bootstrap a repo, create a project from stackkit.
---

# bootstrap

Turn a non-techie's brief into a working project that is as small, cheap and easy as the brief allows. The person you're talking to may never have used a terminal. Everything you say to them is in plain words: no tool names, no jargon, one question at a time, and a sensible default offered with every question so they can just say "yes".

The template lives at `${CLAUDE_PLUGIN_ROOT}/template/`. Never edit it. This skill only talks: it finds out what they need and agrees a plan. The `create` skill builds it.

## Steps

### 1. Check the computer is ready

Check quietly with `which uv make git` (`which` never needs permission). Don't list the tools to the person. More tools may be needed once you know the plan (step 3).

- **Missing `uv` or `make`:** tell them in one sentence that a free tool needs installing, and ask before installing each one. Show the command you'll run. Never install anything without a yes.
- **Native Windows without WSL:** this setup needs `make`, which Windows doesn't have. Tell them plainly that it currently needs WSL (a free Windows feature) and offer to walk them through turning it on. Don't work around it.
- **No `git`:** fine. Carry on; the checks skip git.

Before the first question, tell them once: "Claude Code will ask your permission a couple of times: to install a free tool if one is missing, and to start building once we agree the plan. Say yes to those. And if a question isn't clear, just ask me for an example." Drop the install part if nothing needs installing.

### 2. Interview

Ask in this order, one at a time, in these words or close to them. Skip any question the brief already answered, and say what you assumed. Some questions are asked only when an earlier answer calls for them.

Each question has a **tech impact**: what the answer changes under the hood, and what it costs. Don't volunteer it. Use it when they ask "what does that mean?" or "why does it matter?", in the same plain words.

Each question also has **examples** (after the table). Offer them when the person asks for one, says "I'm not sure", or answers something that doesn't fit the choices. Pick the two or three closest to their brief rather than reading the whole list, then ask the question again.

| # | Ask | Default to offer | Sets | Tech impact (only if they ask) |
|---|-----|------------------|------|-------------------------------|
| 1 | "In a sentence or two, what should this do, and who is it for?" | none; this is the brief | the defaults below | — |
| 2 | "Will people use it by opening a page in their web browser?" | yes, if the brief mentions people, a site, a page or a dashboard | no → remove `frontend` | A web page built into the same server as everything else, so there's one thing to run and put online. Without it, the project is something other programs talk to (like a phone app's backend). |
| 3 | "Does it need to remember things between visits, like orders, form submissions, or people's details?" | yes if the brief mentions records, lists, forms or history | no → remove `database` | Google's Firestore database. It stores records with no server of its own to run, and small use is free. On this computer it runs as a local copy, so testing never touches real data. |
| 4 | "Will people upload or keep files, like photos, PDFs or spreadsheets? (Not the pictures that make up the site itself.)" | no unless the brief mentions files | no → remove `storage` | A Google Cloud Storage space for files. You pay per gigabyte kept, and small use costs pennies a month. The site's own pictures ship with the code and don't need this. |
| 5 | "Who will use it: only your team, customers or the public with their own accounts, or anyone without signing in?" | anyone, or team if it sounds like an internal tool | team → keep `auth_iap`, remove `auth_firebase`, ask 5b. accounts → keep `auth_firebase`, remove `auth_iap`. anyone → remove both | Team: Google's sign-in sits in front of the whole thing (Identity-Aware Proxy), so there's no login screen to build or keep up, and only the email addresses you allow get in. Accounts: people sign up with their own email or Google account (Firebase Auth); the server side is set up now, and the sign-up and login screens are built afterwards. Anyone: no sign-in at all. |
| 5b | *(team only)* "What do your work email addresses end in, like @mariasbakery.com?" | the domain from the brief, if any | `VALID_DOMAINS=<domain>` | Anyone whose email ends differently is turned away. |
| 6 | "Should it use AI?" (If yes, say right away: "Good news: you don't need an AI key or account. Claude and Gemini both work out of the box, and the project signs in to them for you.") | no unless the brief asks for it | no → remove `ai` and `agents` | Each use of AI is a paid call to Google's Vertex AI, which serves both Gemini and Claude. There is no API key to get, paste or keep safe: the project uses its Google service account, and a key would be a worse, leakable way to do the same thing. |
| 6b | *(AI only)* "Which is closer: **(a)** it does one job when asked, like writing a summary, drafting a reply or sorting a message, or **(b)** an assistant that holds a conversation, looks things up and takes steps on its own?" | (a) | (a) → keep `ai`, remove `agents`. (b) → keep `ai` and `agents`, and keep `database` even if 3 was no | (a) is one AI call from your server: cheap, nothing extra to run. (b) is a separate assistant service built with Google's agent kit: more capable, but a second thing to put online, and each conversation costs more. The assistant keeps its instructions in the database. |
| 7 | *(only if 3, 4 and 6 were all no, 5 wasn't accounts, and 2 was yes)* "Does it need to do anything behind the scenes, like send emails, take payments, pull information from other websites, or do something on a schedule?" | no | no → remove `api` and `http_tests` (a static site) | No: it's a static site, just pages and pictures. That's the cheapest and simplest thing to run, usually free. Yes: it needs a small server, which can be added later without moving anything. |
| 7b | *(only if there's a server)* "Will it use any outside services that give you a password or key to connect, like a payment, email-sending or weather service? Just tell me which ones. (Claude and Gemini don't count: they need no key here.)" | none | each service → one secret name in UPPER_SNAKE_CASE (`STRIPE_API_KEY`), which `create` wires in by editing the project. None → nothing | Keys are kept in Google's Secret Manager, never in the code. On this computer they go in the project's private `.env` file. Online, the server reads them from Secret Manager when it starts. I never ask for the key itself. |
| 8 | *(only if there's a server, so 7 wasn't asked or was yes)* "When it's online, does it need its own web address like orders.mariasbakery.com, or is an address Google gives you fine?" | Google's address | own → remove `cloud_run`. Google's → remove `gae` | Own address → App Engine, which connects your domain for free. Google's address → Cloud Run, which costs nothing while nobody's using it and can send replies word by word. Connecting your own domain to Cloud Run needs a paid load balancer, about $18 a month. |
| 8b | *(own address, and it streams: an AI assistant that types its reply, live updates, or long tasks)* "One catch: with your own address, [AI replies] appear all at once instead of word by word. Is that okay, or would you rather keep Google's address?" | ask; don't assume | okay → remove `cloud_run`. rather stream → remove `gae` | App Engine sends each reply in one piece. Word-by-word on your own address needs Cloud Run plus the load balancer, which goes against small and cheap. |
| 9 | *(only if there's a server)* "When someone opens it after nobody's used it for a while, is a wait of a few seconds okay? That keeps it cheapest. Or should it always answer instantly, for a bit more?" | a short wait is fine | wait → remove `always_on`. instantly → keep `always_on` | Instantly keeps one copy of the server running all the time. Otherwise it switches off when nobody's using it, costs nothing while off, and the first visit after a quiet spell waits a few seconds while it starts (Cloud Run gets extra power while starting to shorten that wait, for a fraction of a cent each time). See the cost guide below for the price on each host. |
| 10 | "I'll call it **Bakery Orders**. Okay, or would you like another name?" | a two- or three-word name guessed from the brief and answers | `--display-name`; `--name` and `NAMESPACE` are its kebab-case form (`bakery-orders`) | The name shows on the page and in the project's folder and code. |
| 11 | "I'll build it in this folder: `<path>`. Okay?" | the current folder if it's empty, otherwise `<current folder>/<kebab-name>` | `--dest` | — |

#### Examples

Short, everyday cases for each answer. Swap in details from their brief when you can ("like your order list").

- **1. What it does, and who for**
  - "A page where my bakery staff see today's orders and tick them off."
  - "A sign-up form for our book club's monthly meetups."
  - "A site with our restaurant's menu, hours and address."
  - "A tool that reads customer emails and drafts a reply for me to check."
- **2. Opened in a web browser**
  - Yes: a menu site, a staff dashboard, a booking form, a chat page.
  - No: the behind-the-scenes part of a phone app, or something only other software talks to, like a service a shop's till sends sales to.
- **3. Remembers things between visits**
  - Yes: orders and whether they're done, sign-ups from a form, a list of customers, comments people leave.
  - No: a menu or price list you change by editing the site itself, a calculator that works things out on the spot.
- **4. Uploads or keeps files**
  - Yes: customers send photos of a damaged item, staff upload invoices as PDFs, members share a spreadsheet.
  - No: the logo, photos and pictures that are part of the site's design; links to files kept somewhere else, like a shared drive.
- **5. Who uses it**
  - Only your team: a staff rota, an internal stock list, a dashboard for the office.
  - Customers with their own accounts: an online shop where people see their past orders, a members' area, a booking site where people manage their bookings.
  - Anyone: a menu, a landing page, a contact form, an event page.
- **5b. Work email ending**
  - "@mariasbakery.com" if everyone's email ends that way. If people use personal Gmail addresses, team-only access can't tell them apart by the ending; say so, and suggest "anyone" or customer accounts instead.
- **6. Uses AI**
  - Yes: write a summary of today's orders, draft replies to reviews, sort messages into "urgent" and "can wait", answer questions about your opening hours.
  - No: showing and saving information, forms, lists, totals and simple sums.
- **6b. One job, or an assistant**
  - (a) One job when asked: "summarise this", "draft a reply to this email", "sort these messages", "turn these notes into a tidy list".
  - (b) An assistant: a chat helper that answers customers' questions by looking up your products, or one that books an appointment by checking the calendar, asking follow-up questions and confirming.
- **7. Behind the scenes**
  - Yes: emails a receipt after an order, takes card payments, pulls in the weather or exchange rates, sends a reminder every Monday.
  - No: pages people read, with links and pictures. Opening an email app with a "mailto" link counts as no.
- **7b. Services with a key**
  - Yes: Stripe or Square for card payments, SendGrid or Mailgun for email, a weather or exchange-rate service, Twilio for text messages.
  - No: Claude or Gemini (no key needed, the project signs in itself), Google's own database and file storage (same), anything that needs no sign-up.
  - If they name an AI service from another company (like OpenAI), say that Claude and Gemini are built in and need no key, and ask if one of those will do. If they still want it, add its key as a secret.
- **8. Own web address**
  - Own: orders.mariasbakery.com, bookclub.org, a name you'd print on a menu or business card.
  - Google's: an address like bakery-orders-abc123.a.run.app, fine for a team tool or something only shared by link.
- **8b. Word by word, or all at once**
  - Word by word: a chat assistant whose reply appears as it's written, like typing; a progress bar on a long task.
  - All at once: the reply shows up complete after a few seconds' pause, which is fine for summaries, drafts and most forms.
- **9. Instant, or a short wait**
  - A short wait is fine: a staff tool used a few times a day, a sign-up form, anything where a few seconds now and then won't matter.
  - Instantly: a checkout people might give up on, a booking page shared at a busy event, a tool used in front of customers.
- **10. Name**
  - "Bakery Orders", "Book Club Signups", "Menu Site". Two or three plain words; it can change later.
- **11. Folder**
  - "Here is fine", or a place they'll remember, like a "Projects" folder in their home folder.

#### Always, without asking

- Remove `notebooks` (a developer tool). Keep it only if the person turns out to be a developer and asks.
- Remove `http_tests` when `api` is removed; keep it otherwise.
- Customer accounts need a server: if 5 was "accounts", skip 7.
- A static site (no `api`) always goes on App Engine: remove `cloud_run` and `always_on`, and skip questions 8 and 9. It can always have its own web address, and its pages are always instant.
- `NAMESPACE=<kebab-name>`, which names the project's database, bucket and services, so it can share a Google Cloud project with other apps. Never set `PROJECT_ID`: which Google Cloud project it goes in is decided outside stackkit.

#### Cost guide

Monthly estimates for small use, from Google's published prices and free tiers (checked 2026-10-23). Free tiers are per Google Cloud project, so they shrink if the project is shared with other apps. Use these in the confirmation (step 3) and when someone asks what something costs. They're estimates, never quotes.

| Part | Estimate | Why |
|------|----------|-----|
| Static site (App Engine) | $0 | Pages are served without a running server; 1 GB a day of traffic is free |
| Server that sleeps when idle (Cloud Run or App Engine) | $0 | Cloud Run: 2 million requests a month free. App Engine: 28 server-hours a day free |
| Always ready, Cloud Run | about $10 | One idle server at Cloud Run's default size, at the idle rate |
| Always ready, App Engine | $0, or up to about $36 | Free while it's the only App Engine app in its Google Cloud project (24 of the 28 free hours a day); $0.05 an hour beyond that |
| Database | $0 | Free up to 1 GB stored and 50,000 reads and 20,000 writes a day |
| File storage | $0 to a few cents | 5 GB free in the US regions, then a couple of cents per GB a month |
| AI | pay per use | Depends on how much it's used; not estimated. The assistant (6b) costs more per conversation than one-off calls |
| Own web address | the domain name | Buying the name itself (orders.mariasbakery.com) is separate, from a domain seller; App Engine connects it for free |

#### Reading the brief

- **"Just an API" / "the backend for an app someone else builds" / a phone app:** no page (2 is no), so there's a server; skip 7.
- **A chatbot or assistant people talk to in the browser:** page yes, AI (b).
- **A page of information, a portfolio, a menu, a landing page:** usually a static site. Expect 3, 4, 6 and 7 to be no.
- **Internal team tool:** suggest team-only at question 5, but let them choose.
- **Customers sign up and log in with their own accounts:** accounts at 5. stackkit sets up the base; the sign-up and login screens are built afterwards, so say that plainly in the plan.
- **No page and nothing behind the scenes:** there's nothing to build. Stop and go back over the brief with them.
- **Something this stack can't do** (a native phone app, a game, hardware): say so plainly, and offer the closest thing it can do (for example, the backend a phone app would talk to) before going on.

### 3. Confirm

First, check quietly for the extra tools the plan needs, and ask before installing any that are missing, as in step 1:
- `bun` if it keeps the web page
- `firebase` and `java` if it keeps `database` or `storage` (they run the local copy of the database)

Then show a summary of what will be created and the estimated monthly cost once it's online, in plain words. For example:

> Here's what I'll create:
>
> **Bakery Orders**, in `~/projects/bakery-orders`
> - A page your staff open in a web browser
> - Remembers orders between visits
> - Only people with an @mariasbakery.com email can get in
> - No AI
> - Its own web address once it's online
> - Starts in a few seconds after a quiet spell, to keep it cheap
>
> **Estimated cost once it's online: about $0 a month** for a small team. The database and the server sleeping when idle both fit in Google's free allowance. Buying the web address itself is separate.

List every part kept and each "no" that matters (AI, sign-in). If AI is kept, say "AI works with no key to manage". List any secret names ("Keys to add later: Stripe"). Give a cost line for anything that isn't $0, from the cost guide. Then ask with the AskUserQuestion tool (or in plain text if it isn't available), with three choices:

- **Create it** → go to step 4.
- **Change something** → ask what, update the plan, and show the summary again.
- **Cancel** → stop. Nothing has been created; say so.

Keep the exact `--remove` list, `--env` values and secret names ready for `create`. The script works out the parts nobody is asked about (like the local database copy and the cloud tooling folder) and refuses a combination that can't work, saying why.

### 4. Build it

As soon as they choose **Create it**, in that same reply, invoke the `stackkit:create` skill with the Skill tool. It creates the project, tidies its docs, checks it runs and hands it over, all in that one turn. Don't run any of it yourself: `create` carries the permissions that let it work without stopping to ask the person, and they only last for the turn it's invoked in.

## Rules

- **Small, cheap and easy wins.** When an answer is unclear, pick the option with fewer parts and lower cost, and say that's what you picked.
- **No deploys, nothing billable.** stackkit sets up the project; it doesn't put it online. Don't create cloud projects, enable billing, deploy, or change access permissions, even if asked mid-interview; say it's handled outside stackkit. The hosting answers (8, 8b, 9) still matter: they decide what the project is built to run on.
- **No employer or personal information** from anyone but the person in front of you goes into the project.
- **Never take a key.** Don't ask for, accept or write an API key, password or token during the interview, even if offered. Only the names of the secrets go in the plan. If AI is wanted, never suggest creating an AI API key: Claude and Gemini use the service account.
- **One project per run.** If they describe two different apps, make the first and offer the second after.
