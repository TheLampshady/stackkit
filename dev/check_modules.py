"""
Check that docs/MODULES.md lists every module in template/stackkit.toml.

For stackkit's maintainers; `make test-bootstrap` runs it. Standard library only.

Usage::

    uv run --no-project dev/check_modules.py
"""

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    """
    Compare the manifest's modules with the map's table rows.

    :return: 0 when every module has a row, 1 otherwise
    """
    with (ROOT / "template" / "stackkit.toml").open("rb") as handle:
        modules = tomllib.load(handle)["modules"]
    text = (ROOT / "docs" / "MODULES.md").read_text(encoding="utf-8")
    missing = [name for name in modules if f"| `{name}` |" not in text]
    for name in missing:
        print(f"  {name} is missing from docs/MODULES.md")
    if missing:
        return 1
    print("  ✓ docs/MODULES.md lists every module")
    return 0


if __name__ == "__main__":
    sys.exit(main())
