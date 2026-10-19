"""
CLI Commands
============
Flask CLI commands for administrative tasks.

Usage:
    flask sync-jobs           # Sync jobs from Remotive API
    flask sync-jobs --clear   # Clear existing and sync fresh
    flask job-status          # Show job sync status
"""

import click
from flask import current_app
from flask.cli import with_appcontext

from src.services.job_sync_service import JobSyncService
from src.services.remotive_client import RemotiveAPIError


@click.command("sync-jobs")
@click.option(
    "--clear",
    is_flag=True,
    default=False,
    help="Clear existing Remotive jobs before syncing",
)
@click.option(
    "--category",
    default=None,
    help="Filter by category (e.g., software-dev, devops, data)",
)
@with_appcontext
def sync_jobs_command(clear, category):
    """
    Sync jobs from Remotive API to the database.

    This command fetches IT/tech job listings from Remotive and stores
    them in the local database. Jobs no longer in the API are soft-deleted.

    Examples:
        flask sync-jobs                      # Sync all jobs
        flask sync-jobs --clear              # Clear and sync fresh
        flask sync-jobs --category=devops    # Sync only DevOps jobs
    """
    click.echo("=" * 50)
    click.echo("Remotive Job Sync")
    click.echo("=" * 50)

    if clear:
        click.echo("Mode: Clear existing jobs and sync fresh")
    else:
        click.echo("Mode: Upsert (update existing, add new)")

    if category:
        click.echo(f"Category filter: {category}")

    click.echo("-" * 50)
    click.echo("Fetching jobs from Remotive API...")

    try:
        stats = JobSyncService.sync_from_remotive(clear_existing=clear, category=category)

        click.echo("-" * 50)
        click.echo("Sync completed successfully!")
        click.echo("-" * 50)
        click.echo(f"Jobs fetched from API:  {stats.jobs_fetched}")
        click.echo(f"New jobs created:       {stats.jobs_created}")
        click.echo(f"Existing jobs updated:  {stats.jobs_updated}")
        click.echo(f"Stale jobs deactivated: {stats.jobs_deactivated}")
        click.echo(f"Jobs skipped (errors):  {stats.jobs_skipped}")
        click.echo(f"Processing errors:      {stats.errors}")
        click.echo("-" * 50)
        click.echo(f"Total active jobs:      {stats.total_active}")
        click.echo("=" * 50)

    except RemotiveAPIError as e:
        click.echo(f"ERROR: Failed to fetch jobs from Remotive API", err=True)
        click.echo(f"Details: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"ERROR: Sync failed", err=True)
        click.echo(f"Details: {e}", err=True)
        current_app.logger.exception("Job sync failed")
        raise SystemExit(1)


@click.command("job-status")
@with_appcontext
def job_status_command():
    """
    Show current job data status.

    Displays counts of jobs by source and last sync time.
    """
    click.echo("=" * 50)
    click.echo("Job Data Status")
    click.echo("=" * 50)

    try:
        status = JobSyncService.get_sync_status()

        click.echo(f"Total jobs in database: {status['total_jobs']}")
        click.echo(f"Active jobs:            {status['active_jobs']}")
        click.echo("-" * 50)
        click.echo("By source:")

        for source, data in status["sources"].items():
            click.echo(f"  {source}:")
            click.echo(f"    Total:  {data['total']}")
            click.echo(f"    Active: {data['active']}")
            if data.get("last_sync_at"):
                click.echo(f"    Last sync: {data['last_sync_at']}")

        click.echo("=" * 50)

    except Exception as e:
        click.echo(f"ERROR: Failed to get job status", err=True)
        click.echo(f"Details: {e}", err=True)
        raise SystemExit(1)


def register_cli_commands(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(sync_jobs_command)
    app.cli.add_command(job_status_command)
