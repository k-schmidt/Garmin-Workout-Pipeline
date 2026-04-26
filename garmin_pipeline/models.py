"""Pydantic data models for parsed YAML workout definitions."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SportType(Enum):
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH = "strength"
    MULTI_SPORT = "multi_sport"
    WALKING = "walking"
    HIKING = "hiking"


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^(?:(?P<hours>\d+):)?(?P<minutes>\d+):(?P<seconds>\d{2})$")

LAP_BUTTON = "lap"


def parse_duration_seconds(value: str) -> float:
    """Parse a duration string to seconds.

    Formats:
        "2:00"     → 120.0
        "0:45"     → 45.0
        "1:30:00"  → 5400.0
        "30"       → 30.0

    Raises:
        ValueError: If format is unrecognized.
    """
    m = _DURATION_RE.match(value)
    if m:
        hours = int(m.group("hours") or 0)
        minutes = int(m.group("minutes"))
        seconds = int(m.group("seconds"))
        return float(hours * 3600 + minutes * 60 + seconds)
    if value.isdigit():
        return float(value)
    raise ValueError(f"Invalid duration format: '{value}'. Expected 'M:SS', 'H:MM:SS', or seconds.")


def parse_distance_meters(value: str) -> float:
    """Parse a distance string to meters.

    Formats:
        "1km"    → 1000.0
        "1000m"  → 1000.0
        "1mi"    → 1609.34
        "400"    → 400.0 (assumed meters)

    Raises:
        ValueError: If format is unrecognized.
    """
    value = value.strip().lower()
    if value.endswith("km"):
        return float(value[:-2]) * 1000
    if value.endswith("mi"):
        return float(value[:-2]) * 1609.34
    if value.endswith("m"):
        return float(value[:-1])
    if value.replace(".", "").isdigit():
        return float(value)
    raise ValueError(
        f"Invalid distance format: '{value}'. Expected '1km', '1000m', '1mi', or meters."
    )


# ---------------------------------------------------------------------------
# Step models — represent parsed YAML, NOT Garmin API format
# ---------------------------------------------------------------------------


class ExerciseStep(BaseModel):
    """A strength/cardio exercise step: { exercise: wall_ball, reps: 20, weight: 13 }"""

    step_kind: Literal["exercise"] = "exercise"
    exercise: str
    duration: str | None = None  # "M:SS" or "lap"
    reps: int | None = None
    weight: float | None = None  # lbs
    notes: str | None = None

    @field_validator("exercise")
    @classmethod
    def _normalize_exercise(cls, v: str) -> str:
        return v.strip().lower()


class RestStep(BaseModel):
    """A rest step: { rest: "2:00" }"""

    step_kind: Literal["rest"] = "rest"
    duration: str


class RunStep(BaseModel):
    """A running interval: run: { duration: "5:00", zone: threshold }"""

    step_kind: Literal["run"] = "run"
    duration: str | None = None
    distance: str | None = None
    zone: str | None = None
    hr: dict[str, float] | None = None
    pace: dict[str, str] | None = None
    notes: str | None = None


class BikeStep(BaseModel):
    """A cycling interval: bike: { duration: "20:00", zone: tempo }"""

    step_kind: Literal["bike"] = "bike"
    duration: str | None = None
    distance: str | None = None
    zone: str | None = None
    power: dict[str, float] | None = None
    power_pct: dict[str, float] | None = None


class WarmupStep(BaseModel):
    """Warmup step — strength (with exercise) or cardio (with zone)."""

    step_kind: Literal["warmup"] = "warmup"
    exercise: str | None = None
    duration: str = LAP_BUTTON
    zone: str | None = None
    notes: str | None = None


class CooldownStep(BaseModel):
    """Cooldown step."""

    step_kind: Literal["cooldown"] = "cooldown"
    exercise: str | None = None
    duration: str = LAP_BUTTON
    zone: str | None = None
    notes: str | None = None


class RecoveryStep(BaseModel):
    """Recovery interval between work sets."""

    step_kind: Literal["recovery"] = "recovery"
    duration: str = LAP_BUTTON
    distance: str | None = None
    zone: str | None = None


class CircuitGroup(BaseModel):
    """Repeat group / circuit: circuit: 4, steps: [...]"""

    step_kind: Literal["circuit"] = "circuit"
    iterations: int
    skip_last_rest: bool | None = None
    steps: list[Step]


# Union of all step types
Step = Annotated[
    ExerciseStep
    | RestStep
    | RunStep
    | BikeStep
    | WarmupStep
    | CooldownStep
    | RecoveryStep
    | CircuitGroup,
    Field(discriminator="step_kind"),
]

# Rebuild CircuitGroup to resolve the forward reference
CircuitGroup.model_rebuild()


# ---------------------------------------------------------------------------
# Top-level workout model
# ---------------------------------------------------------------------------


class Workout(BaseModel):
    """Top-level workout definition parsed from YAML."""

    name: str
    type: SportType
    steps: list[Step]
    description: str | None = None


# ---------------------------------------------------------------------------
# YAML dict → Step parser (discriminator by dict keys)
# ---------------------------------------------------------------------------


def parse_step(raw: dict) -> Step:  # type: ignore[type-arg]
    """Parse a raw YAML dict into the appropriate Step model.

    Dispatches based on which keys are present in the dict.
    """
    # Circuit / repeat group
    if "circuit" in raw:
        child_steps = [parse_step(s) for s in raw.get("steps", [])]
        return CircuitGroup(
            iterations=int(raw["circuit"]),
            skip_last_rest=raw.get("skip_last_rest"),
            steps=child_steps,
        )
    if "repeat" in raw:
        child_steps = [parse_step(s) for s in raw.get("steps", [])]
        return CircuitGroup(
            iterations=int(raw["repeat"]),
            skip_last_rest=raw.get("skip_last_rest"),
            steps=child_steps,
        )

    # Warmup — can be dict value or inline
    if "warmup" in raw:
        val = raw["warmup"]
        if isinstance(val, dict):
            return WarmupStep(**val)
        return WarmupStep()

    # Cooldown
    if "cooldown" in raw:
        val = raw["cooldown"]
        if isinstance(val, dict):
            return CooldownStep(**val)
        return CooldownStep()

    # Recovery
    if "recovery" in raw:
        val = raw["recovery"]
        if isinstance(val, dict):
            return RecoveryStep(**val)
        return RecoveryStep(duration=str(val))

    # Rest — value is the duration string
    if "rest" in raw:
        val = raw["rest"]
        if isinstance(val, dict):
            return RestStep(duration=val["duration"])
        return RestStep(duration=str(val))

    # Run step
    if "run" in raw:
        val = raw["run"]
        if isinstance(val, dict):
            return RunStep(**val)
        return RunStep()

    # Bike step
    if "bike" in raw:
        val = raw["bike"]
        if isinstance(val, dict):
            return BikeStep(**val)
        return BikeStep()

    # Exercise step (strength/cardio) — two YAML forms:
    #   1. Wrapper: - exercise: { exercise: cardio, duration: lap, notes: "..." }
    #   2. Flat:    - { exercise: wall_ball, reps: 20, weight: 13 }
    if "exercise" in raw:
        val = raw["exercise"]
        if isinstance(val, dict):
            return ExerciseStep(**val)
        return ExerciseStep(
            exercise=val,
            duration=raw.get("duration"),
            reps=raw.get("reps"),
            weight=raw.get("weight"),
            notes=raw.get("notes"),
        )

    raise ValueError(f"Cannot parse step: unrecognized keys {set(raw.keys())}")
