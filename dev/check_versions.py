"""
Check stackkit's pinned emulator tool versions against the latest Firebase CLI.

``skills/create/scripts/status.py`` pins the oldest Java and Node the Firebase
CLI accepts, and the template's ``docs/ENVIRONMENTS.md`` repeats them in its
install steps. This reads what the latest CLI actually requires, from its npm
``engines`` field and the Java constant in that release's source, and fails if
either pin or the docs are out of step. For stackkit's maintainers; new
projects never run it. Standard library only.

Usage::

    uv run --no-project dev/check_versions.py
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Import status.py for its pins without leaving a cache in the plugin folder
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "skills" / "create" / "scripts"))
import status

NPM_LATEST = "https://registry.npmjs.org/firebase-tools/latest"
JAVA_SOURCE = (
    "https://raw.githubusercontent.com/firebase/firebase-tools/"
    "v{version}/src/emulator/commandUtils.ts"
)
JAVA_CONST_RE = re.compile(r"MIN_SUPPORTED_JAVA_MAJOR_VERSION\s*=\s*(\d+)")
DOCS = ROOT / "template" / "docs" / "ENVIRONMENTS.md"


def fetch(url: str) -> str:
    """Download a URL as text.

    :param url: Address to fetch
    :return: The response body
    """
    request = urllib.request.Request(url, headers={"User-Agent": "stackkit-dev"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode()


def required() -> tuple[str, int, int]:
    """Read what the latest Firebase CLI requires.

    :return: CLI version, oldest Java major and oldest Node major it accepts
    :raises ValueError: If the Java constant can't be found in its source
    """
    latest = json.loads(fetch(NPM_LATEST))
    version = latest["version"]
    node = min(int(m) for m in re.findall(r">=\s*(\d+)", latest["engines"]["node"]))
    match = JAVA_CONST_RE.search(fetch(JAVA_SOURCE.format(version=version)))
    if not match:
        raise ValueError(
            "MIN_SUPPORTED_JAVA_MAJOR_VERSION is no longer in "
            f"{JAVA_SOURCE.format(version=version)}; find where the CLI checks "
            "Java now and update this script"
        )
    return version, int(match.group(1)), node


def doc_problems(java: int, node: int) -> list[str]:
    """Find install steps in the template docs that don't match the pins.

    :param java: Pinned Java major
    :param node: Pinned Node major
    :return: One line per expected phrase that's missing
    """
    text = DOCS.read_text()
    expected = [
        f"older than {java}",
        f"openjdk-{java}-jre-headless",
        f"temurin@{java}",
        f"Node {node} or newer",
    ]
    return [
        f"{DOCS.relative_to(ROOT)} doesn't say {e!r}" for e in expected if e not in text
    ]


def main() -> int:
    """Command-line entry point.

    :return: Process exit code
    """
    version, java, node = required()
    print(f"Firebase CLI {version} needs Java {java}+ and Node {node}+")
    problems = []
    if java != status.JAVA_MIN:
        problems.append(
            f"status.py pins JAVA_MIN = {status.JAVA_MIN}; set it to {java}"
        )
    if node != status.NODE_MIN:
        problems.append(
            f"status.py pins NODE_MIN = {status.NODE_MIN}; set it to {node}"
        )
    problems += doc_problems(status.JAVA_MIN, status.NODE_MIN)
    for problem in problems:
        print(f"  ✗ {problem}")
    if problems:
        print(
            "Update JAVA_MIN / NODE_MIN in skills/create/scripts/status.py, then the "
            "install steps in template/docs/ENVIRONMENTS.md to match."
        )
        return 1
    print("  ✓ status.py and the template docs match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
