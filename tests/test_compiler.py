"""Tests for the compiler — golden test against workout_detail.json."""

import json
from pathlib import Path

import pytest

from garmin_pipeline.compiler import compile_workout
from garmin_pipeline.loader import load_workout

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def hyrox_compiled() -> dict:
    workout = load_workout(FIXTURES / "hyrox-strength.yaml")
    return compile_workout(workout)


@pytest.fixture()
def golden_json() -> dict:
    return json.loads((FIXTURES / "workout_detail.json").read_text())


class TestCompilerGolden:
    """Verify compiled output matches the known-good Garmin API JSON structure."""

    def test_sport_type(self, hyrox_compiled: dict) -> None:
        assert hyrox_compiled["sportType"]["sportTypeId"] == 6
        assert hyrox_compiled["sportType"]["sportTypeKey"] == "cardio_training"

    def test_segment_sport_type(self, hyrox_compiled: dict) -> None:
        segment = hyrox_compiled["workoutSegments"][0]
        assert segment["sportType"]["sportTypeKey"] == "cardio_training"

    def test_step_count(self, hyrox_compiled: dict, golden_json: dict) -> None:
        compiled_steps = hyrox_compiled["workoutSegments"][0]["workoutSteps"]
        golden_steps = golden_json["workoutSegments"][0]["workoutSteps"]
        assert len(compiled_steps) == len(golden_steps)

    def test_warmup_step(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][0]

        assert step["type"] == "ExecutableStepDTO"
        assert step["stepOrder"] == 1
        assert step["stepType"]["stepTypeKey"] == "warmup"
        assert step["endCondition"]["conditionTypeKey"] == "lap.button"
        assert step["category"] == "ROW"
        assert step["exerciseName"] == "INDOOR_ROW"
        assert step["childStepId"] is None

    def test_exercise_interval_step(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][1]
        assert step["stepOrder"] == 2
        assert step["stepType"]["stepTypeKey"] == "interval"
        assert step["endCondition"]["conditionTypeKey"] == "lap.button"
        assert step["category"] == "CARDIO"

    def test_first_circuit(self, hyrox_compiled: dict) -> None:
        circuit = hyrox_compiled["workoutSegments"][0]["workoutSteps"][2]

        assert circuit["type"] == "RepeatGroupDTO"
        assert circuit["stepOrder"] == 3
        assert circuit["numberOfIterations"] == 4
        assert circuit["endConditionValue"] == 4.0
        assert circuit["skipLastRestStep"] is False
        assert len(circuit["workoutSteps"]) == 5

    def test_circuit_child_step_ids(self, hyrox_compiled: dict) -> None:
        circuit = hyrox_compiled["workoutSegments"][0]["workoutSteps"][2]
        assert circuit["childStepId"] == 1
        for child in circuit["workoutSteps"]:
            assert child["childStepId"] == 1

    def test_step_ordering(self, hyrox_compiled: dict, golden_json: dict) -> None:
        """Verify global step ordering matches golden reference."""
        compiled_steps = hyrox_compiled["workoutSegments"][0]["workoutSteps"]
        golden_steps = golden_json["workoutSegments"][0]["workoutSteps"]

        # Top-level step orders
        for c, g in zip(compiled_steps, golden_steps, strict=True):
            assert c["stepOrder"] == g["stepOrder"], (
                f"Step order mismatch: {c['stepOrder']} != {g['stepOrder']}"
            )

        # Children of first circuit
        c_circuit = compiled_steps[2]
        g_circuit = golden_steps[2]
        for c, g in zip(c_circuit["workoutSteps"], g_circuit["workoutSteps"], strict=True):
            assert c["stepOrder"] == g["stepOrder"]

        # Children of second circuit
        c_circuit2 = compiled_steps[3]
        g_circuit2 = golden_steps[3]
        for c, g in zip(c_circuit2["workoutSteps"], g_circuit2["workoutSteps"], strict=True):
            assert c["stepOrder"] == g["stepOrder"]

    def test_rowing_in_circuit(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][2]["workoutSteps"][0]
        assert step["stepOrder"] == 4
        assert step["category"] == "ROW"
        assert step["exerciseName"] == "INDOOR_ROW"
        assert step["endCondition"]["conditionTypeKey"] == "time"
        assert step["endConditionValue"] == 120.0

    def test_wall_ball_reps_and_weight(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][2]["workoutSteps"][1]
        assert step["stepOrder"] == 5
        assert step["category"] == "SQUAT"
        assert step["exerciseName"] == "WALL_BALL"
        assert step["endCondition"]["conditionTypeKey"] == "reps"
        assert step["endConditionValue"] == 20.0
        assert step["weightValue"] == 13
        assert step["weightUnit"]["unitKey"] == "pound"

    def test_weighted_lunge(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][2]["workoutSteps"][2]
        assert step["category"] == "LUNGE"
        assert step["exerciseName"] == "WEIGHTED_LUNGE"
        assert step["endConditionValue"] == 20.0
        assert step["weightValue"] == 45

    def test_farmers_carry_with_notes(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][2]["workoutSteps"][3]
        assert step["category"] == "CARRY"
        assert step["exerciseName"] == "FARMERS_CARRY"
        assert step["description"] == "40m"
        assert step["endCondition"]["conditionTypeKey"] == "lap.button"
        assert step["weightValue"] == 53

    def test_rest_in_circuit(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][2]["workoutSteps"][4]

        assert step["stepType"]["stepTypeKey"] == "rest"
        assert step["endCondition"]["conditionTypeKey"] == "time"
        assert step["endConditionValue"] == 120.0
        assert step["category"] is None
        assert step["exerciseName"] is None

    def test_second_circuit(self, hyrox_compiled: dict, golden_json: dict) -> None:
        circuit = hyrox_compiled["workoutSegments"][0]["workoutSteps"][3]
        golden = golden_json["workoutSegments"][0]["workoutSteps"][3]

        assert circuit["stepOrder"] == golden["stepOrder"]  # 9
        assert circuit["numberOfIterations"] == 3
        assert circuit["childStepId"] == 2

        for child in circuit["workoutSteps"]:
            assert child["childStepId"] == 2

    def test_hanging_knee_raise(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][3]["workoutSteps"][0]
        assert step["category"] == "LEG_RAISE"
        assert step["exerciseName"] == "HANGING_KNEE_RAISE"
        assert step["endCondition"]["conditionTypeKey"] == "time"
        assert step["endConditionValue"] == 45.0

    def test_kettlebell_swing(self, hyrox_compiled: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][3]["workoutSteps"][1]
        assert step["category"] == "HIP_RAISE"
        assert step["exerciseName"] == "KETTLEBELL_SWING"
        assert step["endConditionValue"] == 20.0
        assert step["weightValue"] == 20

    def test_cooldown(self, hyrox_compiled: dict, golden_json: dict) -> None:
        step = hyrox_compiled["workoutSegments"][0]["workoutSteps"][4]
        golden = golden_json["workoutSegments"][0]["workoutSteps"][4]

        assert step["stepOrder"] == golden["stepOrder"]  # 12
        assert step["stepType"]["stepTypeKey"] == "cooldown"
        assert step["endCondition"]["conditionTypeKey"] == "lap.button"
        assert step["category"] == "ROW"
        assert step["exerciseName"] == "INDOOR_ROW"
        assert step["childStepId"] is None


