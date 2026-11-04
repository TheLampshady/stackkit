# Cost guide

What a stackkit project costs once it's online, part by part. The interview (`bootstrap`), the hand-over (`create`) and the `status` skill all read this; keep the numbers here and nowhere else.

Monthly estimates for small use, from Google's published prices and free tiers (checked 2026-10-23; background work 2026-11-04). Free tiers are per Google Cloud project, so they shrink if the project is shared with other apps. They're estimates, never quotes.

| Part | Estimate | Why |
|------|----------|-----|
| Static site (App Engine) | $0 | Pages are served without a running server; 1 GB a day of traffic is free |
| Server that sleeps when idle (Cloud Run or App Engine) | $0 | Cloud Run: 2 million requests a month free. App Engine: 28 server-hours a day free |
| Always ready, Cloud Run | about $10 | One idle server at Cloud Run's default size, at the idle rate |
| Always ready, App Engine | $0, or up to about $36 | Free while it's the only App Engine app in its Google Cloud project (24 of the 28 free hours a day); $0.05 an hour beyond that |
| Database | $0 | Free up to 1 GB stored and 50,000 reads and 20,000 writes a day |
| File storage | $0 to a few cents | 5 GB free in the US regions, then a couple of cents per GB a month |
| AI | pay per use | Depends on how much it's used; not estimated. The assistant (`agents`) costs more per conversation than one-off calls |
| Background work (Cloud Run jobs) | $0 for small use | Billed only while it runs. 240,000 vCPU-seconds and 450,000 GiB-seconds free a month per billing account (about 66 hours of one CPU); a five-minute run every day uses about 4% of that. Then about $0.000018 a vCPU-second |
| A reaction built by hand (Cloud Functions) | $0 for small use | Runs on Cloud Run, billed per use like a server that sleeps when idle (estimate; check Google's Cloud Run functions pricing) |
| Timer for a scheduled job | $0, or about $0.10 a job | Google's timer: 3 jobs free per billing account, then about $0.10 a job a month (estimate; check Google's Cloud Scheduler pricing) |
| Outside services with a key (texts, payments, email) | their own prices | Billed by that service, not Google: a text costs cents, card payments take a small cut of each sale. Not estimated; say who bills it |
| Own web address | the domain name | Buying the name itself (orders.mariasbakery.com) is separate, from a domain seller; App Engine connects it for free |

Every server has a cap on how many copies run at once (2 by default, `max` in `status.py`'s `scaling`). Busy months cost more only up to that cap; past it, visits slow down instead. Say so when someone worries about a surprise bill.

## Which rows apply

From the plan, or from `parts` in `status.py`'s report:

| Project has | Row |
|---|---|
| `gae` without `api` | Static site |
| `api` without `always_on` | Server that sleeps when idle |
| `api`, `always_on` and `cloud_run` | Always ready, Cloud Run |
| `api`, `always_on` and `gae` | Always ready, App Engine |
| `database` | Database |
| `storage` | File storage |
| `ai` or `agents` | AI |
| `gae` (with or without `api`) | Own web address, if they use one |
| `jobs` | Background work |
| A reaction in the plan | A reaction built by hand |
| A scheduled job in the plan | Timer for a scheduled job |
| A secret name for an outside service | Outside services with a key |

## Adding it up

Give one line per part that isn't $0, then a total for small use ("about $0 a month", "about $10 a month plus AI use"). Name the parts at $0 together in one sentence ("the database and the server sleeping when idle both fit in Google's free allowance"). Never give a quote; say it's an estimate.
