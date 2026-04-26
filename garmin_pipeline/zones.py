"""Zone definitions and resolver — loads zones.yaml and resolves zone references."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Zone config models
# ---------------------------------------------------------------------------


class HRZone(BaseModel):
    min: int
    max: int


class PaceZone(BaseModel):
    """Pace zone in min/km format."""

    min: str  # "4:10" (faster pace = lower min/km)
    max: str  # "4:30" (slower pace = higher min/km)


class PowerZone(BaseModel):
    """Power zone as percentage of FTP."""

    min_pct: float
    max_pct: float


class RunningZones(BaseModel):
    hr_zones: dict[str, HRZone] = {}
    pace_zones: dict[str, PaceZone] = {}


class CyclingZones(BaseModel):
    ftp: int = 0
    power_zones: dict[str, PowerZone] = {}


class ZoneConfig(BaseModel):
    updated: str | None = None
    running: RunningZones = RunningZones()
    cycling: CyclingZones = CyclingZones()


# ---------------------------------------------------------------------------
# Garmin target type constants
# ---------------------------------------------------------------------------

NO_TARGET: dict[str, Any] = {
    "workoutTargetTypeId": 1,
    "workoutTargetTypeKey": "no.target",
    "displayOrder": 1,
}

HR_TARGET_TYPE: dict[str, Any] = {
    "workoutTargetTypeId": 4,
    "workoutTargetTypeKey": "heart.rate.zone",
    "displayOrder": 4,
}

SPEED_TARGET_TYPE: dict[str, Any] = {
    "workoutTargetTypeId": 5,
    "workoutTargetTypeKey": "speed.zone",
    "displayOrder": 5,
}

PACE_TARGET_TYPE: dict[str, Any] = {
    "workoutTargetTypeId": 6,
    "workoutTargetTypeKey": "pace.zone",
    "displayOrder": 6,
}

POWER_TARGET_TYPE: dict[str, Any] = {
    "workoutTargetTypeId": 2,
    "workoutTargetTypeKey": "power.zone",
    "displayOrder": 2,
}


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


METERS_PER_MILE = 1609.344


def pace_to_mps(pace_str: str) -> float:
    """Convert pace string to meters per second.

    Supports both per-km and per-mile:
        "5:00"      → min/km (default) → 1000m / 300s = 3.333 m/s
        "5:00/km"   → explicit min/km
        "7:00/mi"   → min/mile → 1609.344m / 420s = 3.832 m/s
    """
    raw = pace_str.strip()

    if raw.endswith("/mi"):
        distance = METERS_PER_MILE
        raw = raw[:-3].strip()
    elif raw.endswith("/km"):
        distance = 1000.0
        raw = raw[:-3].strip()
    else:
        distance = 1000.0  # default: min/km

    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid pace format: '{pace_str}'. Expected 'M:SS', 'M:SS/mi', or 'M:SS/km'."
        )
    minutes = int(parts[0])
    seconds = int(parts[1])
    total_seconds = minutes * 60 + seconds
    if total_seconds == 0:
        raise ValueError("Pace cannot be zero.")
    return distance / total_seconds


# ---------------------------------------------------------------------------
# Zone resolver
# ---------------------------------------------------------------------------


def load_zones(path: Path) -> ZoneConfig:
    """Load zones from a YAML file."""
    raw = yaml.safe_load(path.read_text())
    if raw is None:
        return ZoneConfig()
    return ZoneConfig.model_validate(raw)


def resolve_zone(
    sport_type: str,
    zone_name: str,
    zone_config: ZoneConfig,
    target_type_override: str | None = None,
) -> dict[str, Any]:
    """Resolve a zone reference to a Garmin target specification.

    Args:
        sport_type: "running", "cycling", etc.
        zone_name: Zone reference from YAML, e.g. "z2", "threshold".
        zone_config: Loaded zone configuration.
        target_type_override: Force a target type ("heart_rate", "pace", "power").

    Returns:
        Dict with targetType, targetValueOne, targetValueTwo for Garmin API.

    Raises:
        KeyError: If zone name not found in config.
    """
    if sport_type == "running":
        return _resolve_running_zone(zone_name, zone_config.running, target_type_override)
    if sport_type == "cycling":
        return _resolve_cycling_zone(zone_name, zone_config.cycling)
    # Strength and other types have no zone targets
    return {"targetType": NO_TARGET, "targetValueOne": None, "targetValueTwo": None}


def _resolve_running_zone(
    zone_name: str,
    zones: RunningZones,
    target_type_override: str | None,
) -> dict[str, Any]:
    """Resolve a running zone — prefer pace, fallback to HR."""
    # Explicit HR override
    if target_type_override == "heart_rate" and zone_name in zones.hr_zones:
        z = zones.hr_zones[zone_name]
        return {
            "targetType": HR_TARGET_TYPE,
            "targetValueOne": float(z.min),
            "targetValueTwo": float(z.max),
        }

    # Default: try pace zones first
    if zone_name in zones.pace_zones:
        z = zones.pace_zones[zone_name]
        # Garmin pace target: values are still in m/s internally
        # min pace (faster) → higher m/s = targetValueTwo
        # max pace (slower) → lower m/s = targetValueOne
        speed_low = pace_to_mps(z.max)  # slower pace = lower speed
        speed_high = pace_to_mps(z.min)  # faster pace = higher speed
        return {
            "targetType": PACE_TARGET_TYPE,
            "targetValueOne": speed_low,
            "targetValueTwo": speed_high,
        }

    # Fallback: HR zones
    if zone_name in zones.hr_zones:
        z = zones.hr_zones[zone_name]
        return {
            "targetType": HR_TARGET_TYPE,
            "targetValueOne": float(z.min),
            "targetValueTwo": float(z.max),
        }

    available = sorted(set(list(zones.pace_zones.keys()) + list(zones.hr_zones.keys())))
    raise KeyError(f"Unknown running zone '{zone_name}'. Available: {available}")


def _resolve_cycling_zone(
    zone_name: str,
    zones: CyclingZones,
) -> dict[str, Any]:
    """Resolve a cycling zone against FTP."""
    if zone_name not in zones.power_zones:
        available = sorted(zones.power_zones.keys())
        raise KeyError(f"Unknown cycling zone '{zone_name}'. Available: {available}")

    z = zones.power_zones[zone_name]
    ftp = zones.ftp
    return {
        "targetType": POWER_TARGET_TYPE,
        "targetValueOne": ftp * z.min_pct / 100.0,
        "targetValueTwo": ftp * z.max_pct / 100.0,
    }
