"""
Report what's left to set up in a project made from the stackkit template.

Changes nothing. Reads the project and prints JSON with:

- ``parts``: the template's modules the project has, found by the files and
  settings each one leaves (the template manifest says which)
- ``tools``: tools this computer is missing or has too old for the project,
  each with the commands that fix it here
- ``env``: whether ``.env`` exists, its blank keys, and whether each secret
  name is set or blank in it (never the values)
- ``cloud``: whether the project's database and file storage exist in Google
  Cloud yet, checked read-only with ``gcloud`` once ``PROJECT_ID`` is set
- ``scaling``: for each host the server can deploy to, the fewest and most
  copies it runs at once, read from its deploy settings
- ``access``: the Google Cloud steps the project needs (creating the database,
  granting roles, deploying), the roles each takes if you aren't the project's
  Owner, and, once ``PROJECT_ID`` is set and ``gcloud`` is signed in, whether
  your account can do each one and whether Cloud Run's build account has the
  role source deploys need. Read-only: it asks Google, it never grants

``check.py`` adds this to its summary at the end of a bootstrap, and the
status skill runs it on its own. Standard library only, so it runs anywhere
``uv run --no-project`` can find a Python.

Usage::

    status.py --dest ~/projects/bakery-orders
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[3] / "template"

# The one place stackkit pins tool versions and install commands. The skills
# read them from this script's output; the template's docs/ENVIRONMENTS.md
# repeats the Java and Node ones in its install steps. `make check-versions`
# compares both with what the latest Firebase CLI requires. Firebase CLI 15
# refuses Java before 21; CLI 14 dropped Node 18.
JAVA_MIN = 21
NODE_MIN = 20
FIREBASE_INSTALL = "curl -sL https://firebase.tools | bash"
INSTALL = {
    "uv": {"any": ["curl -LsSf https://astral.sh/uv/install.sh | sh"]},
    "bun": {"any": ["curl -fsSL https://bun.sh/install | bash"]},
    "make": {
        "linux": ["sudo apt-get update", "sudo apt-get install -y make"],
        "darwin": ["xcode-select --install"],
    },
    # Smallest free Java: the headless OpenJDK runtime, or Eclipse Temurin on a Mac
    "java": {
        "linux": [
            "sudo apt-get update",
            f"sudo apt-get install -y openjdk-{JAVA_MIN}-jre-headless",
        ],
        "darwin": [f"brew install --cask temurin@{JAVA_MIN}"],
    },
}
PROVISION = "make -C gcp provision"
SETUP_IAM = "make -C gcp setup-iam"

# Folders the template renamed: new name, then the name projects made before
# the rename still have. Every path the manifest names goes through
# ``project_path``, so both layouts are read the same way.
RENAMED = {"api_service": "service"}
# A manifest path starting with this names that file in every service's copy
COPIES = "gcp_services"


def legacy_dirs(dest: Path) -> dict[str, str]:
    """Find the renamed folders this project still has under their old name.

    :param dest: Project root
    :return: New name to old name, for each folder only the old name exists for
    """
    return {
        new: old
        for new, old in RENAMED.items()
        if not (dest / new).exists() and (dest / old).is_dir()
    }


def project_path(dest: Path, rel: str) -> Path:
    """Resolve a template path in a project made by any version of stackkit.

    :param dest: Project root
    :param rel: Path as the template names it, such as ``api_service/app.yaml``
    :return: Where that path is in this project, under a renamed folder's old
        name if it still has it
    """
    first, _, rest = rel.partition("/")
    old = legacy_dirs(dest).get(first)
    return dest / (f"{old}/{rest}" if old and rest else old or rel)


def service_copies(dest: Path, rel: str) -> list[Path]:
    """Every service's copy of a ``gcp_services/`` file the manifest names.

    :param dest: Project root
    :param rel: Such as ``gcp_services/clients/fb_auth.py``
    :return: That file in each folder with a ``gcp_services/`` (``api_service``,
        ``job_service``, an older project's ``service``), whether or not it's there
    """
    return [d / rel for d in sorted(dest.iterdir()) if (d / COPIES).is_dir()]


def manifest_paths(dest: Path, rel: str) -> list[Path]:
    """Where a path the manifest names is in this project.

    :param dest: Project root
    :param rel: A manifest path
    :return: Every service's copy for a ``gcp_services/`` path, else the one path
    """
    if rel.split("/", 1)[0] == COPIES:
        return service_copies(dest, rel)
    return [project_path(dest, rel)]


# Google Cloud steps: (what, needed when the project has, permission tested,
# roles that allow it for someone who isn't the project's Owner). Roles from
# Google's docs for Cloud Run source deploys and App Engine deploys.
ACCESS_STEPS = [
    (
        f"grant the server's and jobs' accounts their roles ({SETUP_IAM})",
        "iam",
        "resourcemanager.projects.setIamPolicy",
        ["roles/resourcemanager.projectIamAdmin"],
    ),
    (
        f"create the database ({PROVISION})",
        "database",
        "datastore.databases.create",
        ["roles/datastore.owner"],
    ),
    (
        f"create the file bucket ({PROVISION})",
        "storage",
        "storage.buckets.create",
        ["roles/storage.admin"],
    ),
    (
        "add keys to Secret Manager",
        "iam",
        "secretmanager.secrets.create",
        ["roles/secretmanager.admin"],
    ),
    (
        "put it online on Cloud Run (make deploy-cr)",
        "cloud_run",
        "run.services.create",
        [
            "roles/run.sourceDeveloper",
            "roles/serviceusage.serviceUsageConsumer",
            "roles/iam.serviceAccountUser",
            # Only Cloud Run Admin can make a service public (no team sign-in)
            "roles/run.admin",
        ],
    ),
    (
        "put background jobs online and on a timer (make deploy-job, make schedule-job)",
        "jobs",
        "run.jobs.create",
        [
            "roles/run.sourceDeveloper",
            "roles/serviceusage.serviceUsageConsumer",
            "roles/iam.serviceAccountUser",
            "roles/cloudscheduler.admin",
        ],
    ),
    (
        "put it online on App Engine (make deploy-app)",
        "gae",
        "appengine.versions.create",
        [
            "roles/appengine.deployer",
            "roles/iam.serviceAccountUser",
            "roles/cloudbuild.builds.editor",
            "roles/storage.objectAdmin",
        ],
    ),
]
# Cloud Run source deploys build as the Compute Engine default account, which
# needs this role; newer projects don't give it Editor, which used to cover it.
BUILD_ROLES = {"roles/run.builder", "roles/editor"}
# Parts deployed by a Cloud Run source build
BUILDS_ON_CLOUD_RUN = {"cloud_run", "jobs"}
TEST_PERMISSIONS = (
    "https://cloudresourcemanager.googleapis.com/v1/projects/{project}"
    ":testIamPermissions"
)

JAVA_RE = re.compile(r'version "(?:1\.)?(\d+)')
NODE_RE = re.compile(r"v(\d+)\.")
SECRETS_RE = re.compile(r"SECRET_KEY_NAMES\s*=\s*\[([^\]]*)\]")
SCAN_SKIP = {".git", ".venv", "node_modules", "dist", "static", "__pycache__"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Read the command line.

    :param argv: Arguments after the script name
    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--dest", required=True, type=Path)
    return parser.parse_args(argv)


def probe(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    """Run a command quietly, never waiting for input.

    :param cmd: Command to run
    :param timeout: Seconds before giving up
    :return: Exit code (127 if it couldn't run) and its combined output
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return 127, str(err)
    return result.returncode, result.stdout + result.stderr


def last_line(text: str) -> str:
    """Keep the last non-empty line of a command's output.

    :param text: Full output
    :return: That line, or an empty string
    """
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1].strip()[:200] if lines else ""


def fix(tool: str) -> list[str]:
    """The commands that install a tool on this computer.

    :param tool: Key in ``INSTALL``
    :return: Commands in order; empty where stackkit has none for this system
    """
    by_system = INSTALL[tool]
    return by_system.get("any") or by_system.get(sys.platform, [])


def kept_parts(dest: Path, manifest: dict) -> list[str]:
    """Find the template modules this project has.

    :param dest: Project root
    :param manifest: The template manifest
    :return: Module names in manifest order
    """
    code = None
    kept = []
    for name, module in manifest["modules"].items():
        if paths := module.get("paths"):
            if any(f.exists() for p in paths for f in manifest_paths(dest, p)):
                kept.append(name)
            continue
        if code is None:
            code = "\n".join(code_texts(dest))
        if any(ref in code for ref in module.get("refs", [])):
            kept.append(name)
    return kept


def code_texts(dest: Path):
    """Yield the text of the project's files other than Markdown.

    :param dest: Project root
    :return: File contents, one at a time
    """
    for path in dest.rglob("*"):
        if (
            not path.is_file()
            or path.suffix == ".md"
            or SCAN_SKIP & set(path.relative_to(dest).parts)
        ):
            continue
        try:
            yield path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def tool_report(parts: list[str]) -> list[dict]:
    """Find tools the project needs that this computer lacks.

    :param parts: Modules the project has
    :return: One entry per tool, with ``tool``, ``problem``, ``needed_for``
        and ``run``
    """
    problems = []
    needed = [("uv", "running it"), ("make", "running it")]
    if "frontend" in parts:
        needed.append(("bun", "the web page"))
    for tool, purpose in needed:
        if not shutil.which(tool):
            problems.append(
                {
                    "tool": tool,
                    "problem": "missing",
                    "needed_for": purpose,
                    "run": fix(tool),
                }
            )
    if "firebase" in parts:
        problems += emulator_tools()
    return problems


def emulator_tools() -> list[dict]:
    """Find what the local Firebase emulator needs that isn't ready.

    :return: One entry per tool to install or upgrade
    """
    problems = []
    purpose = "the local database copy (make emulator)"
    code, out = probe(["java", "-version"])
    match = JAVA_RE.search(out)
    if code != 0 or not match:
        java = f"missing; needs Java {JAVA_MIN}+"
    elif int(match.group(1)) < JAVA_MIN:
        java = f"Java {match.group(1)} is too old; needs {JAVA_MIN}+"
    else:
        java = None
    if java:
        problems.append(
            {"tool": "java", "problem": java, "needed_for": purpose, "run": fix("java")}
        )

    found = shutil.which("firebase")
    if not found:
        firebase, run = "missing", [FIREBASE_INSTALL]
    elif (
        "node_modules" in Path(found).resolve().parts
        and (node := node_major()) < NODE_MIN
    ):
        firebase = f"installed with npm on Node {node or 'unknown'}; needs {NODE_MIN}+"
        run = ["npm uninstall -g firebase-tools", FIREBASE_INSTALL]
    elif (result := probe(["firebase", "--version"]))[0] != 0:
        firebase, run = f"fails: {last_line(result[1])}", [FIREBASE_INSTALL]
    else:
        return problems
    problems.append(
        {"tool": "firebase", "problem": firebase, "needed_for": purpose, "run": run}
    )
    return problems


def node_major() -> int:
    """Find the installed Node's major version.

    :return: The major version, or 0 if Node is missing
    """
    match = NODE_RE.search(probe(["node", "--version"])[1])
    return int(match.group(1)) if match else 0


def read_env(path: Path) -> dict[str, str]:
    """Read the active ``KEY=VALUE`` lines of an env file.

    :param path: The file
    :return: Values by key; commented-out lines are left out
    """
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("\"'")
    return values


def secret_names(dest: Path) -> list[str]:
    """Read the secret names the project's settings load.

    :param dest: Project root
    :return: Names in order, without the template's ``TODO`` placeholder
    """
    names = []
    # Every service's settings, and the server's from before it was api_service/
    paths = sorted(dest.glob("*_service/app_settings.py"))
    paths += [dest / old / "app_settings.py" for old in RENAMED.values()]
    for path in paths:
        if path.is_file() and (match := SECRETS_RE.search(path.read_text())):
            for name in re.findall(r"[\"']([A-Z0-9_]+)[\"']", match.group(1)):
                if name != "TODO" and name not in names:
                    names.append(name)
    return names


def env_report(dest: Path) -> tuple[dict, dict[str, str]]:
    """Check ``.env`` without revealing any value.

    :param dest: Project root
    :return: The report, and the values for the cloud checks
    """
    path = dest / ".env"
    if not path.is_file():
        return {"exists": False, "blank": [], "secrets": {}}, {}
    values = read_env(path)
    secrets = {
        name: ("set" if values.get(name) else "blank") for name in secret_names(dest)
    }
    blank = [k for k, v in values.items() if not v and k not in secrets]
    return {"exists": True, "blank": blank, "secrets": secrets}, values


def cloud_report(parts: list[str], env: dict[str, str]) -> list[dict]:
    """Check, read-only, whether the cloud database and storage exist yet.

    :param parts: Modules the project has
    :param env: Values from ``.env``
    :return: One entry per resource, with ``resource``, ``name``, ``state``
        (``exists``, ``missing`` or ``unchecked``), ``reason`` when unchecked,
        and ``create``, the command that creates it
    """
    project, namespace = env.get("PROJECT_ID"), env.get("NAMESPACE")
    wanted = []
    if "database" in parts:
        name = env.get("FIRESTORE_DB_NAME") or namespace or "(default)"
        wanted.append(
            (
                "database",
                name,
                ["firestore", "databases", "describe", f"--database={name}"],
            )
        )
    if "storage" in parts:
        name = (
            env.get("FIRESTORE_BUCKET_NAME")
            or f"{project or '<PROJECT_ID>'}-{namespace}"
        )
        wanted.append(
            ("storage", name, ["storage", "buckets", "describe", f"gs://{name}"])
        )

    entries = []
    for resource, name, describe in wanted:
        entry = {"resource": resource, "name": name, "create": PROVISION}
        if not project:
            entry |= {"state": "unchecked", "reason": "PROJECT_ID is blank in .env"}
        elif not shutil.which("gcloud"):
            entry |= {"state": "unchecked", "reason": "gcloud isn't installed"}
        else:
            code, out = probe(
                ["gcloud", *describe, f"--project={project}", "--format=value(name)"],
                timeout=30,
            )
            if code == 0:
                entry["state"] = "exists"
            elif re.search(r"NOT_FOUND|not found|does not exist|404", out):
                entry["state"] = "missing"
            else:
                entry |= {"state": "unchecked", "reason": last_line(out)}
        entries.append(entry)
    return entries


def instances(text: str, key: str) -> int | None:
    """Read one scaling number from a deploy setting.

    :param text: The setting's text: ``app.yaml``'s ``min_instances: 1`` or the
        Makefile's ``MIN_INSTANCES := 1``; the last assignment wins, as in make
    :param key: ``min`` or ``max``
    :return: The number, or None if it isn't set
    """
    found = re.findall(
        rf"^\s*{key}_instances\s*(?::=|=|:)\s*(\d+)", text, re.IGNORECASE | re.MULTILINE
    )
    return int(found[-1]) if found else None


def scaling_report(dest: Path, parts: list[str]) -> list[dict]:
    """Read how the server scales on each host it can deploy to.

    :param dest: Project root
    :param parts: Modules the project has
    :return: One entry per host, with ``host``, ``min``, ``max`` (None means
        no cap) and ``file``, the setting to change
    """
    if "api" not in parts:
        return []
    hosts = []
    makefile = project_path(dest, "api_service/Makefile")
    if "cloud_run" in parts and makefile.is_file():
        text = makefile.read_text()
        hosts.append(
            {
                "host": "cloud_run",
                "min": instances(text, "min") or 0,
                "max": instances(text, "max"),
                "file": str(makefile.relative_to(dest)),
            }
        )
    app_yaml = project_path(dest, "api_service/app.yaml")
    if "gae" in parts and app_yaml.is_file():
        text = app_yaml.read_text()
        hosts.append(
            {
                "host": "gae",
                "min": instances(text, "min") or 0,
                "max": instances(text, "max"),
                "file": str(app_yaml.relative_to(dest)),
            }
        )
    return hosts


def gcloud_out(args: list[str]) -> str | None:
    """Run a read-only gcloud command and keep its standard output.

    :param args: Arguments after ``gcloud``
    :return: The output, stripped, or None if the command failed
    """
    try:
        result = subprocess.run(
            ["gcloud", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def held_permissions(project: str, permissions: list[str]) -> set[str] | str:
    """Ask Google which of these permissions the signed-in account has.

    :param project: Google Cloud project id
    :param permissions: Permission names to test
    :return: The ones held, or why they couldn't be checked
    """
    token = gcloud_out(["auth", "print-access-token"])
    if not token:
        return "gcloud isn't signed in (gcloud auth login)"
    request = urllib.request.Request(
        TEST_PERMISSIONS.format(project=project),
        data=json.dumps({"permissions": permissions}).encode(),
        headers={
            "Authorization": f"Bearer {token.splitlines()[-1]}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return set(json.load(response).get("permissions", []))
    except urllib.error.HTTPError as err:
        if err.code == 401:
            return "gcloud's sign-in has expired (gcloud auth login)"
        if err.code in (403, 404):
            return f"your account can't see project {project}"
        return f"Google Cloud answered {err.code}"
    except (OSError, ValueError):
        return "couldn't reach Google Cloud"


def build_account(project: str) -> dict:
    """Check whether Cloud Run's build account can build source deploys.

    :param project: Google Cloud project id
    :return: ``account``, ``ready`` (None if unchecked), ``reason`` when
        unchecked, and ``fix``
    """
    entry = {"account": None, "role": "roles/run.builder", "fix": SETUP_IAM}
    number = gcloud_out(
        ["projects", "describe", project, "--format=value(projectNumber)"]
    )
    if not number:
        return entry | {"ready": None, "reason": "couldn't read the project"}
    entry["account"] = f"{number}-compute@developer.gserviceaccount.com"
    policy = gcloud_out(["projects", "get-iam-policy", project, "--format=json"])
    if not policy:
        return entry | {
            "ready": None,
            "reason": "your account can't read the project's permissions",
        }
    member = f"serviceAccount:{entry['account']}"
    bindings = json.loads(policy).get("bindings", [])
    ready = any(
        b.get("role") in BUILD_ROLES and member in b.get("members", [])
        for b in bindings
    )
    return entry | {"ready": ready}


def access_report(parts: list[str], env: dict[str, str]) -> dict:
    """Check, read-only, who can do the project's Google Cloud steps.

    :param parts: Modules the project has
    :param env: Values from ``.env``
    :return: ``account``, ``checked``, ``reason`` when unchecked, ``steps``
        (each with ``step``, ``roles`` and ``can``: True, False or None), and
        ``build_account`` for Cloud Run; empty when there's nothing to set up
    """
    steps = [
        {"step": step, "roles": roles, "can": None, "permission": permission}
        for step, part, permission, roles in ACCESS_STEPS
        if part in parts
    ]
    if not steps:
        return {}
    result = {"account": None, "checked": False, "steps": steps}
    project = env.get("PROJECT_ID")
    if not project:
        result["reason"] = "PROJECT_ID is blank in .env"
    elif not shutil.which("gcloud"):
        result["reason"] = "gcloud isn't installed"
    else:
        result["account"] = gcloud_out(["config", "get-value", "account"]) or None
        held = held_permissions(project, [s["permission"] for s in steps])
        if isinstance(held, str):
            result["reason"] = held
        else:
            result["checked"] = True
            for step in steps:
                step["can"] = step["permission"] in held
        if BUILDS_ON_CLOUD_RUN & set(parts):
            result["build_account"] = build_account(project)
    if BUILDS_ON_CLOUD_RUN & set(parts) and "build_account" not in result:
        result["build_account"] = {
            "account": None,
            "role": "roles/run.builder",
            "fix": SETUP_IAM,
            "ready": None,
            "reason": result["reason"],
        }
    for step in steps:
        del step["permission"]
    return result


def project_names(dest: Path) -> tuple[str | None, str | None]:
    """Read the project's short name and the title people see.

    :param dest: Project root
    :return: The name from ``pyproject.toml`` and the web page's title, or the
        name made readable when there's no web page
    """
    pyproject = dest / "pyproject.toml"
    name = None
    if pyproject.is_file():
        name = tomllib.loads(pyproject.read_text()).get("project", {}).get("name")
    page = dest / "frontend" / "index.html"
    title = (
        re.search(r"<title>([^<]+)</title>", page.read_text())
        if page.is_file()
        else None
    )
    display = title.group(1).strip() if title else None
    return name, display or (name.replace("-", " ").title() if name else None)


def report(dest: Path, template: Path = TEMPLATE) -> dict:
    """Build the whole status report.

    :param dest: Project root
    :param template: Template root, for its manifest
    :return: The report
    """
    if not (dest / "Makefile").is_file():
        return {"error": f"{dest} is not a stackkit project"}
    manifest = tomllib.loads((template / "stackkit.toml").read_text())
    parts = kept_parts(dest, manifest)
    env, values = env_report(dest)
    name, display = project_names(dest)
    return {
        "checked": date.today().isoformat(),
        "name": name,
        "display_name": display,
        "parts": parts,
        "tools": tool_report(parts),
        "env": env,
        "cloud": cloud_report(parts, values),
        "scaling": scaling_report(dest, parts),
        "access": access_report(parts, values),
    }


def local_time_zone() -> str:
    """The computer's time zone, for the interview to assume when a timer runs.

    :return: An IANA name such as ``Europe/London``, or ``Etc/UTC`` when the
        computer doesn't say
    """
    if "/" in (tz := os.environ.get("TZ", "").lstrip(":")):
        return tz
    target = os.path.realpath("/etc/localtime")
    return target.split("zoneinfo/", 1)[1] if "zoneinfo/" in target else "Etc/UTC"


def main() -> int:
    """Command-line entry point.

    :return: Process exit code
    """
    args = parse_args(sys.argv[1:])
    summary = {
        "dest": str(args.dest.resolve()),
        "time_zone": local_time_zone(),
        **report(args.dest),
    }
    print(json.dumps(summary, indent=2))
    return 1 if "error" in summary else 0


if __name__ == "__main__":
    sys.exit(main())
