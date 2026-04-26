"""Compiler — transforms Workout models into raw Garmin API JSON dicts.

Bypasses python-garminconnect's typed workout models (too limited for strength
exercises) and constructs the JSON payload directly for upload_workout().
"""

from __future__ import annotations

from typing import Any

from garmin_pipeline.exercises import lookup_exercise
from garmin_pipeline.models import (
    LAP_BUTTON,
    BikeStep,
    CircuitGroup,
    CooldownStep,
    ExerciseStep,
    RecoveryStep,
    RestStep,
    RunStep,
    Step,
    WarmupStep,
    Workout,
    parse_distance_meters,
    parse_duration_seconds,
)
from garmin_pipeline.zones import (
    HR_TARGET_TYPE,
    NO_TARGET,
    PACE_TARGET_TYPE,
    POWER_TARGET_TYPE,
    ZoneConfig,
    pace_to_mps,
    resolve_zone,
)

# ---------------------------------------------------------------------------
# Garmin API constants
# ---------------------------------------------------------------------------

REPS_CONDITION: dict[str, Any] = {
    "conditionTypeId": 10,
    "conditionTypeKey": "reps",
    "displayOrder": 10,
    "displayable": True,
}

LAP_BUTTON_CONDITION: dict[str, Any] = {
    "conditionTypeId": 1,
    "conditionTypeKey": "lap.button",
    "displayOrder": 1,
    "displayable": True,
}

TIME_CONDITION: dict[str, Any] = {
    "conditionTypeId": 2,
    "conditionTypeKey": "time",
    "displayOrder": 2,
    "displayable": True,
}

DISTANCE_CONDITION: dict[str, Any] = {
    "conditionTypeId": 3,
    "conditionTypeKey": "distance",
    "displayOrder": 3,
    "displayable": True,
}

ITERATIONS_CONDITION: dict[str, Any] = {
    "conditionTypeId": 7,
    "conditionTypeKey": "iterations",
    "displayOrder": 7,
    "displayable": False,
}

POUND_UNIT: dict[str, Any] = {
    "unitId": 9,
    "unitKey": "pound",
    "factor": 453.59237,
}

DEFAULT_STROKE: dict[str, Any] = {
    "strokeTypeId": 0,
    "strokeTypeKey": None,
    "displayOrder": 0,
}

DEFAULT_EQUIPMENT: dict[str, Any] = {
    "equipmentTypeId": 0,
    "equipmentTypeKey": None,
    "displayOrder": 0,
}

# Step type dicts
STEP_WARMUP: dict[str, Any] = {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1}
STEP_COOLDOWN: dict[str, Any] = {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2}
STEP_INTERVAL: dict[str, Any] = {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3}
STEP_RECOVERY: dict[str, Any] = {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4}
STEP_REST: dict[str, Any] = {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5}
STEP_REPEAT: dict[str, Any] = {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6}

# Sport type mappings
SPORT_TYPES: dict[str, dict[str, Any]] = {
    "strength": {"sportTypeId": 6, "sportTypeKey": "cardio_training", "displayOrder": 6},
    "running": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
    "cycling": {"sportTypeId": 2, "sportTypeKey": "cycling", "displayOrder": 2},
    "swimming": {"sportTypeId": 4, "sportTypeKey": "swimming", "displayOrder": 4},
    "walking": {"sportTypeId": 4, "sportTypeKey": "walking", "displayOrder": 4},
    "hiking": {"sportTypeId": 7, "sportTypeKey": "hiking", "displayOrder": 7},
    "multi_sport": {"sportTypeId": 5, "sportTypeKey": "multi_sport", "displayOrder": 5},
}

# Default endConditionValue for lap.button steps (observed Garmin default)
LAP_BUTTON_DEFAULT_VALUE = 10.0


# ---------------------------------------------------------------------------
# Compiler state
# ---------------------------------------------------------------------------


class _CompilerState:
    """Mutable state threaded through compilation."""

    def __init__(self) -> None:
        self._step_order = 0
        self._child_step_id_counter = 0

    def next_step_order(self) -> int:
        self._step_order += 1
        return self._step_order

    def next_child_step_id(self) -> int:
        self._child_step_id_counter += 1
        return self._child_step_id_counter


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compile_workout(
    workout: Workout,
    zone_config: ZoneConfig | None = None,
) -> dict[str, Any]:
    """Compile a Workout model into a Garmin API JSON dict.

    Args:
        workout: Parsed workout model.
        zone_config: Optional zone configuration for resolving zone references.

    Returns:
        Dict ready for upload via garminconnect.Garmin.upload_workout().
    """
    state = _CompilerState()
    sport_type = SPORT_TYPES.get(workout.type.value)
    if sport_type is None:
        raise ValueError(f"Unsupported sport type: {workout.type.value}")

    steps = [
        _compile_step(step, state, workout.type.value, zone_config, parent_child_id=None)
        for step in workout.steps
    ]

    result: dict[str, Any] = {
        "workoutName": workout.name,
        "sportType": sport_type,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": sport_type,
                "workoutSteps": steps,
            }
        ],
        "estimatedDurationInSecs": 0,
        "estimatedDistanceInMeters": 0.0,
    }

    if workout.description:
        result["description"] = workout.description

    return result


