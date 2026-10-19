# Research Charter

Frame for research runs in this repo. Read for context; never cited as a source.

**Mandate** — Stackkit bets that one opinionated, copy-and-paste stack, set up by an agent from a plain-language interview, serves most non-technical asks better than a custom build. Research exists to test that bet and keep the calls it forces evidence-backed: what to ask, what to generate versus leave as-is, and what keeps the result cheap to maintain.

The property worth protecting is the one that already works: **copy the template repo and it runs.** Every recommendation is judged against whether it keeps that true.

## Objectives

The first one is the point; the rest matter only where they change it.

- **The bootstrap mechanism** — how an agent turns the template repo into a new project: plain copy + strip, parameterized copy, feature toggles, or skill-guided hand edits. What other people do, what each costs to keep in sync with the template, and which one keeps "just copy it" working.
- **What the agent asks first** — the smallest set of plain-language questions whose answers change what the bootstrap does, and where a default should be picked instead of asking.
- **What a new project can drop** — which parts of the template are core and which are optional modules (agents, frontend, notebooks, auth modes), so the bootstrap can remove them cleanly.
- **What setup an agent may do unattended** — cloud provisioning, secrets, CI, git hooks: which steps are safe to automate, and which need a human to approve or click.

## Out of scope

Already decided against. Don't research these, and don't recommend them.

- **A heavy template engine** — the template repo stays runnable as-is after a plain copy; nothing that turns it into a Jinja/cookiecutter source tree that only works once rendered. Light substitution of a few values is fair game; a render step the repo depends on is not.
- **Rebuilding a sibling kit** — docs and project agents belong to repokit, issue-to-PR flow to codekit, tickets to tikkit, research to claimkit. Stackkit calls or recommends them, never reimplements them.
- **A hosted product** — no web UI, SaaS, or no-code builder for the non-techie. The interview runs inside a coding agent, driven by a skill.

Other stacks and platforms are **not** ruled out. Research may question the stack; it may not turn stackkit into a catalog of templates without that being decided here first.

## Constraints

- Open source and free only. Paid cloud services may be the deploy target (the stack runs on GCP), but the tooling that sets them up may not require a paid product.
- No employer information anywhere in stackkit or the template — no employer names, domains, emails, repos or employer-specific formats, not even as defaults to be rewritten. Anonymize sensitive and client-identifying material. Project-specific information stays in the project.
- Stackkit ships the way its siblings do: skills as Markdown, config as TOML/JSON/YAML, distributed as a plugin. An answer must hold on Claude Code and Antigravity, or name the one it excludes and why.
- The template stays runnable after a plain copy, and the toolchain stays as is: `uv`, `bun`, `make`, `gcloud`.
- Any cloud action that creates billable resources or grants IAM confirms first, the way the template's provisioning already does. An agent working from a non-techie's brief never spends money or widens access silently.

## Standard of evidence

Practitioner consensus is the floor, upgraded by benchmarks and skeptical reports wherever they exist. Order: official docs and specs for the tools involved > documented practice from people who maintain templates or scaffolders at scale > credentialed practitioner write-ups with working examples > vendor blogs.

A single vendor blog is a lead, not a basis. Template and scaffolder projects describe themselves well and their maintenance costs badly, so look for the issue tracker, the migration story, and the people who left.

Verify load-bearing claims against the primary source, not a summary. Absence of evidence is labeled as an absence claim, never treated as a negative finding.

## Terminology

- **template repo** — the working stack that new projects are copied from (currently the `zgoldstein_dev` repo). A real, runnable project, not a render source.
- **bootstrap** — turning a copy of the template repo into a new project: renaming, dropping modules, setting values, provisioning. Not generating code from nothing.
- **brief** — the non-techie's plain-language description of what they want. Input to the interview, not a spec.
- **non-techie** — the non-technical person whose brief drives a bootstrap. Not the agent, and not the developer who maintains stackkit.
- **namespace** — the `NAMESPACE` value that names a project's cloud resources (Firestore database, `{project_id}-{namespace}` bucket, service name). Settled by the template; don't coin a synonym.
- **deploy unit** — an independently deployable package in the template (the service, the agents). Not a module you can drop.

<!-- rot-prone: additive; a rename is a conflict, not an edit -->
