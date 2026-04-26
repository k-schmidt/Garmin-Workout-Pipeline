"""Garmin Connect sync — auth, upload, schedule, list, delete."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from garminconnect import Garmin

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_DIR = Path.home() / ".garmin-workout-pipeline" / "tokens"


class GarminSync:
    """Manages workout sync with Garmin Connect."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        token_dir: Path = DEFAULT_TOKEN_DIR,
    ) -> None:
        self.email = email or os.environ.get("GARMIN_EMAIL", "")
        self.password = password or os.environ.get("GARMIN_PASSWORD", "")
        self.token_dir = token_dir

        if not self.email or not self.password:
            raise ValueError(
                "Garmin credentials required. Set GARMIN_EMAIL and GARMIN_PASSWORD "
                "environment variables or pass email/password arguments."
            )

        self.client = Garmin(self.email, self.password)

    def login(self) -> None:
        """Authenticate with Garmin Connect, using cached tokens if available."""
        self.token_dir.mkdir(parents=True, exist_ok=True)
        token_path = str(self.token_dir)
        logger.info("Logging in to Garmin Connect...")
        self.client.login(tokenstore=token_path)
        logger.info("Login successful.")

    def upload(self, workout_json: dict[str, Any]) -> int:
        """Upload a workout to Garmin Connect.

        Args:
            workout_json: Compiled workout dict (from compiler.compile_workout).

        Returns:
            Workout ID from Garmin Connect.
        """
        logger.info("Uploading workout: %s", workout_json.get("workoutName", "unnamed"))
        result = self.client.upload_workout(workout_json)
        workout_id: int = result["workoutId"]
        logger.info("Uploaded successfully. Workout ID: %d", workout_id)
        return workout_id

    def schedule(self, workout_id: int, date_str: str) -> None:
        """Schedule a workout to a specific date.

        Args:
            workout_id: Garmin workout ID.
            date_str: Date in YYYY-MM-DD format.
        """
        logger.info("Scheduling workout %d for %s", workout_id, date_str)
        self.client.schedule_workout(workout_id, date_str)
        logger.info("Scheduled successfully.")

    def list_workouts(self) -> list[dict[str, Any]]:
        """List all workouts on Garmin Connect."""
        return self.client.get_workouts()

    def delete(self, workout_id: int) -> None:
        """Delete a workout from Garmin Connect."""
        logger.info("Deleting workout %d", workout_id)
        self.client.delete_workout(workout_id)
        logger.info("Deleted successfully.")

    def sync_workout(
        self,
        workout_json: dict[str, Any],
        schedule_date: str | None = None,
    ) -> int:
        """Upload a workout, replacing any existing workout with the same name.

        Args:
            workout_json: Compiled workout dict.
            schedule_date: Optional date to schedule (YYYY-MM-DD).

        Returns:
            New workout ID.
        """
        name = workout_json.get("workoutName", "")
        existing = self.list_workouts()
        for w in existing:
            if w.get("workoutName") == name:
                logger.info("Replacing existing workout '%s' (ID: %s)", name, w["workoutId"])
                self.delete(w["workoutId"])

        workout_id = self.upload(workout_json)

        if schedule_date:
            self.schedule(workout_id, schedule_date)

        return workout_id