# ---------------------------------------------------------------------------
# Step dispatch
# ---------------------------------------------------------------------------


def _compile_step(
    step: Step,
    state: _CompilerState,
    sport_type: str,
    zone_config: ZoneConfig | None,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Dispatch to the appropriate step compiler."""
    if isinstance(step, ExerciseStep):
        return _compile_exercise_step(step, state, parent_child_id)
    if isinstance(step, RestStep):
        return _compile_rest_step(step, state, parent_child_id)
    if isinstance(step, RunStep):
        return _compile_run_step(step, state, sport_type, zone_config, parent_child_id)
    if isinstance(step, BikeStep):
        return _compile_bike_step(step, state, sport_type, zone_config, parent_child_id)
    if isinstance(step, WarmupStep):
        return _compile_warmup_step(step, state, sport_type, zone_config, parent_child_id)
    if isinstance(step, CooldownStep):
        return _compile_cooldown_step(step, state, sport_type, zone_config, parent_child_id)
    if isinstance(step, RecoveryStep):
        return _compile_recovery_step(step, state, sport_type, zone_config, parent_child_id)
    if isinstance(step, CircuitGroup):
        return _compile_circuit(step, state, sport_type, zone_config, parent_child_id)
    raise ValueError(f"Unknown step type: {type(step)}")


# ---------------------------------------------------------------------------
# Individual step compilers
# ---------------------------------------------------------------------------


def _base_executable_step(
    step_order: int,
    step_type: dict[str, Any],
    child_step_id: int | None,
) -> dict[str, Any]:
    """Build a base ExecutableStepDTO with common fields."""
    return {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": step_type,
        "childStepId": child_step_id,
        "description": None,
        "targetType": NO_TARGET,
        "targetValueOne": None,
        "targetValueTwo": None,
        "targetValueUnit": None,
        "zoneNumber": None,
        "secondaryTargetType": None,
        "secondaryTargetValueOne": None,
        "secondaryTargetValueTwo": None,
        "secondaryTargetValueUnit": None,
        "secondaryZoneNumber": None,
        "endConditionZone": None,
        "preferredEndConditionUnit": None,
        "endConditionCompare": None,
        "strokeType": DEFAULT_STROKE,
        "equipmentType": DEFAULT_EQUIPMENT,
        "category": None,
        "exerciseName": None,
        "weightValue": None,
        "weightUnit": None,
    }


def _apply_end_condition_duration(
    step: dict[str, Any],
    duration: str | None,
) -> None:
    """Set end condition based on a duration string ("M:SS" or "lap")."""
    if duration is None or duration == LAP_BUTTON:
        step["endCondition"] = LAP_BUTTON_CONDITION
        step["endConditionValue"] = LAP_BUTTON_DEFAULT_VALUE
    else:
        step["endCondition"] = TIME_CONDITION
        step["endConditionValue"] = parse_duration_seconds(duration)


def _apply_exercise(step: dict[str, Any], exercise_name: str | None) -> None:
    """Set category and exerciseName from the exercise registry."""
    if exercise_name is None:
        return
    exercise_def = lookup_exercise(exercise_name)
    step["category"] = exercise_def.category
    step["exerciseName"] = exercise_def.exercise_name


def _apply_weight(step: dict[str, Any], weight: float | None) -> None:
    """Set weight fields in lbs."""
    if weight is not None:
        step["weightValue"] = weight
        step["weightUnit"] = POUND_UNIT


def _apply_zone_target(
    step: dict[str, Any],
    zone_name: str | None,
    sport_type: str,
    zone_config: ZoneConfig | None,
) -> None:
    """Resolve a zone reference and set target fields."""
    if zone_name is None or zone_config is None:
        return
    resolved = resolve_zone(sport_type, zone_name, zone_config)
    step["targetType"] = resolved["targetType"]
    step["targetValueOne"] = resolved.get("targetValueOne")
    step["targetValueTwo"] = resolved.get("targetValueTwo")


def _compile_exercise_step(
    step: ExerciseStep,
    state: _CompilerState,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a strength/cardio exercise step."""
    result = _base_executable_step(state.next_step_order(), STEP_INTERVAL, parent_child_id)
    result["description"] = step.notes

    _apply_exercise(result, step.exercise)
    _apply_weight(result, step.weight)

    if step.reps is not None:
        result["endCondition"] = REPS_CONDITION
        result["endConditionValue"] = float(step.reps)
    else:
        _apply_end_condition_duration(result, step.duration)

    return result


def _compile_rest_step(
    step: RestStep,
    state: _CompilerState,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a rest step."""
    result = _base_executable_step(state.next_step_order(), STEP_REST, parent_child_id)
    result["endCondition"] = TIME_CONDITION
    result["endConditionValue"] = parse_duration_seconds(step.duration)
    return result


def _compile_run_step(
    step: RunStep,
    state: _CompilerState,
    sport_type: str,
    zone_config: ZoneConfig | None,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a running interval step."""
    result = _base_executable_step(state.next_step_order(), STEP_INTERVAL, parent_child_id)
    result["description"] = step.notes

    # End condition: distance or duration
    if step.distance is not None:
        result["endCondition"] = DISTANCE_CONDITION
        result["endConditionValue"] = parse_distance_meters(step.distance)
    else:
        _apply_end_condition_duration(result, step.duration)

    # Target: explicit HR/pace override or zone reference
    if step.hr is not None:
        result["targetType"] = HR_TARGET_TYPE
        result["targetValueOne"] = step.hr["min"]
        result["targetValueTwo"] = step.hr["max"]
    elif step.pace is not None:
        result["targetType"] = PACE_TARGET_TYPE
        result["targetValueOne"] = pace_to_mps(step.pace["max"])  # slower = lower speed
        result["targetValueTwo"] = pace_to_mps(step.pace["min"])  # faster = higher speed
    elif step.zone is not None:
        _apply_zone_target(result, step.zone, sport_type, zone_config)

    return result


def _compile_bike_step(
    step: BikeStep,
    state: _CompilerState,
    sport_type: str,
    zone_config: ZoneConfig | None,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a cycling interval step."""
    result = _base_executable_step(state.next_step_order(), STEP_INTERVAL, parent_child_id)

    if step.distance is not None:
        result["endCondition"] = DISTANCE_CONDITION
        result["endConditionValue"] = parse_distance_meters(step.distance)
    else:
        _apply_end_condition_duration(result, step.duration)

    if step.power is not None:
        result["targetType"] = POWER_TARGET_TYPE
        result["targetValueOne"] = step.power["min"]
        result["targetValueTwo"] = step.power["max"]
    elif step.power_pct is not None:
        if zone_config is None:
            raise ValueError("power_pct requires zones.yaml with FTP defined")
        ftp = zone_config.cycling.ftp
        result["targetType"] = POWER_TARGET_TYPE
        result["targetValueOne"] = ftp * step.power_pct["min"] / 100.0
        result["targetValueTwo"] = ftp * step.power_pct["max"] / 100.0
    elif step.zone is not None:
        _apply_zone_target(result, step.zone, sport_type, zone_config)

    return result


def _compile_warmup_step(
    step: WarmupStep,
    state: _CompilerState,
    sport_type: str,
    zone_config: ZoneConfig | None,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a warmup step."""
    result = _base_executable_step(state.next_step_order(), STEP_WARMUP, parent_child_id)
    result["description"] = step.notes

    _apply_end_condition_duration(result, step.duration)
    _apply_exercise(result, step.exercise)
    _apply_zone_target(result, step.zone, sport_type, zone_config)

    return result


def _compile_cooldown_step(
    step: CooldownStep,
    state: _CompilerState,
    sport_type: str,
    zone_config: ZoneConfig | None,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a cooldown step."""
    result = _base_executable_step(state.next_step_order(), STEP_COOLDOWN, parent_child_id)
    result["description"] = step.notes

    _apply_end_condition_duration(result, step.duration)
    _apply_exercise(result, step.exercise)
    _apply_zone_target(result, step.zone, sport_type, zone_config)

    return result


def _compile_recovery_step(
    step: RecoveryStep,
    state: _CompilerState,
    sport_type: str,
    zone_config: ZoneConfig | None,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a recovery step."""
    result = _base_executable_step(state.next_step_order(), STEP_RECOVERY, parent_child_id)

    if step.distance is not None:
        result["endCondition"] = DISTANCE_CONDITION
        result["endConditionValue"] = parse_distance_meters(step.distance)
    else:
        _apply_end_condition_duration(result, step.duration)

    _apply_zone_target(result, step.zone, sport_type, zone_config)

    return result


def _compile_circuit(
    step: CircuitGroup,
    state: _CompilerState,
    sport_type: str,
    zone_config: ZoneConfig | None,
    parent_child_id: int | None,
) -> dict[str, Any]:
    """Compile a repeat group / circuit."""
    child_id = state.next_child_step_id()
    group_order = state.next_step_order()

    child_steps = [
        _compile_step(s, state, sport_type, zone_config, parent_child_id=child_id)
        for s in step.steps
    ]

    result: dict[str, Any] = {
        "type": "RepeatGroupDTO",
        "stepOrder": group_order,
        "stepType": STEP_REPEAT,
        "childStepId": child_id,
        "numberOfIterations": step.iterations,
        "workoutSteps": child_steps,
        "endCondition": ITERATIONS_CONDITION,
        "endConditionValue": float(step.iterations),
        "smartRepeat": False,
    }

    if step.skip_last_rest is not None:
        result["skipLastRestStep"] = step.skip_last_rest

    return result
