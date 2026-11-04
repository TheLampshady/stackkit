"""
Create a new project from the stackkit template.

Copies the template into a new folder, removes the modules the project does
not need, swaps in the project's name, writes its ``.env``, copies in any files
carried over from an existing project, and reports any mention of a removed
module that is still in the copy.

With ``--convert``, the destination is an existing project to turn into a
stackkit one in place: everything but its ``.git`` first moves to a sibling
``<dest>-before-stackkit`` folder, so its history is kept and its old files are
still there to read, and ``--copy`` sources inside it are read from there.

With ``--add``, the destination is an existing stackkit project to add modules
to. The template is rendered twice in a scratch folder, with the modules the
project has and with the added ones, and the difference is applied: new files
are copied in, shared files the project hasn't changed are updated, changed
ones are merged three ways with ``git merge-file``, and anything that can't be
merged cleanly is reported, untouched, under ``conflicts``. ``--name`` and
``--display-name`` are read from the project unless given. Standard library only, so it
runs anywhere ``uv run --no-project`` can find a Python.

Usage::

    bootstrap.py --dest ~/projects/bakery-orders --name bakery-orders \\
        --display-name "Bakery Orders" --remove agents,notebooks \\
        --env PROJECT_ID=bakery-orders-prod --env NAMESPACE=orders \\
        --copy ~/old-site/images=frontend/public/images

    bootstrap.py --dest ~/projects/bakery-orders --add database,ai

Prints a JSON summary on stdout. Exits non-zero, having written nothing, if
an argument is invalid or the destination is not empty (without
``--convert``).
"""

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import status

TEMPLATE = Path(__file__).resolve().parents[3] / "template"
MANIFEST = "stackkit.toml"
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}[a-z0-9]$")
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".idea",
    "dist",
    "static",
}
SKIP_FILES = {".env"}
# Left out of files carried over from an existing project: installs, caches,
# history and anything that could hold a secret value.
CARRY_SKIP_DIRS = SKIP_DIRS - {"dist", "static"} | {".mypy_cache", ".next"}
CARRY_SKIP_RE = re.compile(r"^\.env(\..*)?$")
OLD_SUFFIX = "-before-stackkit"
MARKER_RE = re.compile(r"stackkit:(begin|end) ([a-z_,]+)")


