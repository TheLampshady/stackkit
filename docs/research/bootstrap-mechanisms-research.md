# Bootstrap Mechanisms — Research

**Written:** 2026-10-19
**Last updated:** 2026-10-19
**Original request:** Research how an agent should turn the stackkit template repo into a new project, so a non-techie can get a working stack by answering questions.
**Charter:** `docs/research/CHARTER.md`
**Provenance:** Sourced claims cite primary sources inline; everything under Hypotheses is unmeasured. This doc stands alone.

## Summary

### Goal

Pick how stackkit turns a copy of the template repo into a new project, run by a non-techie alone inside Claude Code, without git, leaving no unused code behind and no link back to the template afterwards.

### Claims

11 findings, 4 hypotheses

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

## How this applies to your request

Copy-once settles the biggest fork. Every update-capable mechanism ([Copier](#f-copier-update-reqs), [cruft](#f-cookiecutter-cruft), [remote merges](#f-remote-merge), sync Actions) exists to keep a link to the template, and you don't want that link. They also all need git on the non-techie's side, which [may not be there](#f-windows-git-optional). [H1](#h1) records why that choice should hold, and what would show it was wrong.

What's left is plain copy, plus three things a plain copy doesn't give you:

1. **Delivery without git.** The best fit for "the non-techie only has Claude Code" is shipping the template inside the stackkit plugin. Skills can [reach files in the plugin and run bundled scripts](#f-skill-scripts), and plugins can [install from a zip](#f-plugin-archive). The tracked template is about 1.4 MB across 159 files, small enough to bundle. A Drive zip also works, but it adds a download-and-unzip step and a second copy to keep current ([H3](#h3)). A [GitHub zip](#f-source-archive) is the same idea with a stable, pinnable URL, which makes it the better fallback of the two. The risk with bundling is two template copies drifting apart. Keeping the template only inside the plugin repo removes that risk.

2. **Removal, not toggles.** You said not to leave code behind. The prior art splits into [composition](#f-t3-compose), which needs the template split into add-on pieces and breaks "copy it and it runs", and [copy-time exclusion](#f-copier-suffix-exclude), which only drops files. Removing a module from this repo also touches the Makefile, the uv workspace, `.env.sample`, the docs and the agent sync step, so file exclusion alone isn't enough. [H2](#h2) is the bet that a per-module manifest plus a final `make check` makes removal reliable.

3. **Values.** "Light substitution" (allowed by the charter) is really a list of the values the bootstrap rewrites. Today they're scattered, which is [H4](#h4).

The charter rules out a render step the repo depends on. Copier's [suffix precedence](#f-copier-suffix-exclude) would technically allow a runnable repo with `.jinja` twins beside it, but that doubles every templated file and only pays off if you want `copier update`, which you don't. A skill-driven copy fits better.

## Actions

- **A1 — Add `skills/bootstrap/` to the stackkit plugin: a `SKILL.md` that interviews the non-techie, then runs a bundled script to copy `${CLAUDE_PLUGIN_ROOT}/template/` into a new folder, apply module removals, rewrite values, and run the verification gate (A4).** · *building*
  **Because:** [H1](#h1), [H3](#h3), [skills run bundled scripts](#f-skill-scripts), [plugin files reachable from skills](#f-plugin-archive)
- **A2 — Keep the template only in stackkit's `template/` folder (moved in from the original template repo), so the plugin ships exactly one copy and nothing has to be generated or kept in sync.** · *building*
  **Because:** [H3](#h3), [plugin files reachable from skills](#f-plugin-archive)
- **A3 — Add a module manifest to the template repo (e.g. `stackkit.toml`, one table per optional module: `agent_service`, `frontend`, `notebooks`, `http_tests`, Firebase auth vs IAP) listing its paths, Makefile targets, uv workspace members, `.env.sample` keys and doc sections. A1's script removes modules only from this list.** · *building*
  **Because:** [H2](#h2), [Copier's conditional exclude](#f-copier-suffix-exclude)
- **A4 — End every bootstrap with a gate: `make check` on the new copy (and `make run` health check where possible). On failure, report it to the non-techie in plain words and stop. Never hand back a broken project as done.** · *building*
  **Because:** [H2](#h2)
- **A5 — Strip all employer information from the template outright, never as a rewritable default: blank the `VALID_DOMAINS` default in both `app_settings.py` files, switch test fixture emails and `gcp/bin/test_auth.py` to `example.com`, and remove the bundled `tech-discovery` skill (its formats are employer-specific). Then collect the remaining owner values (project name, package descriptions, the absolute paths in the PyCharm section of `AGENTS.md`) into one `[values]` table in the same manifest, which A1 rewrites from.** · *building*
  **Because:** [H4](#h4); the charter's no-employer-information constraint
- **A6 — Publish stackkit with a plugin entry that uses an `archive` source (a pinned zip with `sha256`), next to the GitHub source, so installing it needs no git.** · *proposed*
  **Because:** [H3](#h3), [archive plugin source](#f-plugin-archive), [git optional on Windows](#f-windows-git-optional)

## Decisions (deliberately not doing)

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

## Open questions

- **The toolchain on a non-techie's machine.** The template needs `make`, `uv`, `bun` and `gcloud`, and the charter keeps that toolchain. A native-Windows non-techie probably has none of them, and `make` is not native to Windows at all. Whether the bootstrap installs them, swaps `make` for something cross-platform, or requires WSL is unresolved, and the answer may conflict with the charter's toolchain constraint. This belongs to the charter's "what setup an agent may do unattended" objective.
- **Cloud login and billing for an unassisted non-techie.** `gcloud auth login`, project creation, billing and IAM all need a person in a browser, and the charter requires confirmation before anything billable. How much of this a non-techie can do alone was not researched here.
- **Drive as a distribution channel.** You raised a zip on Google Drive. Reading a Drive file from inside Claude Code without a connector or auth wasn't checked. A GitHub release zip gives the same no-git download with a pinnable URL ([finding](#f-source-archive)).
- **claude.ai-hosted and org-synced plugins.** The plugin docs mention marketplaces hosted on claude.ai and plugins synced from organization settings, which could reach non-techies with even less setup. They also note that claude.ai and Cowork don't install plugins with a top-level `bin/`. Not researched.
- **Archive size limits.** The archive plugin source's size, timeout and extraction limits are on the plugin hosting page, which wasn't read. The template is small (about 1.4 MB), so this is unlikely to bind.
- **Interview questions.** Which questions map to which module removals and values (the charter's second objective) is downstream of A3's manifest, and wasn't researched here.
