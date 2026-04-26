"""CLI entry point for the Garmin workout pipeline."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

from garmin_pipeline.compiler import compile_workout
from garmin_pipeline.loader import load_workout
from garmin_pipeline.zones import load_zones

load_dotenv()

DEFAULT_ZONES = Path("workouts/zones.yaml")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """gwp — Garmin Workout Pipeline."""
    _setup_logging(verbose)


@cli.command()
@click.argument("workout_file", type=click.Path(exists=True, path_type=Path))
@click.option("--zones", "zones_file", type=click.Path(path_type=Path), default=None)
@click.option("--dry-run", is_flag=True, help="Compile and print JSON without uploading.")
@click.option("--schedule", "schedule_date", default=None, help="Schedule date (YYYY-MM-DD).")
def push(
    workout_file: Path,
    zones_file: Path | None,
    dry_run: bool,
    schedule_date: str | None,
) -> None:
    """Compile and upload a workout to Garmin Connect."""
    zone_config = None
    zones_path = zones_file or DEFAULT_ZONES
    if zones_path.exists():
        zone_config = load_zones(zones_path)

    workout = load_workout(workout_file)
    compiled = compile_workout(workout, zone_config)

    if dry_run:
        click.echo(json.dumps(compiled, indent=2))
        return

    from garmin_pipeline.sync import GarminSync

    sync = GarminSync()
    sync.login()
    workout_id = sync.sync_workout(compiled, schedule_date)
    click.echo(f"Uploaded workout '{workout.name}' (ID: {workout_id})")
    if schedule_date:
        click.echo(f"Scheduled for {schedule_date}")


@cli.command()
@click.argument("workout_file", type=click.Path(exists=True, path_type=Path))
@click.option("--zones", "zones_file", type=click.Path(path_type=Path), default=None)
def validate(workout_file: Path, zones_file: Path | None) -> None:
    """Validate a workout YAML and print compiled JSON."""
    zone_config = None
    zones_path = zones_file or DEFAULT_ZONES
    if zones_path.exists():
        zone_config = load_zones(zones_path)

    workout = load_workout(workout_file)
    compiled = compile_workout(workout, zone_config)
    click.echo(json.dumps(compiled, indent=2))
    click.echo(f"\nValid: '{workout.name}' ({len(workout.steps)} top-level steps)", err=True)


@cli.command(name="sync")
@click.argument("schedule_file", type=click.Path(exists=True, path_type=Path))
@click.option("--zones", "zones_file", type=click.Path(path_type=Path), default=None)
@click.option("--dry-run", is_flag=True, help="Compile and validate without uploading.")
def sync_schedule(
    schedule_file: Path,
    zones_file: Path | None,
    dry_run: bool,
) -> None:
    """Deploy a weekly schedule to Garmin Connect."""
    zone_config = None
    zones_path = zones_file or DEFAULT_ZONES
    if zones_path.exists():
        zone_config = load_zones(zones_path)

    raw = yaml.safe_load(schedule_file.read_text())
    week_str = raw.get("week", "")

    # Parse ISO week to get Monday date
    monday = datetime.strptime(week_str + "-1", "%G-W%V-%u").date()

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    templates_dir = schedule_file.parent.parent / "templates"

    if not dry_run:
        from garmin_pipeline.sync import GarminSync

        garmin_sync = GarminSync()
        garmin_sync.login()

    for i, day_name in enumerate(days):
        date = monday + timedelta(days=i)
        date_str = date.isoformat()
        entries = raw.get(day_name, [])

        if not entries:
            continue

        for entry in entries:
            if entry == "rest":
                click.echo(f"{date_str} ({day_name}): rest day")
                continue

            template_name = entry.get("template", "")
            template_path = templates_dir / f"{template_name}.yaml"

            if not template_path.exists():
                click.echo(f"ERROR: Template not found: {template_path}", err=True)
                continue

            workout = load_workout(template_path)

            # Apply overrides
            overrides = entry.get("overrides", {})
            if "name" in overrides:
                workout = workout.model_copy(update={"name": overrides["name"]})

            compiled = compile_workout(workout, zone_config)

            if dry_run:
                click.echo(f"{date_str} ({day_name}): {workout.name} [valid]")
            else:
                workout_id = garmin_sync.sync_workout(compiled, date_str)  # type: ignore[possibly-undefined]
                click.echo(f"{date_str} ({day_name}): {workout.name} (ID: {workout_id})")


@cli.command(name="list")
def list_workouts() -> None:
    """List all workouts on Garmin Connect."""
    from garmin_pipeline.sync import GarminSync

    sync = GarminSync()
    sync.login()
    workouts = sync.list_workouts()

    if not workouts:
        click.echo("No workouts found.")
        return

    for w in workouts:
        sport = w.get("sportType", {}).get("sportTypeKey", "unknown")
        click.echo(f"  {w['workoutId']}  {w['workoutName']:<40s}  [{sport}]")


@cli.command()
@click.argument("workout_id", type=int)
def delete(workout_id: int) -> None:
    """Delete a workout from Garmin Connect."""
    from garmin_pipeline.sync import GarminSync

    sync = GarminSync()
    sync.login()
    sync.delete(workout_id)
    click.echo(f"Deleted workout {workout_id}")


@cli.command()
@click.option("--zones", "zones_file", type=click.Path(exists=True, path_type=Path), default=None)
def zones(zones_file: Path | None) -> None:
    """Show resolved training zones."""
    zones_path = zones_file or DEFAULT_ZONES
    if not zones_path.exists():
        click.echo(f"Zones file not found: {zones_path}", err=True)
        return

    zone_config = load_zones(zones_path)
    click.echo(json.dumps(zone_config.model_dump(), indent=2))


if __name__ == "__main__":
    cli()