class BootstrapError(Exception):
    """A problem the person running the bootstrap has to fix."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Read the command line.

    :param argv: Arguments after the script name
    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--name", help="required unless --add")
    parser.add_argument("--display-name", help="required unless --add")
    parser.add_argument("--remove", default="", help="comma-separated modules")
    parser.add_argument("--env", action="append", default=[], help="KEY=VALUE")
    parser.add_argument(
        "--copy",
        action="append",
        default=[],
        help="SRC=REL: copy a file or folder from an existing project to REL",
    )
    parser.add_argument(
        "--convert",
        action="store_true",
        help="turn the existing project at --dest into a stackkit one in place",
    )
    parser.add_argument(
        "--add",
        default="",
        help="comma-separated modules to add to the existing project at --dest",
    )
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    args = parser.parse_args(argv)
    if not args.add and not (args.name and args.display_name):
        parser.error("--name and --display-name are required unless --add")
    return args


def load_manifest(template: Path) -> dict:
    """Read the template's module manifest.

    :param template: Template root
    :return: The parsed manifest
    :raises BootstrapError: If the manifest is missing
    """
    path = template / MANIFEST
    if not path.is_file():
        raise BootstrapError(f"No {MANIFEST} in {template}")
    return tomllib.loads(path.read_text())


def parse_env(pairs: list[str], allowed: list[str]) -> dict[str, str]:
    """Turn ``KEY=VALUE`` arguments into a dict.

    :param pairs: Raw ``--env`` values
    :param allowed: Keys the manifest lets the bootstrap set
    :return: The values by key
    :raises BootstrapError: On a malformed pair or a key not in the manifest
    """
    env = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or key not in allowed:
            raise BootstrapError(
                f"--env {pair!r}: expected one of {allowed} as KEY=VALUE"
            )
        env[key] = value
    return env


def resolve_removals(manifest: dict, requested: list[str]) -> list[str]:
    """Work out the full set of modules to remove and check it's buildable.

    An ``implicit`` module is removed on its own once no kept module
    ``requires`` it. Every kept module's ``requires`` must be kept, and each
    ``keep_one_of`` group must keep at least one module.

    :param manifest: The template manifest
    :param requested: Modules asked to be removed
    :return: Modules to remove, in manifest order
    :raises BootstrapError: On an unknown module or an impossible combination
    """
    modules = manifest["modules"]
    unknown = sorted(set(requested) - set(modules))
    if unknown:
        user = sorted(m for m in modules if not modules[m].get("implicit"))
        raise BootstrapError(f"Unknown modules {unknown}; choose from {user}")

    removed = set(requested)
    changed = True
    while changed:
        kept = set(modules) - removed
        needed = {r for m in kept for r in modules[m].get("requires", [])}
        unused = {m for m in kept if modules[m].get("implicit") and m not in needed}
        removed |= unused
        changed = bool(unused)

    kept = set(modules) - removed
    for name in sorted(kept):
        missing = sorted(set(modules[name].get("requires", [])) & removed)
        if missing:
            raise BootstrapError(f"{name} needs {', '.join(missing)}, which is removed")
    for group in manifest.get("rules", {}).get("keep_one_of", []):
        if not kept & set(group):
            raise BootstrapError(f"Keep at least one of {', '.join(group)}")
    return [m for m in modules if m in removed]


def old_home(dest: Path) -> Path:
    """Where ``--convert`` moves an existing project's files.

    :param dest: Project root
    :return: The sibling folder that keeps the old files
    """
    dest = dest.resolve()
    return dest.with_name(dest.name + OLD_SUFFIX)


def kept_folders(template: Path, manifest: dict, removed: list[str]) -> set[str]:
    """Top-level folders the new project will have.

    :param template: Template root
    :param manifest: The template manifest
    :param removed: Modules being removed
    :return: Folder names, such as ``frontend`` and ``api_service``
    """
    gone = {
        p
        for name in removed
        for p in manifest["modules"][name].get("paths", [])
        if "/" not in p
    }
    return {
        p.name
        for p in template.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_DIRS
    } - gone


def parse_copies(
    pairs: list[str], dest: Path, folders: set[str], convert: bool
) -> list[tuple[Path, Path]]:
    """Turn ``SRC=REL`` arguments into source and target paths.

    :param pairs: Raw ``--copy`` values
    :param dest: New project root
    :param folders: Top-level folders the new project keeps; every target goes
        inside one, so the project keeps stackkit's layout
    :param convert: Whether ``dest`` is being converted in place, in which
        case sources inside it are read from where its old files move to
    :return: Pairs of source path and path relative to ``dest``
    :raises BootstrapError: On a malformed pair, a missing source, a target
        outside stackkit's folders, a ``.env`` file, or a source that holds
        ``dest``
    """
    copies = []
    for pair in pairs:
        src, sep, rel = pair.partition("=")
        target = Path(rel)
        if not sep or not src or not rel:
            raise BootstrapError(f"--copy {pair!r}: expected SRC=REL")
        source = Path(src).expanduser()
        if not source.exists():
            raise BootstrapError(f"--copy {pair!r}: {source} doesn't exist")
        if (
            target.is_absolute()
            or ".." in target.parts
            or len(target.parts) < 2
            or target.parts[0] not in folders
        ):
            raise BootstrapError(
                f"--copy {pair!r}: REL must be inside one of the project's "
                f"folders ({', '.join(sorted(folders))})"
            )
        if CARRY_SKIP_RE.match(source.name) or CARRY_SKIP_RE.match(target.name):
            raise BootstrapError(f"--copy {pair!r}: .env files hold secrets")
        resolved, root = source.resolve(), dest.resolve()
        if convert and resolved.is_relative_to(root):
            source = old_home(dest) / resolved.relative_to(root)
        elif source.is_dir() and root.is_relative_to(resolved):
            raise BootstrapError(f"--copy {pair!r}: {source} contains {dest}")
        copies.append((source, target))
    return copies


def check_inputs(args: argparse.Namespace, manifest: dict) -> list[str]:
    """Validate everything before anything is written.

    :param args: Parsed arguments
    :param manifest: The template manifest
    :return: Modules to remove, including implicit ones
    :raises BootstrapError: On an invalid name, an impossible module set, or a
        non-empty destination
    """
    if not NAME_RE.match(args.name):
        raise BootstrapError(
            f"Name {args.name!r} must be lowercase letters, digits and dashes"
        )
    requested = [m.strip() for m in args.remove.split(",") if m.strip()]
    remove = resolve_removals(manifest, requested)
    filled = args.dest.is_dir() and any(args.dest.iterdir())
    if args.convert:
        if not filled:
            raise BootstrapError(f"--convert: {args.dest} has no project in it")
        if old_home(args.dest).exists():
            raise BootstrapError(f"--convert: {old_home(args.dest)} already exists")
    elif filled:
        raise BootstrapError(f"{args.dest} already exists and is not empty")
    return remove


def move_out(dest: Path) -> Path:
    """Move an existing project's files, all but ``.git``, out of the way.

    :param dest: Project root
    :return: The folder they moved to
    :side effects: Creates the sibling folder and moves files into it
    """
    old = old_home(dest)
    old.mkdir()
    for entry in dest.iterdir():
        if entry.name != ".git":
            shutil.move(entry, old / entry.name)
    return old


def copy_template(template: Path, dest: Path) -> None:
    """Copy the template, leaving out caches, installs and local secrets.

    :param template: Template root
    :param dest: New project root
    :side effects: Creates ``dest`` and writes files into it
    """

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in SKIP_DIRS or n in SKIP_FILES}

    shutil.copytree(template, dest, ignore=ignore, dirs_exist_ok=True)


def carry_over(dest: Path, copies: list[tuple[Path, Path]]) -> None:
    """Copy files from an existing project into the new one.

    :param dest: New project root
    :param copies: Pairs of source path and path relative to ``dest``
    :side effects: Writes files under ``dest``, replacing any already there
    """

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in CARRY_SKIP_DIRS or CARRY_SKIP_RE.match(n)}

    for source, rel in copies:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)


def remove_paths(dest: Path, module: dict) -> None:
    """Delete a module's folders and files.

    :param dest: Project root
    :param module: The module's manifest entry
    :side effects: Deletes files under ``dest``
    """
    for rel in module.get("paths", []):
        target = dest / rel
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def remove_json_keys(dest: Path, module: dict) -> None:
    """Delete a module's keys from JSON files, which can't hold markers.

    :param dest: Project root
    :param module: The module's manifest entry; ``json_keys`` maps a file to
        dotted key paths such as ``emulators.firestore``
    :side effects: Rewrites the JSON files
    """
    for rel, keys in module.get("json_keys", {}).items():
        path = dest / rel
        if not path.is_file():
            continue
        data = json.loads(path.read_text())
        for key in keys:
            *parents, leaf = key.split(".")
            node = data
            for part in parents:
                node = node.get(part, {})
            node.pop(leaf, None)
        path.write_text(json.dumps(data, indent=2) + "\n")


def drop_workspace_member(dest: Path, member: str) -> None:
    """Remove a package from the uv workspace ``members`` list.

    :param dest: Project root
    :param member: Workspace member name
    :side effects: Rewrites ``pyproject.toml``
    """
    path = dest / "pyproject.toml"
    text = path.read_text()
    text = re.sub(rf',\s*"{re.escape(member)}"|"{re.escape(member)}",\s*', "", text)
    path.write_text(text)


def strip_markers(text: str, removed: set[str]) -> str:
    """Delete removed modules' marked blocks and every marker line.

    A marker can name several modules (``stackkit:begin auth_iap,auth_firebase``);
    its block goes only when all of them are removed.

    :param text: File contents
    :param removed: Names of removed modules
    :return: The contents with blocks and markers gone
    :raises BootstrapError: On an unbalanced marker
    """
    out, skipping, marked, open_blocks = [], None, False, []
    for line in text.splitlines(keepends=True):
        match = MARKER_RE.search(line)
        if not match:
            if skipping is None:
                out.append(line)
            continue
        marked = True
        kind, name = match.groups()
        if kind == "begin":
            open_blocks.append(name)
            if skipping is None and set(name.split(",")) <= removed:
                skipping = name
        else:
            if not open_blocks or open_blocks.pop() != name:
                raise BootstrapError(
                    f"stackkit:end {name} doesn't close the innermost block"
                )
            if skipping == name:
                skipping = None
    if open_blocks:
        raise BootstrapError(f"stackkit:begin {open_blocks[-1]} has no matching end")
    result = "".join(out)
    if marked:
        # Removed blocks leave their surrounding blank lines behind
        result = re.sub(r"\n{4,}", "\n\n\n", result).rstrip("\n") + "\n"
    return result


def text_files(dest: Path):
    """Yield every UTF-8 text file in the project with its contents.

    :param dest: Project root
    :return: Pairs of path and text
    """
    for path in sorted(dest.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def rewrite_text(
    dest: Path, removed: set[str], values: dict[str, tuple[str, str]]
) -> None:
    """Apply marker removal and value replacement to every text file.

    :param dest: Project root
    :param removed: Names of removed modules
    :param values: Placeholder and replacement, by value name
    :side effects: Rewrites files under ``dest``
    """
    for path, text in list(text_files(dest)):
        try:
            new = strip_markers(text, removed)
        except BootstrapError as err:
            raise BootstrapError(f"{path.relative_to(dest)}: {err}") from err
        for placeholder, value in values.values():
            new = new.replace(placeholder, value)
        if new != text:
            path.write_text(new, encoding="utf-8")


def write_env(dest: Path, env: dict[str, str]) -> None:
    """Write ``.env`` from ``.env.sample`` with the given values filled in.

    :param dest: Project root
    :param env: Values by key
    :side effects: Writes ``dest/.env``
    """
    sample = dest / ".env.sample"
    lines = sample.read_text().splitlines() if sample.exists() else []
    done = set()
    for i, line in enumerate(lines):
        key = line.lstrip("# ").split("=", 1)[0]
        if "=" in line and key in env:
            lines[i] = f"{key}={env[key]}"
            done.add(key)
    lines += [f"{k}={v}" for k, v in env.items() if k not in done]
    (dest / ".env").write_text("\n".join(lines) + "\n")


LIST_ITEM_RE = re.compile(r"(\s*)(?:[-*+]|\d+\.)\s")
TABLE_RULE_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")


def drop_emptied(lines: list[str]) -> tuple[list[str], list[int]]:
    """Remove tables and code blocks that pruning left with nothing in them.

    :param lines: A Markdown file's lines, after pruning
    :return: The lines without them, and the line numbers where they were
    """
    out, emptied, i, in_code = [], [], 0, False
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        after = lines[i + 2] if i + 2 < len(lines) else ""
        if (
            not in_code
            and line.lstrip().startswith("|")
            and TABLE_RULE_RE.match(nxt.strip())
            and not after.lstrip().startswith("|")
        ):
            emptied.append(len(out) + 1)
            i += 2
            continue
        if line.strip().startswith("```"):
            if not in_code and nxt.strip() == "```":
                emptied.append(len(out) + 1)
                i += 2
                continue
            in_code = not in_code
        out.append(line)
        i += 1
    return out, emptied


def prune_markdown(
    dest: Path, refs: list[str], skip: list[Path]
) -> tuple[int, list[str]]:
    """Delete self-contained Markdown lines that mention removed modules.

    Table rows, list items (with their indented continuation lines) and lines
    inside code blocks stand on their own, so they go. Headings and prose are
    left for the skill to reword, and are still reported by ``leftover_refs``.

    :param dest: Project root
    :param refs: Strings that mark a removed module
    :param skip: Folders not to touch
    :return: How many lines were deleted, and ``path:line`` for each table or
        code block left empty and removed, whose heading or introduction may
        need rewording
    :side effects: Rewrites Markdown files under ``dest``
    """
    if not refs:
        return 0, []
    deleted, emptied = 0, []
    for path in sorted(dest.rglob("*.md")):
        if any(path.is_relative_to(s) for s in skip) or ".git" in path.parts:
            continue
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        out, in_code, item_indent = [], False, None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code, item_indent = not in_code, None
                out.append(line)
                continue
            if item_indent is not None:
                indent = len(line) - len(line.lstrip())
                if stripped and indent > item_indent:
                    deleted += 1
                    continue
                item_indent = None
            if any(r in line for r in refs):
                item = LIST_ITEM_RE.match(line)
                if in_code or stripped.startswith("|") or item:
                    item_indent = len(item.group(1)) if item and not in_code else None
                    deleted += 1
                    continue
            out.append(line)
        if len(out) != len(lines):
            out, gone = drop_emptied(out)
            rel = path.relative_to(dest)
            emptied += [f"{rel}:{n}" for n in gone]
            path.write_text("".join(out), encoding="utf-8")
    return deleted, emptied


def leftover_refs(
    dest: Path, manifest: dict, removed: set[str], carried: list[Path]
) -> list[str]:
    """Find mentions of removed modules that survived the removal.

    :param dest: Project root
    :param manifest: The template manifest
    :param removed: Names of removed modules
    :param carried: Paths, relative to ``dest``, copied from an existing
        project, which aren't checked
    :return: ``path:line: text`` entries, relative to ``dest``
    """
    modules = manifest["modules"]
    refs = [r for m in removed for r in modules[m].get("refs", [])]
    skip = [
        dest / p
        for name, module in modules.items()
        if name not in removed and module.get("self_contained")
        for p in module.get("paths", [])
    ] + [dest / rel for rel in carried]
    hits = []
    for path, text in text_files(dest):
        if path.name.endswith(".lock") or any(path.is_relative_to(s) for s in skip):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if any(r in line for r in refs):
                hits.append(f"{path.relative_to(dest)}:{n}: {line.strip()[:120]}")
    return hits


def render(
    template: Path, dest: Path, manifest: dict, remove: list[str], values: dict
) -> tuple[int, list[str]]:
    """Write the template with these modules removed and the name filled in.

    :param template: Template root
    :param dest: Where to write it
    :param manifest: The template manifest
    :param remove: Modules to remove, including implicit ones
    :param values: Placeholder and replacement, by value name
    :return: How many self-contained doc lines about removed modules were
        deleted, and where a whole table or code block went
    :side effects: Writes files under ``dest``
    """
    copy_template(template, dest)
    for name in remove:
        module = manifest["modules"][name]
        remove_paths(dest, module)
        remove_json_keys(dest, module)
        if member := module.get("workspace_member"):
            drop_workspace_member(dest, member)
    for name in set(manifest["modules"]) - set(remove):
        remove_paths(dest, {"paths": manifest["modules"][name].get("only_without", [])})
    rewrite_text(dest, set(remove), values)
    (dest / MANIFEST).unlink()
    modules = manifest["modules"]
    return prune_markdown(
        dest,
        [r for m in remove for r in modules[m].get("refs", [])],
        [
            dest / p
            for name, module in modules.items()
            if name not in remove and module.get("self_contained")
            for p in module.get("paths", [])
        ],
    )


def bootstrap(args: argparse.Namespace) -> dict:
    """Run the whole bootstrap.

    :param args: Parsed arguments
    :return: Summary of what was done
    :side effects: Creates the project at ``args.dest``
    """
    manifest = load_manifest(args.template)
    remove = check_inputs(args, manifest)
    env = parse_env(args.env, manifest["env"]["keys"])
    folders = kept_folders(args.template, manifest, remove)
    copies = parse_copies(args.copy, args.dest, folders, args.convert)
    old = move_out(args.dest) if args.convert else None
    values = {
        "name": (manifest["values"]["name"], args.name),
        "display_name": (manifest["values"]["display_name"], args.display_name),
    }

    pruned, emptied = render(args.template, args.dest, manifest, remove, values)
    write_env(args.dest, env)
    carry_over(args.dest, copies)

    return {
        "dest": str(args.dest.resolve()),
        "removed": remove,
        "kept": sorted(set(manifest["modules"]) - set(remove)),
        "old_files": str(old) if old else None,
        "carried": [str(rel) for _, rel in copies],
        "doc_lines_pruned": pruned,
        "doc_blocks_emptied": emptied,
        "leftover_refs": leftover_refs(
            args.dest, manifest, set(remove), [rel for _, rel in copies]
        ),
    }


def project_values(
    dest: Path, manifest: dict, name: str | None, display: str | None
) -> dict:
    """Work out an existing project's name and display name.

    :param dest: Project root
    :param manifest: The template manifest
    :param name: ``--name``, if given; otherwise read from ``pyproject.toml``
    :param display: ``--display-name``, if given; otherwise read from the web
        page's title, or made from the name when there's no web page
    :return: Placeholder and replacement, by value name
    :raises BootstrapError: If the name can't be found
    """
    pyproject = dest / "pyproject.toml"
    if not name and pyproject.is_file():
        name = tomllib.loads(pyproject.read_text()).get("project", {}).get("name")
    if not name:
        raise BootstrapError("--add: couldn't read the project's name; pass --name")
    page = dest / "frontend" / "index.html"
    title = (
        re.search(r"<title>([^<]+)</title>", page.read_text())
        if page.is_file()
        else None
    )
    if not display and title:
        display = title.group(1).strip()
    display = display or name.replace("-", " ").title()
    return {
        "name": (manifest["values"]["name"], name),
        "display_name": (manifest["values"]["display_name"], display),
    }


def merge_three_way(mine: Path, base: Path, theirs: Path) -> str | None:
    """Merge the template's change into a file the project has changed.

    :param mine: The project's file
    :param base: The template rendered with the project's current modules
    :param theirs: The template rendered with the added modules
    :return: The merged text, or None if it doesn't merge cleanly or git is missing
    """
    if not shutil.which("git"):
        return None
    result = subprocess.run(
        ["git", "merge-file", "-p", "-q", str(mine), str(base), str(theirs)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def unified(base: Path, theirs: Path, rel: str) -> str:
    """Show what adding the modules changes in one file.

    :param base: The file before
    :param theirs: The file after
    :param rel: Its path in the project, for the headers
    :return: A unified diff
    """
    return "".join(
        difflib.unified_diff(
            base.read_text().splitlines(keepends=True) if base.is_file() else [],
            theirs.read_text().splitlines(keepends=True),
            f"a/{rel}",
            f"b/{rel}",
        )
    )


def add_env_keys(dest: Path, sample: Path, env: dict[str, str]) -> list[str]:
    """Add keys the added modules need to the project's ``.env``, blank.

    :param dest: Project root
    :param sample: The new ``.env.sample``
    :param env: Values from ``--env``
    :return: The keys added
    :side effects: Appends to ``dest/.env``
    """
    path = dest / ".env"
    have = path.read_text() if path.is_file() else ""
    present = {
        line.split("=", 1)[0].strip() for line in have.splitlines() if "=" in line
    }
    added = []
    for line in sample.read_text().splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key not in present:
            added.append(key)
    if added:
        lines = [f"{key}={env.get(key, '')}" for key in added]
        tail = "" if not have or have.endswith("\n") else "\n"
        path.write_text(have + tail + "\n".join(lines) + "\n")
    return added


def use_old_names(tree: Path, legacy: dict[str, str]) -> None:
    """Rewrite a rendered template into a project's pre-rename layout.

    Projects made before the template renamed a folder keep its old name.
    Renaming the folder and its mentions in the rendered copies lets the
    three-way merge compare like with like.

    :param tree: A rendered template
    :param legacy: New folder name to old, from ``status.legacy_dirs``
    :side effects: Moves folders and rewrites text files in ``tree``
    """
    for new, old in legacy.items():
        if (tree / new).is_dir():
            (tree / new).rename(tree / old)
        package = new.replace("_", "-")
        for path in tree.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            fixed = text.replace(new, old).replace(package, old)
            if fixed != text:
                path.write_text(fixed, encoding="utf-8")


def add_modules(args: argparse.Namespace) -> dict:
    """Add modules to an existing stackkit project.

    :param args: Parsed arguments
    :return: Summary of what was done
    :raises BootstrapError: If the folder isn't a stackkit project, a module is
        unknown, nothing would be added, or the combination can't work
    :side effects: Writes, merges and removes files in ``args.dest``
    """
    manifest = load_manifest(args.template)
    modules = manifest["modules"]
    dest = args.dest
    if not (dest / "Makefile").is_file() or not (dest / "pyproject.toml").is_file():
        raise BootstrapError(f"--add: {dest} isn't a stackkit project")
    if args.remove or args.convert:
        raise BootstrapError("--add can't be combined with --remove or --convert")
    requested = {m.strip() for m in args.add.split(",") if m.strip()}
    if unknown := requested - set(modules):
        raise BootstrapError(f"--add: unknown modules {', '.join(sorted(unknown))}")

    current = set(status.kept_parts(dest, manifest))
    wanted = current | requested
    # A new server comes with its request examples, as in a fresh project
    if "api" in wanted - current:
        wanted.add("http_tests")
    while (
        needed := {r for m in wanted for r in modules[m].get("requires", [])} - wanted
    ):
        wanted |= needed
    remove_before = resolve_removals(manifest, sorted(set(modules) - current))
    remove_after = resolve_removals(manifest, sorted(set(modules) - wanted))
    added = sorted(set(remove_before) - set(remove_after))
    if not added:
        raise BootstrapError(
            f"--add: the project already has {', '.join(sorted(requested))}"
        )
    values = project_values(dest, manifest, args.name, args.display_name)
    env = parse_env(args.env, manifest["env"]["keys"])
    # A project made before a folder rename keeps the old name; copies go there
    legacy = status.legacy_dirs(dest)
    folders = {
        legacy.get(f, f) for f in kept_folders(args.template, manifest, remove_after)
    }
    copies = parse_copies(args.copy, dest, folders, False)

    summary = {
        "dest": str(dest.resolve()),
        "added": added,
        "kept": sorted(set(modules) - set(remove_after)),
        "new_files": [],
        "updated": [],
        "merged": [],
        "removed_files": [],
        "conflicts": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        base, after = Path(tmp) / "base", Path(tmp) / "after"
        render(args.template, base, manifest, remove_before, values)
        render(args.template, after, manifest, remove_after, values)
        if legacy:
            use_old_names(base, legacy)
            use_old_names(after, legacy)
        before_files = {p.relative_to(base) for p in base.rglob("*") if p.is_file()}
        after_files = {p.relative_to(after) for p in after.rglob("*") if p.is_file()}

        for rel in sorted(after_files):
            new, old, mine = after / rel, base / rel, dest / rel
            if rel not in before_files:
                if mine.exists():
                    summary["conflicts"].append(
                        {
                            "path": str(rel),
                            "reason": "the project already has a file here",
                        }
                    )
                    continue
                mine.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(new, mine)
                summary["new_files"].append(str(rel))
                continue
            if new.read_bytes() == old.read_bytes() or rel.name.endswith(".lock"):
                continue
            if not mine.exists():
                summary["conflicts"].append(
                    {
                        "path": str(rel),
                        "reason": "the project deleted this file",
                        "diff": unified(old, new, str(rel)),
                    }
                )
            elif mine.read_bytes() in (old.read_bytes(), new.read_bytes()):
                shutil.copy2(new, mine)
                summary["updated"].append(str(rel))
            elif (merged := merge_three_way(mine, old, new)) is not None:
                mine.write_text(merged)
                summary["merged"].append(str(rel))
            else:
                summary["conflicts"].append(
                    {
                        "path": str(rel),
                        "reason": "the project changed it too",
                        "diff": unified(old, new, str(rel)),
                    }
                )

        for rel in sorted(before_files - after_files):
            mine = dest / rel
            if mine.is_file() and mine.read_bytes() == (base / rel).read_bytes():
                mine.unlink()
                summary["removed_files"].append(str(rel))
            elif mine.is_file():
                summary["conflicts"].append(
                    {
                        "path": str(rel),
                        "reason": "no longer used, but the project changed it; delete it once its changes are moved",
                    }
                )
        summary["env_added"] = add_env_keys(dest, after / ".env.sample", env)
    carry_over(dest, copies)
    summary["carried"] = [str(rel) for _, rel in copies]
    # Docs that still describe parts the project doesn't have, from its first
    # build or from before this addition
    summary["leftover_refs"] = leftover_refs(
        dest, manifest, set(remove_after), [rel for _, rel in copies]
    )
    return summary


def main() -> int:
    """Command-line entry point.

    :return: Process exit code
    """
    try:
        args = parse_args(sys.argv[1:])
        summary = add_modules(args) if args.add else bootstrap(args)
    except BootstrapError as err:
        print(json.dumps({"error": str(err)}))
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
