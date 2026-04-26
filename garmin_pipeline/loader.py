"""YAML workout loader with !include support."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from garmin_pipeline.models import Workout, parse_step


class _IncludeTracker:
    """Tracks included files to detect circular includes."""

    def __init__(self) -> None:
        self.stack: set[str] = set()


_tracker = _IncludeTracker()


class WorkoutLoader(yaml.SafeLoader):
    """Custom YAML loader with !include constructor."""

    root: Path = Path(".")


def _include_constructor(loader: WorkoutLoader, node: yaml.Node) -> Any:
    """Load referenced YAML file relative to current file's directory."""
    relative_path = loader.construct_scalar(node)
    if not isinstance(relative_path, str):
        raise yaml.YAMLError(f"!include value must be a string, got {type(relative_path)}")

    filepath = (loader.root / relative_path).resolve()
    file_key = str(filepath)

    if file_key in _tracker.stack:
        raise yaml.YAMLError(f"Circular include detected: {filepath}")

    if not filepath.exists():
        raise FileNotFoundError(f"!include file not found: {filepath}")

    _tracker.stack.add(file_key)
    try:
        included = _load_raw_yaml(filepath)
    finally:
        _tracker.stack.discard(file_key)

    return included


WorkoutLoader.add_constructor("!include", _include_constructor)


def _load_raw_yaml(path: Path) -> Any:
    """Load a YAML file using WorkoutLoader with correct root path."""
    text = path.read_text()
    loader = WorkoutLoader(text)
    loader.root = path.parent
    loader.name = str(path)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def load_workout(path: Path) -> Workout:
    """Load a YAML workout file and parse into a Workout model.

    Args:
        path: Path to the workout YAML file.

    Returns:
        Parsed Workout model.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If required fields are missing.
        yaml.YAMLError: If YAML is malformed.
    """
    path = path.resolve()
    _tracker.stack.clear()

    raw = _load_raw_yaml(path)

    if not isinstance(raw, dict):
        raise ValueError(f"Workout YAML must be a mapping, got {type(raw).__name__}")

    for field in ("name", "type", "steps"):
        if field not in raw:
            raise ValueError(f"Missing required field '{field}' in {path}")

    if not isinstance(raw["steps"], list):
        raise ValueError(f"'steps' must be a list in {path}")

    steps = [parse_step(s) for s in raw["steps"]]

    return Workout(
        name=raw["name"],
        type=raw["type"],
        steps=steps,
        description=raw.get("description"),
    )
