"""
Install a new project's dependencies and run its checks.

Runs, in the project folder: ``git init`` (if git is installed), ``uv lock``,
``uv sync``, ``bun install`` (if the frontend was kept), then ``make check``.
Stops at the first step that fails. One script instead of five commands, so
the skill needs a single permission rule for all of them. Standard library
only, so it runs anywhere ``uv run --no-project`` can find a Python.

Usage::

    check.py --dest ~/projects/bakery-orders

Prints a JSON summary on stdout. Exits non-zero if a tool is missing or a
step fails; the summary then carries the tail of that step's output.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TAIL_LINES = 60


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Read the command line.

    :param argv: Arguments after the script name
    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--dest", required=True, type=Path)
    return parser.parse_args(argv)


def plan_steps(dest: Path) -> list[tuple[str, list[str], Path]]:
    """List the steps to run for this project.

    :param dest: Project root
    :return: Step name, command and working folder, in order
    """
    steps = []
    if shutil.which("git") and not (dest / ".git").exists():
        steps.append(("git init", ["git", "init", "-q"], dest))
    steps += [
        ("uv lock", ["uv", "lock"], dest),
        ("uv sync", ["uv", "sync", "--all-extras", "--all-groups"], dest),
    ]
    if (dest / "frontend").is_dir():
        steps.append(("bun install", ["bun", "install"], dest / "frontend"))
    steps.append(("make check", ["make", "check"], dest))
    return steps


def missing_tools(steps: list[tuple[str, list[str], Path]]) -> list[str]:
    """Find the programs the steps need that aren't installed.

    :param steps: Steps from ``plan_steps``
    :return: Program names not on ``PATH``
    """
    return sorted({cmd[0] for _, cmd, _ in steps if not shutil.which(cmd[0])})


def tail(text: str) -> str:
    """Keep the end of a command's output, where the error usually is.

    :param text: Full output
    :return: The last ``TAIL_LINES`` lines
    """
    return "\n".join(text.strip().splitlines()[-TAIL_LINES:])


def check(dest: Path) -> dict:
    """Run every step, stopping at the first failure.

    :param dest: Project root
    :return: Summary with ``ok``, the steps that passed and any failure
    :side effects: Installs dependencies into ``dest`` and may create ``dest/.git``
    """
    if not (dest / "Makefile").is_file():
        return {"ok": False, "error": f"{dest} is not a stackkit project"}
    steps = plan_steps(dest)
    if missing := missing_tools(steps):
        return {"ok": False, "error": f"Not installed: {', '.join(missing)}"}

    passed = []
    for name, cmd, cwd in steps:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            return {
                "ok": False,
                "passed": passed,
                "failed": name,
                "output": tail(result.stdout + result.stderr),
            }
        passed.append(name)
    return {"ok": True, "passed": passed}


def main() -> int:
    """Command-line entry point.

    :return: Process exit code
    """
    args = parse_args(sys.argv[1:])
    summary = {"dest": str(args.dest.resolve()), **check(args.dest)}
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
