"""
Create a new project from the stackkit template.

Copies the template into a new folder, removes the modules the project does
not need, swaps in the project's name, writes its ``.env``, and reports any
mention of a removed module that is still in the copy. Standard library only,
so it runs anywhere ``uv run --no-project`` can find a Python.

Usage::

    bootstrap.py --dest ~/projects/bakery-orders --name bakery-orders \\
        --display-name "Bakery Orders" --remove agents,notebooks \\
        --env PROJECT_ID=bakery-orders-prod --env NAMESPACE=orders

Prints a JSON summary on stdout. Exits non-zero, having written nothing, if
an argument is invalid or the destination is not empty.
"""

import argparse
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

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
MARKER_RE = re.compile(r"stackkit:(begin|end) ([a-z_]+)")


class BootstrapError(Exception):
    """A problem the person running the bootstrap has to fix."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Read the command line.

    :param argv: Arguments after the script name
    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--remove", default="", help="comma-separated modules")
    parser.add_argument("--env", action="append", default=[], help="KEY=VALUE")
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    return parser.parse_args(argv)


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
            raise BootstrapError(f"--env {pair!r}: expected one of {allowed} as KEY=VALUE")
        env[key] = value
    return env


def check_inputs(args: argparse.Namespace, manifest: dict) -> list[str]:
    """Validate everything before anything is written.

    :param args: Parsed arguments
    :param manifest: The template manifest
    :return: Modules to remove
    :raises BootstrapError: On an invalid name, unknown module, or non-empty destination
    """
    if not NAME_RE.match(args.name):
        raise BootstrapError(
            f"Name {args.name!r} must be lowercase letters, digits and dashes"
        )
    remove = [m.strip() for m in args.remove.split(",") if m.strip()]
    unknown = sorted(set(remove) - set(manifest["modules"]))
    if unknown:
        raise BootstrapError(
            f"Unknown modules {unknown}; choose from {sorted(manifest['modules'])}"
        )
    if args.dest.exists() and any(args.dest.iterdir()):
        raise BootstrapError(f"{args.dest} already exists and is not empty")
    return remove


def copy_template(template: Path, dest: Path) -> None:
    """Copy the template, leaving out caches, installs and local secrets.

    :param template: Template root
    :param dest: New project root
    :side effects: Creates ``dest`` and writes files into it
    """

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in SKIP_DIRS or n in SKIP_FILES}

    shutil.copytree(template, dest, ignore=ignore, dirs_exist_ok=True)


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

    :param text: File contents
    :param removed: Names of removed modules
    :return: The contents with blocks and markers gone
    :raises BootstrapError: On an unbalanced marker
    """
    out, skipping = [], None
    for line in text.splitlines(keepends=True):
        match = MARKER_RE.search(line)
        if not match:
            if skipping is None:
                out.append(line)
            continue
        kind, name = match.groups()
        if kind == "begin":
            if skipping is None and name in removed:
                skipping = name
        elif skipping == name:
            skipping = None
    if skipping is not None:
        raise BootstrapError(f"stackkit:begin {skipping} has no matching end")
    return "".join(out)


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


def rewrite_text(dest: Path, removed: set[str], values: dict[str, tuple[str, str]]) -> None:
    """Apply marker removal and value replacement to every text file.

    :param dest: Project root
    :param removed: Names of removed modules
    :param values: Placeholder and replacement, by value name
    :side effects: Rewrites files under ``dest``
    """
    for path, text in list(text_files(dest)):
        new = strip_markers(text, removed)
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


def leftover_refs(dest: Path, manifest: dict, removed: set[str]) -> list[str]:
    """Find mentions of removed modules that survived the removal.

    :param dest: Project root
    :param manifest: The template manifest
    :param removed: Names of removed modules
    :return: ``path:line: text`` entries, relative to ``dest``
    """
    refs = [r for m in removed for r in manifest["modules"][m].get("refs", [])]
    hits = []
    for path, text in text_files(dest):
        if path.name.endswith(".lock"):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if any(r in line for r in refs):
                hits.append(f"{path.relative_to(dest)}:{n}: {line.strip()[:120]}")
    return hits


def bootstrap(args: argparse.Namespace) -> dict:
    """Run the whole bootstrap.

    :param args: Parsed arguments
    :return: Summary of what was done
    :side effects: Creates the project at ``args.dest``
    """
    manifest = load_manifest(args.template)
    remove = check_inputs(args, manifest)
    env = parse_env(args.env, manifest["env"]["keys"])
    values = {
        "name": (manifest["values"]["name"], args.name),
        "display_name": (manifest["values"]["display_name"], args.display_name),
    }

    copy_template(args.template, args.dest)
    for name in remove:
        module = manifest["modules"][name]
        remove_paths(args.dest, module)
        if member := module.get("workspace_member"):
            drop_workspace_member(args.dest, member)
    rewrite_text(args.dest, set(remove), values)
    write_env(args.dest, env)
    (args.dest / MANIFEST).unlink()

    return {
        "dest": str(args.dest.resolve()),
        "removed": remove,
        "kept": sorted(set(manifest["modules"]) - set(remove)),
        "leftover_refs": leftover_refs(args.dest, manifest, set(remove)),
    }


def main() -> int:
    """Command-line entry point.

    :return: Process exit code
    """
    try:
        summary = bootstrap(parse_args(sys.argv[1:]))
    except BootstrapError as err:
        print(json.dumps({"error": str(err)}))
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
