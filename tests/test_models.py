"""Tests for YAML step parsing and duration utilities."""

import pytest

from garmin_pipeline.models import (
    BikeStep,
    CircuitGroup,
    CooldownStep,
    ExerciseStep,
    RecoveryStep,
    RestStep,
    RunStep,
    WarmupStep,
    parse_distance_meters,
    parse_duration_seconds,
    parse_step,
)


class TestParseDuration:
    def test_minutes_seconds(self) -> None:
        assert parse_duration_seconds("2:00") == 120.0

    def test_seconds_only(self) -> None:
        assert parse_duration_seconds("0:45") == 45.0

    def test_hours_minutes_seconds(self) -> None:
        assert parse_duration_seconds("1:30:00") == 5400.0

    def test_bare_seconds(self) -> None:
        assert parse_duration_seconds("30") == 30.0

    def test_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid duration"):
            parse_duration_seconds("abc")


class TestParseDistance:
    def test_km(self) -> None:
        assert parse_distance_meters("1km") == 1000.0

    def test_meters(self) -> None:
        assert parse_distance_meters("400m") == 400.0

    def test_miles(self) -> None:
        assert parse_distance_meters("1mi") == pytest.approx(1609.34)

    def test_bare_number(self) -> None:
        assert parse_distance_meters("800") == 800.0


class TestParseStep:
    def test_exercise_step(self) -> None:
        step = parse_step({"exercise": "wall_ball", "reps": 20, "weight": 13})
        assert isinstance(step, ExerciseStep)
        assert step.exercise == "wall_ball"
        assert step.reps == 20
        assert step.weight == 13

    def test_rest_step_string(self) -> None:
        step = parse_step({"rest": "2:00"})
        assert isinstance(step, RestStep)
        assert step.duration == "2:00"

    def test_warmup_dict(self) -> None:
        step = parse_step({"warmup": {"exercise": "rowing_machine", "duration": "lap"}})
        assert isinstance(step, WarmupStep)
        assert step.exercise == "rowing_machine"
        assert step.duration == "lap"

    def test_cooldown_dict(self) -> None:
        step = parse_step({"cooldown": {"duration": "5:00", "zone": "z1"}})
        assert isinstance(step, CooldownStep)
        assert step.zone == "z1"

    def test_run_step(self) -> None:
        step = parse_step({"run": {"duration": "5:00", "zone": "threshold"}})
        assert isinstance(step, RunStep)
        assert step.duration == "5:00"
        assert step.zone == "threshold"

    def test_bike_step(self) -> None:
        step = parse_step({"bike": {"duration": "20:00", "zone": "tempo"}})
        assert isinstance(step, BikeStep)

    def test_recovery_step(self) -> None:
        step = parse_step({"recovery": {"duration": "2:00", "zone": "z1"}})
        assert isinstance(step, RecoveryStep)

    def test_circuit(self) -> None:
        step = parse_step(
            {
                "circuit": 4,
                "steps": [
                    {"exercise": "wall_ball", "reps": 20},
                    {"rest": "1:00"},
                ],
            }
        )
        assert isinstance(step, CircuitGroup)
        assert step.iterations == 4
        assert len(step.steps) == 2

    def test_repeat_alias(self) -> None:
        step = parse_step(
            {
                "repeat": 3,
                "steps": [{"run": {"duration": "3:00", "zone": "z3"}}],
            }
        )
        assert isinstance(step, CircuitGroup)
        assert step.iterations == 3

    def test_unknown_keys_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse step"):
            parse_step({"foo": "bar"})