class TestCompilerRunning:
    """Test compilation of running workouts with zone targets."""

    def test_basic_running_workout(self) -> None:
        from garmin_pipeline.models import (
            CooldownStep,
            RecoveryStep,
            RunStep,
            WarmupStep,
            Workout,
        )
        from garmin_pipeline.zones import load_zones

        zones_path = Path(__file__).parent.parent / "workouts" / "zones.yaml"
        zone_config = load_zones(zones_path)

        workout = Workout(
            name="Threshold Intervals",
            type="running",
            steps=[
                WarmupStep(duration="10:00", zone="z2"),
                RunStep(duration="5:00", zone="threshold"),
                RecoveryStep(duration="2:00", zone="z1"),
                CooldownStep(duration="5:00"),
            ],
        )

        compiled = compile_workout(workout, zone_config)
        steps = compiled["workoutSegments"][0]["workoutSteps"]

        assert compiled["sportType"]["sportTypeKey"] == "running"
        assert len(steps) == 4

        # Warmup should have pace target from z2
        warmup = steps[0]
        assert warmup["stepType"]["stepTypeKey"] == "warmup"
        assert warmup["endConditionValue"] == 600.0
        assert warmup["targetType"]["workoutTargetTypeKey"] == "pace.zone"

        # Interval with threshold zone
        interval = steps[1]
        assert interval["endConditionValue"] == 300.0
        assert interval["targetType"]["workoutTargetTypeKey"] == "pace.zone"

        # Recovery
        recovery = steps[2]
        assert recovery["stepType"]["stepTypeKey"] == "recovery"

        # Cooldown with no zone → no target
        cooldown = steps[3]
        assert cooldown["stepType"]["stepTypeKey"] == "cooldown"
        assert cooldown["targetType"]["workoutTargetTypeKey"] == "no.target"
