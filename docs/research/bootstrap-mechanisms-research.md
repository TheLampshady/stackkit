# Bootstrap Mechanisms — Research

**Written:** 2026-10-19
**Last updated:** 2026-10-23
**Original request:** Research how an agent should turn the stackkit template repo into a new project, so a non-techie can get a working stack by answering questions.
**Charter:** `docs/research/CHARTER.md`
**Provenance:** Sourced claims cite primary sources inline; everything under Hypotheses is unmeasured. This doc stands alone.

## Summary

### Goal

Pick how stackkit turns a copy of the template repo into a new project, run by a non-techie alone inside Claude Code, without git, leaving no unused code behind and no link back to the template afterwards.

### Claims

20 findings, 7 hypotheses

**Template copies and update tooling** — The common ways to start from a template, and what each one costs if you later want to pull template fixes into projects already made from it.

*Findings (sourced):*
- [A GitHub template repo copies files once, with no update path](#f-template-repo-no-link)
- [Copier can update projects, but needs an answers file and git tags on both sides](#f-copier-update-reqs)
- [Copier renders only marked files and can exclude paths conditionally](#f-copier-suffix-exclude)
- [Cookiecutter needs the template in a subfolder and can't update; cruft adds updating on top](#f-cookiecutter-cruft)
- [Merging the template in as a git remote works, but is fragile across repeated syncs](#f-remote-merge)
- [Teams that push template updates still hit conflicts when projects diverge](#f-update-bot-practice)

*Hypotheses (unsourced):*
- [**H1**](#h1) — If projects are expected to diverge, a one-time copy costs less over a template's life than any update mechanism.

**Module removal** — How a bootstrap drops the parts of the stack a brief doesn't need, so nothing unused is left behind.

*Findings (sourced):*
- [Scaffolders like create-t3-app choose modules at creation time and say nothing about changing them later](#f-t3-compose)

*Hypotheses (unsourced):*
- [**H2**](#h2) — A module can be removed safely only when one manifest lists everything it touches, and the copy passes its checks afterwards.

**Getting the template to a non-techie** — How the template files reach someone who may have no git and no GitHub account.

*Findings (sourced):*
- [Git is optional for Claude Code on native Windows](#f-windows-git-optional)
- [Skills can carry and run their own scripts](#f-skill-scripts)
- [Plugins can install from a zip over HTTPS, and skills can reference files inside the plugin](#f-plugin-archive)
- [A GitHub repo can be downloaded as a zip without git, but branch links can change](#f-source-archive)

*Hypotheses (unsourced):*
- [**H3**](#h3) — Every prerequisite beyond Claude Code itself is a place an unassisted non-techie stops.

**Permissions during a skill run** — What makes Claude Code stop and ask the person "allow this?", which a non-techie can't judge.

*Findings (sourced):*
- [A skill's pre-approved tools last only for the turn it's invoked in](#f-allowed-tools-turn)
- [Every part of a chained command must be approved, and reads outside the start folder ask](#f-permission-scope)

*Hypotheses (unsourced):*
- [**H5**](#h5) — Splitting the skill so the build runs in one invoked turn removes every command prompt but the skill start itself.

**Hosting and cost for small projects** — Which Google hosting keeps a non-techie's project cheap, and what each one can't do.

*Findings (sourced):*
- [Cloud Run's built-in custom domains aren't production-ready; a load balancer is the supported route](#f-cloud-run-domains)
- [App Engine doesn't stream responses](#f-gae-no-streaming)
- [Firestore's free quota covers the first database in a project, whatever it's named](#f-firestore-free-quota)
- [Google's free tier covers a small sleeping server on either host, a database and 5 GB of files](#f-free-tier)
- [Keeping one Cloud Run instance warm costs about $10 a month](#f-cloud-run-min-instance)
- [Keeping one App Engine instance warm is free only while it's the project's only App Engine app](#f-gae-instance-hours)
- [Cloud Run's startup CPU boost shortens cold starts and is billed only while an instance starts](#f-cpu-boost)

*Hypotheses (unsourced):*
- [**H6**](#h6) — Asking what people do with the project, not which technology it needs, gets answers a non-techie can give reliably.

**Removal markers in code** — Keeping the comment markers that delimit a module intact when tools rewrite the code around them.

*Findings (sourced):* none. This group is about how the template's own tooling treats its files.

*Hypotheses (unsourced):*
- [**H7**](#h7) — Markers around imports don't survive an import sorter, so only imports of deleted files may carry them.

**Owner identity in the template** — The template still carries its author's names, emails and paths, which a plain copy would hand to every new project.

*Findings (sourced):* none. This group is about the template's own contents, and no outside source covers it.

*Hypotheses (unsourced):*
- [**H4**](#h4) — Every value that names the template's owner must live in one place the bootstrap rewrites, or copies leak it.

## Key findings

- <a id="f-template-repo-no-link"></a>**A GitHub template repo copies files once, with no update path** ([GitHub Docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)) — The new repo gets the template's files and structure but "starts with a single commit". Copied branches "have unrelated histories", so nothing can be merged or PR'd between template and copy. The page describes no ongoing link. Creating from a template also needs a GitHub account and is a GitHub-side operation.

- <a id="f-copier-update-reqs"></a>**Copier can update projects, but needs an answers file and git tags on both sides** ([Copier: Updating](https://copier.readthedocs.io/en/stable/updating/)) — `copier update` regenerates the project from the current template, diffs it against the real project, and reapplies the project's own changes. Conflicts are written inline as conflict markers by default, or as `.rej` files. The best case requires three things: a valid `.copier-answers.yml` (which must "**Never**" be hand-edited), a git-versioned template with PEP 440 tags, and a git-versioned destination. The docs advise keeping templates "as pure and simple as possible" to avoid broken updates.

- <a id="f-copier-suffix-exclude"></a>**Copier renders only marked files and can exclude paths conditionally** ([Copier: Configuring](https://copier.readthedocs.io/en/stable/configuring/)) — By default only files ending in `.jinja` are rendered. A suffixed file takes precedence over an unsuffixed file of the same name ("the one without suffix will be ignored"), so a runnable file and its template twin can sit side by side. `_exclude` patterns "can be templated with Jinja", which lets a question's answer drop whole paths at copy time. `_tasks` post-copy commands run only with `--trust`. Copier's own comparison table says it does not require a template subfolder ([Copier: Comparisons](https://copier.readthedocs.io/en/latest/comparisons/)). That table is the project describing itself.

- <a id="f-cookiecutter-cruft"></a>**Cookiecutter needs the template in a subfolder and can't update; cruft adds updating on top** ([Copier: Comparisons](https://copier.readthedocs.io/en/latest/comparisons/), [cruft on PyPI](https://pypi.org/project/cruft/)) — Per Copier's comparison table, Cookiecutter requires the template in a subfolder and has no template updates. That is a competitor's description, not verified here against Cookiecutter's own docs. Cruft links an existing Cookiecutter project to its template and adds `cruft check` (exits 1 when behind, usable in CI), `cruft diff` and `cruft update`.

- <a id="f-remote-merge"></a>**Merging the template in as a git remote works, but is fragile across repeated syncs** ([blue-build sync guide](https://blue-build.org/how-to/sync/), [Ian Lewis, 2025](https://www.ianlewis.org/til/2025/04/10/syncing-with-github-repository-templates), [Paranext wiki](https://github.com/paranext/paranext-extension-template/wiki/Merging-Template-Changes-into-Your-Extension)) — Add the template as a remote and merge with `--allow-unrelated-histories`. The Paranext wiki warns that the merge commits are what git compares against on the next update, so they must not be squashed or rewritten. Ian Lewis's method squashes, and his post covers only a single sync. The packaged version of this approach, [actions-template-sync](https://github.com/AndreasAugustin/actions-template-sync), defaults to `--allow-unrelated-histories --squash --strategy=recursive -X theirs`, which favours the template side in conflicting hunks. Its README also says that changes under `.github/workflows` need a PAT with `workflow` scope. A forum report that sync Actions "fail if there's a merge conflict" is anecdotal ([element14 forum](https://community.element14.com/products/devtools/software/f/forum/54714/github-template-repository-get-updates-from-origin)).

- <a id="f-update-bot-practice"></a>**Teams that push template updates still hit conflicts when projects diverge** ([PyCon DE & PyData 2026 talk abstract](https://pretalx.com/pyconde-pydata-2026/talk/AWFFUS/)) — One team runs a monthly bot that executes `copier update` across its organization and opens PRs. "Merge conflicts are minimized by encouraging teams not to diverge too far from the template", and mergiraf helps, "but maintainers may still need to step in." The abstract also claims projects "can deviate from the template whenever needed, without breaking the update mechanism." *Abstract only; the talk body was not reviewed here.*

- <a id="f-t3-compose"></a>**Scaffolders like create-t3-app choose modules at creation time and say nothing about changing them later** ([create-t3-app: Installation](https://create.t3.gg/en/installation)) — Packages are picked through interactive prompts or `--CI` flags (`--trpc`, `--prisma`, `--nextAuth false`, …). Unselected packages are never added: "You don't need to explicitly opt-out of the packages you don't want." The flags are marked experimental and "may change in the future without following semver". The installation page doesn't cover updating or changing modules in an existing project. The pattern composes a project by adding pieces, which is the reverse of removing them from a full copy.

- <a id="f-windows-git-optional"></a>**Git is optional for Claude Code on native Windows** ([Claude Code: Advanced setup](https://code.claude.com/docs/en/setup)) — Native Windows "Requires: None; Git for Windows is optional". Without it, Claude Code runs shell commands through PowerShell instead of Bash. The listed system requirements don't include git on any platform. So a non-techie with a working Claude Code may well have no git.

- <a id="f-skill-scripts"></a>**Skills can carry and run their own scripts** ([Claude Code: Skills](https://code.claude.com/docs/en/skills)) — A skill directory can hold scripts and reference files alongside `SKILL.md`. Reference files load only when needed, and scripts are "executed, not loaded". `${CLAUDE_SKILL_DIR}` resolves to the skill's directory, and pairing it with `allowed-tools` "lets a skill run a bundled script without a permission prompt." The docs recommend keeping `SKILL.md` under 500 lines.

- <a id="f-plugin-archive"></a>**Plugins can install from a zip over HTTPS, and skills can reference files inside the plugin** ([Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference), [Plugin manifest reference](https://code.claude.com/docs/en/plugins-reference)) — Plugin sources include `github`, git `url`, `git-subdir`, `npm`, `archive` (a zip over HTTPS with an optional `sha256` pin, Claude Code v2.1.224+), and `command`. `${CLAUDE_PLUGIN_ROOT}` is substituted inside skill Markdown and points at the installed plugin, so a skill can reach any file shipped in the plugin. Component paths must stay inside the plugin root. The docs say not to write state under `${CLAUDE_PLUGIN_ROOT}` because it changes on update. Archive size limits live on a hosting page not read here. The 256 MiB / 20,000-entry cap that was read applies to `command` sources in copy mode.

- <a id="f-allowed-tools-turn"></a>**A skill's pre-approved tools last only for the turn it's invoked in** ([Claude Code: Skills](https://code.claude.com/docs/en/skills)) — `allowed-tools` "grants permission for the listed tools during the turn that invokes the skill… The grant clears when you send your next message", and "invoking the skill again re-applies it for that turn." The page doesn't distinguish a typed `/skill` from Claude invoking it. If an organization sets `allowManagedPermissionRulesOnly`, the field is ignored for project and personal skills (v2.1.282+).

- <a id="f-permission-scope"></a>**Every part of a chained command must be approved, and reads outside the start folder ask** ([Claude Code: Permissions](https://code.claude.com/docs/en/permissions)) — A rule like `Bash(safe-cmd *)` "won't give it permission to run the command `safe-cmd && other-cmd`"; "A rule must match each subcommand independently." File reads need no approval only "within the working directory and additional directories". A built-in set of read-only commands (`ls`, `cat`, `which`, `grep`…) runs without a prompt, and a `*` placed before a command's subcommand draws a startup warning.

- <a id="f-cloud-run-domains"></a>**Cloud Run's built-in custom domains aren't production-ready; a load balancer is the supported route** ([Cloud Run: Mapping custom domains](https://docs.cloud.google.com/run/docs/mapping-custom-domains)) — Domain mapping is in preview, limited to ten regions, and "not recommended for production services". The recommended option is a global external Application Load Balancer; the third is Firebase Hosting in front of the service. The load balancer's monthly price wasn't read here; about $18 a month for its forwarding rule is from memory, not verified.

- <a id="f-gae-no-streaming"></a>**App Engine doesn't stream responses** ([App Engine: How requests are handled](https://docs.cloud.google.com/appengine/docs/standard/how-requests-are-handled?tab=python)) — "App Engine doesn't support streaming responses where data is sent in incremental chunks"; "All data from your code is collected… and sent as a single HTTP response." The page doesn't mention server-sent events or WebSockets by name. It maps custom domains itself, so it's the cheap route to a project's own address.

- <a id="f-firestore-free-quota"></a>**Firestore's free quota covers the first database in a project, whatever it's named** ([Firestore pricing](https://firebase.google.com/docs/firestore/pricing)) — "The first database you create (regardless of its ID) qualifies for the free quota." Delete it and the next one created becomes eligible. So the template's named `NAMESPACE` database is free at small use, as long as it's the project's first.

- <a id="f-free-tier"></a>**Google's free tier covers a small sleeping server on either host, a database and 5 GB of files** ([Google Cloud: Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)) — App Engine standard: "28 hours per day of F1 instances" and "1 GB of outbound data transfer per day." Cloud Run, request-based billing: "2 million requests per month" and "360,000 GB-seconds of memory, 180,000 vCPU-seconds of compute time." Cloud Storage: "5 GB-months of regional storage (US regions only)", only in us-east1, us-west1 and us-central1. Firestore: "1 GiB of storage per project" and "50,000 reads, 20,000 writes, and 20,000 deletes per day per project." The page doesn't list Firebase Auth or IAP limits.

- <a id="f-cloud-run-min-instance"></a>**Keeping one Cloud Run instance warm costs about $10 a month** ([Cloud Run pricing](https://cloud.google.com/run/pricing)) — Idle time on an instance kept by minimum instances is billed at $0.0000025 per vCPU-second and $0.0000025 per GiB-second (Tier 1); idle instances that aren't minimum instances aren't charged. At Cloud Run's default size of 1 vCPU and 512 MiB over a 30-day month that's about $6.48 + $3.24. *The rates come from a search engine's capture of the official page, which renders with JavaScript and couldn't be read directly; the default size is from memory.*

- <a id="f-gae-instance-hours"></a>**Keeping one App Engine instance warm is free only while it's the project's only App Engine app** ([App Engine pricing](https://cloud.google.com/appengine/pricing), [Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)) — F1 instances cost $0.05 per instance-hour in us-central1, after 28 free instance-hours a day per project. One instance kept by `min_instances: 1` uses 24 of those hours; other App Engine apps in the same project share the rest, and beyond them one instance costs about $36 a month. *The F1 rate comes from a search engine's capture of the pricing page, not read directly.*

- <a id="f-cpu-boost"></a>**Cloud Run's startup CPU boost shortens cold starts and is billed only while an instance starts** ([Cloud Run: Configure CPU limits](https://docs.cloud.google.com/run/docs/configuring/services/cpu)) — It "provides additional CPU during instance startup time and for 10 seconds after the instance has started": 2 CPU for a limit of 1 or less. "You are charged for the allocated boosted CPU for the duration of the container startup time." Enabled with `--cpu-boost` on `gcloud run deploy`. The page doesn't say whether it's on by default.

- <a id="f-source-archive"></a>**A GitHub repo can be downloaded as a zip without git, but branch links can change** ([GitHub Docs: Source code archives](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives)) — "Download ZIP", release and tag archives work without git, and "Snapshots don't contain the entire repository history." Branch archive URLs are fixed, but "future downloads of an archive may have different contents", so a stable result needs a commit ID in the URL. The page doesn't cover private repositories.

## Hypotheses

<a id="h1"></a>**H1 — If projects are expected to diverge from their template, a one-time copy costs less over the template's life than any update mechanism, because update tools add files, tags and conflicts that only pay off when projects stay close to the template.** · *open* · added 2026-10-19
- **Builds on:** [Copier update requirements](#f-copier-update-reqs), [remote-merge fragility](#f-remote-merge)
- **Cuts against:** [the PyCon DE team's claim](#f-update-bot-practice) that projects can deviate "without breaking the update mechanism". That is one team's practice, with maintainers on hand to resolve conflicts, but it is the strongest evidence that updates stay workable under divergence.
- **Unsourced because:** Searched for comparisons of template drift costs between copy-once and update-capable tools (Copier vs Cookiecutter vs GitHub templates). Found tool docs and one practice report, but no measurement of maintenance cost either way.
- **Check:** Bootstrap three real projects from briefs. Six months later, list every template commit made since and mark which ones each project would have wanted. If most projects would have wanted most fixes, and porting them by hand took more than an hour per project, the position fails.

<a id="h2"></a>**H2 — A module can be removed from a full copy safely only when a single manifest lists everything the module touches (files, build targets, workspace members, config keys, doc sections), and the copy is proven to still build and test afterwards. An agent working from prose or from its own search leaves dangling references.** · *open* · added 2026-10-19
- **Builds on:** [Copier's conditional `_exclude`](#f-copier-suffix-exclude), the closest prior art: path-level removal driven by an answer. It covers files only, not references from other files.
- **Cuts against:** [create-t3-app's add-only composition](#f-t3-compose), which avoids removal entirely by never adding unchosen modules.
- **Unsourced because:** Searched for scaffolders that remove modules from a complete working project instead of composing one. Found only composition (create-t3-app) and copy-time exclusion (Copier). Nothing on removal from a runnable source.
- **Check:** On fresh copies of the template, remove each optional module twice: once by following the manifest, once by asking an agent to "remove X" with no manifest. Run `make check` and `make run` on each result and count failures and leftover references (`grep` for the module's name). The position holds if the manifest runs pass and the no-manifest runs don't.

<a id="h3"></a>**H3 — For a non-techie working alone, every prerequisite beyond Claude Code itself (git, a GitHub account, a download-and-unzip step) is a point where they stop. A template delivered inside the tool they already have finishes more often than one fetched from somewhere else.** · *open* · added 2026-10-19
- **Builds on:** [git is optional on Windows](#f-windows-git-optional), [plugins install from a zip archive](#f-plugin-archive)
- **Unsourced because:** Searched for drop-off data on developer-tool onboarding for non-technical users and agent-driven setup by non-developers. Found none that measures per-prerequisite abandonment.
- **Check:** Have two or three non-techies bootstrap from a brief on machines without git: once with the template bundled in the stackkit plugin, once from a Drive or GitHub zip they download themselves. Record where each person stops or asks for help.

<a id="h4"></a>**H4 — Every value in the template that names its owner (personal names, emails, absolute local paths, the project name) must live in one place the bootstrap rewrites. Values scattered across code, tests and docs survive a copy and leak the owner's identity into every new project.** · *open* · added 2026-10-19
- **Unsourced because:** This is about the template's contents. A grep of the template repo finds such values in settings defaults, tests, package descriptions, the CLAUDE.md IDE section and a bundled skill's README. No external source applies.
- **Check:** After a bootstrap, grep the new project for every owner identifier in the template's identity list. Any hit fails the position, or the list.

<a id="h5"></a>**H5 — A skill that interviews over many turns can still build without command prompts if the build is a second skill, invoked by Claude in the turn the plan is confirmed, with every command inside one or two bundled scripts. What's left is the prompt to start that skill.** · *validated in-project 2026-10-20* · added 2026-10-20
- **Builds on:** [grants last one turn](#f-allowed-tools-turn), [each chained part must match](#f-permission-scope)
- **Unsourced because:** The docs cover the grant's lifetime, but not whether a Claude-invoked skill's grant behaves like a typed one, or that invoking a skill in default mode prompts. Searched the skills and permissions pages for both; neither says.
- **Check:** Ran `claude -p` in default mode with the plugin loaded, first with nothing pre-approved, then with only `Skill(stackkit:create)` approved → the first run was blocked at the skill call itself. The second built, tidied and checked a project with zero denials, once the questions were inlined (reading the plugin's own reference file asked) and `NotebookEdit` was added. A full multi-turn interview in a real terminal hasn't been run.

<a id="h6"></a>**H6 — A non-techie answers questions about what people do with a project ("does it remember things between visits?", "who will use it?", "does it need its own web address?") reliably, and gets the technology choices that follow (database, sign-in method, static site or server, App Engine or Cloud Run) right more often than when asked about the technology.** · *open* · added 2026-10-22
- **Builds on:** [App Engine's free domains and no streaming](#f-gae-no-streaming), [Cloud Run's domain options](#f-cloud-run-domains), which turn "own web address?" into a hosting choice with one real conflict to explain.
- **Unsourced because:** Searched for studies of non-technical users configuring software through plain-language questionnaires or wizards. Found product onboarding guides, but nothing measuring answer accuracy against the technology a project actually needed.
- **Check:** Give three non-techies a written brief each, run the interview, and compare the modules it picks against what a developer picks from the same brief. Count mismatches per question.

<a id="h7"></a>**H7 — Comment markers around imports don't survive an import sorter, because sorters move comments together with the import below them and merge imports from the same module. Markers hold only around imports of files the module deletes, written in the sorter's own order; imports that just go unused are left for the project's lint fix to remove.** · *validated in-project 2026-10-22* · added 2026-10-22
- **Unsourced because:** This is about how ruff treats this template's files. No outside source covers marker comments specifically.
- **Check:** Ran `ruff check --fix` over the marked template → it merged two marked imports from one module into a single line, and moved an import with its markers so a `begin`/`end` pair interleaved with another module's. After restructuring, the template is ruff-clean as it stands (`make lint`), and the bootstrap now rejects markers that don't nest.

## How this applies to your request

Copy-once settles the biggest fork. Every update-capable mechanism ([Copier](#f-copier-update-reqs), [cruft](#f-cookiecutter-cruft), [remote merges](#f-remote-merge), sync Actions) exists to keep a link to the template, and you don't want that link. They also all need git on the non-techie's side, which [may not be there](#f-windows-git-optional). [H1](#h1) records why that choice should hold, and what would show it was wrong.

What's left is plain copy, plus three things a plain copy doesn't give you:

1. **Delivery without git.** The best fit for "the non-techie only has Claude Code" is shipping the template inside the stackkit plugin. Skills can [reach files in the plugin and run bundled scripts](#f-skill-scripts), and plugins can [install from a zip](#f-plugin-archive). The tracked template is about 1.4 MB across 159 files, small enough to bundle. A Drive zip also works, but it adds a download-and-unzip step and a second copy to keep current ([H3](#h3)). A [GitHub zip](#f-source-archive) is the same idea with a stable, pinnable URL, which makes it the better fallback of the two. The risk with bundling is two template copies drifting apart. Keeping the template only inside the plugin repo removes that risk.

2. **Removal, not toggles.** You said not to leave code behind. The prior art splits into [composition](#f-t3-compose), which needs the template split into add-on pieces and breaks "copy it and it runs", and [copy-time exclusion](#f-copier-suffix-exclude), which only drops files. Removing a module from this repo also touches the Makefile, the uv workspace, `.env.sample`, the docs and the agent sync step, so file exclusion alone isn't enough. [H2](#h2) is the bet that a per-module manifest plus a final `make check` makes removal reliable.

3. **Values.** "Light substitution" (allowed by the charter) is really a list of the values the bootstrap rewrites. Today they're scattered, which is [H4](#h4).

The charter rules out a render step the repo depends on. Copier's [suffix precedence](#f-copier-suffix-exclude) would technically allow a runnable repo with `.jinja` twins beside it, but that doubles every templated file and only pays off if you want `copier update`, which you don't. A skill-driven copy fits better.

## Actions

A1–A5 are built (bootstrap and create skills, the bundled template, the module manifest, the `make check` gate, and the employer and owner cleanup) and have drained out of this list.

- **A6 — Publish stackkit with a plugin entry that uses an `archive` source (a pinned zip with `sha256`), next to the GitHub source, so installing it needs no git.** · *proposed*
  **Because:** [H3](#h3), [archive plugin source](#f-plugin-archive), [git optional on Windows](#f-windows-git-optional)
- **A7 — Run the interview with real non-techies in a real terminal, over many turns, and compare its module picks with a developer's.** · *proposed*
  **Because:** [H5](#h5) (only tested headless, in one turn), [H6](#h6)

## Decisions (deliberately not doing)

- **Managing deploys** (decided 2026-10-22) — stackkit builds the project; it doesn't put it online. Team-only access (IAP) is turned on by hand, or the app sits in a shared Google Cloud project next to other apps, kept apart by `NAMESPACE`. The person who briefed it doesn't need to know about deploys. The hosting question still shapes the build ([App Engine](#f-gae-no-streaming) vs [Cloud Run](#f-cloud-run-domains)).
- **Copier / cruft / `copier update`** — you chose copy-once; their value is updates, and they add an answers file, tags and git on the non-techie's side ([findings](#f-copier-update-reqs)). A Copier template whose files only work once rendered is also barred by the charter.
- **Cookiecutter** — needs the template in a subfolder ([finding](#f-cookiecutter-cruft)), which turns the repo into a render source. Barred by the charter.
- **Template-as-remote merges and sync Actions** — exist only to pull updates; copy-once makes them moot, and they need git ([finding](#f-remote-merge)).
- **Feature toggles that leave unused code in place** — you said don't leave code in.
- **GitHub "Use this template" as the main path** — needs a GitHub account and gives no update path anyway ([finding](#f-template-repo-no-link)). Developers can still use it by hand.

## Sources

| Source | Type | Why it matters |
|--------|------|----------------|
| [GitHub Docs: Creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) | Official docs | What a template repo copies, and that the copy has no link back |
| [GitHub Docs: Downloading source code archives](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives) | Official docs | Zip downloads without git; branch URLs can move |
| [Copier: Updating a project](https://copier.readthedocs.io/en/stable/updating/) | Official docs | Update mechanism and its requirements |
| [Copier: Configuring a template](https://copier.readthedocs.io/en/stable/configuring/) | Official docs | Suffix rendering, conditional `_exclude`, `_tasks` |
| [Copier: Comparisons](https://copier.readthedocs.io/en/latest/comparisons/) | Official docs (self-description) | Copier vs Cookiecutter vs Yeoman on updates and subfolders |
| [cruft (PyPI)](https://pypi.org/project/cruft/) | Project page | Update/check/diff layer for Cookiecutter |
| [blue-build: Sync with template](https://blue-build.org/how-to/sync/) | Project docs | Remote-merge approach in practice |
| [Ian Lewis: Syncing with GitHub repository templates (2025)](https://www.ianlewis.org/til/2025/04/10/syncing-with-github-repository-templates) | Practitioner blog | Squash-merge variant; single sync only |
| [Paranext wiki: Merging template changes](https://github.com/paranext/paranext-extension-template/wiki/Merging-Template-Changes-into-Your-Extension) | Project docs | Why merge commits must be kept for later syncs |
| [AndreasAugustin/actions-template-sync](https://github.com/AndreasAugustin/actions-template-sync) | Open-source tool | Default merge flags and limits of automated syncing |
| [element14 forum thread](https://community.element14.com/products/devtools/software/f/forum/54714/github-template-repository-get-updates-from-origin) | Forum (anecdotal) | Sync Actions failing on conflicts |
| [PyCon DE & PyData 2026: Kickstart Coding at Scale](https://pretalx.com/pyconde-pydata-2026/talk/AWFFUS/) | Conference talk (abstract) | Update-bot practice and its conflict cost |
| [create-t3-app: Installation](https://create.t3.gg/en/installation) | Official docs | Composition-style module selection |
| [Claude Code: Advanced setup](https://code.claude.com/docs/en/setup) | Official docs | Git optional on Windows; system requirements |
| [Claude Code: Skills](https://code.claude.com/docs/en/skills) | Official docs | Bundled scripts and supporting files |
| [Claude Code: Plugin manifest reference](https://code.claude.com/docs/en/plugins-reference) | Official docs | `${CLAUDE_PLUGIN_ROOT}`, containment, layout |
| [Claude Code: Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference) | Official docs | Plugin source types including `archive` |
| [Claude Code: Permissions](https://code.claude.com/docs/en/permissions) | Official docs | What prompts: chained commands, reads outside the start folder |
| [Cloud Run: Mapping custom domains](https://docs.cloud.google.com/run/docs/mapping-custom-domains) | Official docs | Domain mapping is preview; load balancer recommended |
| [App Engine: How requests are handled](https://docs.cloud.google.com/appengine/docs/standard/how-requests-are-handled?tab=python) | Official docs | No streaming responses |
| [Firestore pricing](https://firebase.google.com/docs/firestore/pricing) | Official docs | Free quota for the first database, any name |
| [Google Cloud: Free features](https://docs.cloud.google.com/free/docs/free-cloud-features) | Official docs | Free-tier limits for App Engine, Cloud Run, Cloud Storage, Firestore |
| [Cloud Run pricing](https://cloud.google.com/run/pricing) | Official docs (via search capture) | Idle rate for minimum instances |
| [Cloud Run: Configure CPU limits](https://docs.cloud.google.com/run/docs/configuring/services/cpu) | Official docs | Startup CPU boost and its billing |
| [App Engine pricing](https://cloud.google.com/appengine/pricing) | Official docs (via search capture) | F1 instance-hour rate |

## Open questions

- **The toolchain on a non-techie's machine.** The template needs `make`, `uv`, `bun` and `gcloud`, and the charter keeps that toolchain. A native-Windows non-techie probably has none of them, and `make` is not native to Windows at all. Whether the bootstrap installs them, swaps `make` for something cross-platform, or requires WSL is unresolved, and the answer may conflict with the charter's toolchain constraint. This belongs to the charter's "what setup an agent may do unattended" objective.
- **Drive as a distribution channel.** You raised a zip on Google Drive. Reading a Drive file from inside Claude Code without a connector or auth wasn't checked. A GitHub release zip gives the same no-git download with a pinnable URL ([finding](#f-source-archive)).
- **claude.ai-hosted and org-synced plugins.** The plugin docs mention marketplaces hosted on claude.ai and plugins synced from organization settings, which could reach non-techies with even less setup. They also note that claude.ai and Cowork don't install plugins with a top-level `bin/`. Not researched.
- **Archive size limits.** The archive plugin source's size, timeout and extraction limits are on the plugin hosting page, which wasn't read. The template is small (about 1.4 MB), so this is unlikely to bind.
- **The local database copy.** A project that keeps the database or file storage needs the Firebase emulator running beside `make run`, which needs Java and the Firebase CLI. The interview checks for them and the handover says so, but a non-techie running two terminal windows is untested.
