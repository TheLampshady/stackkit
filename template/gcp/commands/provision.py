"""
Create the environment's cloud resources.

Names come from ``.env`` through the service settings:
stackkit:begin database
the ``NAMESPACE`` Firestore database,
stackkit:end database
stackkit:begin storage
the ``{PROJECT_ID}-{NAMESPACE}`` storage bucket.
stackkit:end storage
Each one is checked
first: one that exists is skipped, and the rest are created after one
confirmation unless ``--yes``. Declining exits non-zero so ``make provision``
stops before deploying rules and indexes to a database that is not there.
Safe to rerun.
"""

import logging
import subprocess
from dataclasses import dataclass
from typing import Annotated

import typer

logger = logging.getLogger(__name__)

DB_LOCATION = "nam5"
BUCKET_LOCATION = "us-central1"


@dataclass(frozen=True)
class Resource:
    """One cloud resource: how to name it, check it, and create it."""

    label: str
    describe: list[str]
    create: list[str]


def gcloud(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one gcloud command and capture its output.

    :param args: Arguments after ``gcloud``
    :return: The finished process
    :side effects: Calls Google Cloud through the gcloud CLI
    """
    return subprocess.run(
        ["gcloud", *args], capture_output=True, text=True, check=False
    )


def resources(project: str, database: str, bucket: str) -> list[Resource]:
    """The resources this environment needs.

    :param project: Google Cloud project id
    :param database: Firestore database id
    :param bucket: Storage bucket name
    :return: The resources, database first
    """
    scope = [f"--project={project}"]
    return [
        # stackkit:begin database
        Resource(
            label=f"Firestore database {database}",
            describe=["firestore", "databases", "describe", f"--database={database}"]
            + scope,
            create=[
                "firestore",
                "databases",
                "create",
                f"--database={database}",
                f"--location={DB_LOCATION}",
                "--type=firestore-native",
            ]
            + scope,
        ),
        # stackkit:end database
        # stackkit:begin storage
        Resource(
            label=f"Storage bucket gs://{bucket}",
            describe=["storage", "buckets", "describe", f"gs://{bucket}"] + scope,
            create=[
                "storage",
                "buckets",
                "create",
                f"gs://{bucket}",
                f"--location={BUCKET_LOCATION}",
            ]
            + scope,
        ),
        # stackkit:end storage
    ]


def provision(
    yes: Annotated[
        bool, typer.Option("--yes", help="Create missing resources without asking")
    ] = False,
) -> None:
    """Create the project's cloud resources, skipping any that exist."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from app_settings import settings

    if not settings.project_id or not settings.namespace:
        typer.echo("Set PROJECT_ID and NAMESPACE in .env first.")
        raise typer.Exit(1)

    missing: list[Resource] = []
    database = bucket = ""
    # stackkit:begin database
    database = settings.firestore_db_name or settings.namespace
    # stackkit:end database
    # stackkit:begin storage
    bucket = settings.firestore_bucket_name or ""
    # stackkit:end storage
    for resource in resources(settings.project_id, database, bucket):
        if gcloud(resource.describe).returncode == 0:
            typer.echo(f"{resource.label}: exists, skipped")
        else:
            missing.append(resource)

    if not missing:
        typer.echo("Nothing to create.")
        return

    names = ", ".join(r.label for r in missing)
    if not yes and not typer.confirm(
        f"Create {names} in {settings.project_id}?", default=False
    ):
        typer.echo("Nothing created.")
        raise typer.Exit(1)

    for resource in missing:
        result = gcloud(resource.create)
        if result.returncode != 0:
            typer.echo(f"{resource.label}: failed\n{result.stderr.strip()}")
            raise typer.Exit(1)
        logger.info("provision created=%s", resource.label)
        typer.echo(f"{resource.label}: created")
