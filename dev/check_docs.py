"""
Check a bootstrapped project's Markdown survived pruning intact.

Pruning deletes table rows, list items and code lines about removed modules.
This fails if that left a code block unclosed or empty, or a table with only
its header. For stackkit's maintainers; `make test-bootstrap` runs it on each
sample. Standard library only.

Usage::

    uv run --no-project dev/check_docs.py <project folder>
"""

import re
import sys
from pathlib import Path

RULE_RE = re.compile(r"^\|[\s\-:|]+\|$")
EMPTY_BLOCK_RE = re.compile(r"^```[\w-]*\n```$", re.MULTILINE)


def problems(path: Path) -> list[str]:
    """Find broken structure in one Markdown file.

    :param path: The file
    :return: One line per problem
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    found = []
    if sum(1 for line in lines if line.strip().startswith("```")) % 2:
        found.append("unclosed code block")
    for i, line in enumerate(lines[:-1]):
        after = lines[i + 2] if i + 2 < len(lines) else ""
        if (
            line.startswith("|")
            and RULE_RE.match(lines[i + 1].strip())
            and not after.startswith("|")
        ):
            found.append(f"line {i + 1}: table with only a header")
    if EMPTY_BLOCK_RE.search(text):
        found.append("empty code block")
    return found


def main() -> int:
    """Command-line entry point.

    :return: Process exit code
    """
    root = Path(sys.argv[1])
    bad = [
        f"{path.relative_to(root)}: {p}"
        for path in sorted(root.rglob("*.md"))
        if "node_modules" not in path.parts and ".venv" not in path.parts
        for p in problems(path)
    ]
    for line in bad:
        print(f"   ✗ {line}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
