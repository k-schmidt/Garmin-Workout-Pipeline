"""Tests for YAML loader with !include support."""

from pathlib import Path

import pytest

from garmin_pipeline.loader import load_workout
from garmin_pipeline.models import CircuitGroup, CooldownStep, ExerciseStep, WarmupStep

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadWorkout:
    def test_load_hyrox(self) -> None:
        workout = load_workout(FIXTURES / "hyrox-strength.yaml")
        assert workout.name == "Hyrox Strength Endurance + Grip"
        assert workout.type.value == "strength"
        assert len(workout.steps) == 5

    def test_warmup_step(self) -> None:
        workout = load_workout(FIXTURES / "hyrox-strength.yaml")
        step = workout.steps[0]
        assert isinstance(step, WarmupStep)
        assert step.exercise == "rowing_machine"
        assert step.duration == "lap"

    def test_circuit_steps(self) -> None:
        workout = load_workout(FIXTURES / "hyrox-strength.yaml")
        circuit = workout.steps[2]
        assert isinstance(circuit, CircuitGroup)
        assert circuit.iterations == 4
        assert circuit.skip_last_rest is False
        assert len(circuit.steps) == 5

    def test_second_circuit(self) -> None:
        workout = load_workout(FIXTURES / "hyrox-strength.yaml")
        circuit = workout.steps[3]
        assert isinstance(circuit, CircuitGroup)
        assert circuit.iterations == 3
        assert len(circuit.steps) == 2

    def test_cooldown(self) -> None:
        workout = load_workout(FIXTURES / "hyrox-strength.yaml")
        step = workout.steps[4]
        assert isinstance(step, CooldownStep)
        assert step.exercise == "rowing_machine"

    def test_exercise_step_in_circuit(self) -> None:
        workout = load_workout(FIXTURES / "hyrox-strength.yaml")
        circuit = workout.steps[2]
        assert isinstance(circuit, CircuitGroup)
        wall_ball = circuit.steps[1]
        assert isinstance(wall_ball, ExerciseStep)
        assert wall_ball.exercise == "wall_ball"
        assert wall_ball.reps == 20
        assert wall_ball.weight == 13

    def test_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_workout(Path("/nonexistent/workout.yaml"))

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("name: test\n")
        with pytest.raises(ValueError, match="Missing required field"):
            load_workout(bad)


class TestInclude:
    def test_include(self, tmp_path: Path) -> None:
        include_file = tmp_path / "warmup.yaml"
        include_file.write_text("warmup:\n  exercise: rowing_machine\n  duration: lap\n")
        main = tmp_path / "workout.yaml"
        main.write_text("name: test\ntype: strength\nsteps:\n  - !include warmup.yaml\n")
        workout = load_workout(main)
        assert len(workout.steps) == 1
        assert isinstance(workout.steps[0], WarmupStep)

    def test_circular_include(self, tmp_path: Path) -> None:
        a = tmp_path / "a.yaml"
        b = tmp_path / "b.yaml"
        a.write_text("!include b.yaml\n")
        b.write_text("!include a.yaml\n")
        main = tmp_path / "workout.yaml"
        main.write_text("name: test\ntype: strength\nsteps:\n  - !include a.yaml\n")
        with pytest.raises(Exception, match="[Cc]ircular"):
            load_workout(main)
