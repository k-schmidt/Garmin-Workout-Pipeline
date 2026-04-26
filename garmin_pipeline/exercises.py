"""Exercise registry mapping YAML names to Garmin API category/exerciseName constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExerciseDefinition:
    """Garmin API exercise definition."""

    category: str
    exercise_name: str


# Mapping of YAML exercise keys → Garmin category + exerciseName.
# Categories and names are Garmin API constants — not user-configurable.
# Source: reverse-engineered from Garmin Connect workout JSON responses.
EXERCISE_REGISTRY: dict[str, ExerciseDefinition] = {
    # Rowing
    "rowing_machine": ExerciseDefinition("ROW", "INDOOR_ROW"),
    "indoor_row": ExerciseDefinition("ROW", "INDOOR_ROW"),
    # Cardio (generic)
    "cardio": ExerciseDefinition("CARDIO", ""),
    "jump_rope": ExerciseDefinition("CARDIO", "JUMP_ROPE"),
    "jumping_jack": ExerciseDefinition("CARDIO", "JUMPING_JACK"),
    "burpee": ExerciseDefinition("CARDIO", "BURPEE"),
    "mountain_climber": ExerciseDefinition("CARDIO", "MOUNTAIN_CLIMBER"),
    "box_jump": ExerciseDefinition("CARDIO", "BOX_JUMP"),
    "battle_rope": ExerciseDefinition("CARDIO", "BATTLE_ROPE"),
    # Squat
    "wall_ball": ExerciseDefinition("SQUAT", "WALL_BALL"),
    "squat": ExerciseDefinition("SQUAT", "SQUAT"),
    "back_squat": ExerciseDefinition("SQUAT", "BACK_SQUAT"),
    "front_squat": ExerciseDefinition("SQUAT", "FRONT_SQUAT"),
    "goblet_squat": ExerciseDefinition("SQUAT", "GOBLET_SQUAT"),
    "air_squat": ExerciseDefinition("SQUAT", "BODY_WEIGHT_SQUAT"),
    "thruster": ExerciseDefinition("SQUAT", "THRUSTERS"),
    # Lunge
    "weighted_lunge": ExerciseDefinition("LUNGE", "WEIGHTED_LUNGE"),
    "lunge": ExerciseDefinition("LUNGE", "LUNGE"),
    "walking_lunge": ExerciseDefinition("LUNGE", "WALKING_LUNGE"),
    "reverse_lunge": ExerciseDefinition("LUNGE", "REVERSE_LUNGE"),
    # Carry
    "farmers_carry": ExerciseDefinition("CARRY", "FARMERS_CARRY"),
    "farmers_walk": ExerciseDefinition("CARRY", "FARMERS_CARRY"),
    "suitcase_carry": ExerciseDefinition("CARRY", "SUITCASE_CARRY"),
    # Leg raise / core
    "hanging_knee_raise": ExerciseDefinition("LEG_RAISE", "HANGING_KNEE_RAISE"),
    "hanging_leg_raise": ExerciseDefinition("LEG_RAISE", "HANGING_LEG_RAISE"),
    "leg_raise": ExerciseDefinition("LEG_RAISE", "LEG_RAISE"),
    # Hip raise / swing
    "kettlebell_swing": ExerciseDefinition("HIP_RAISE", "KETTLEBELL_SWING"),
    "hip_thrust": ExerciseDefinition("HIP_RAISE", "HIP_THRUST"),
    "glute_bridge": ExerciseDefinition("HIP_RAISE", "GLUTE_BRIDGE"),
    # Deadlift
    "deadlift": ExerciseDefinition("DEADLIFT", "DEADLIFT"),
    "romanian_deadlift": ExerciseDefinition("DEADLIFT", "ROMANIAN_DEADLIFT"),
    "sumo_deadlift": ExerciseDefinition("DEADLIFT", "SUMO_DEADLIFT"),
    "kettlebell_deadlift": ExerciseDefinition("DEADLIFT", "KETTLEBELL_DEADLIFT"),
    # Bench press / chest
    "bench_press": ExerciseDefinition("BENCH_PRESS", "BENCH_PRESS"),
    "dumbbell_bench_press": ExerciseDefinition("BENCH_PRESS", "DUMBBELL_BENCH_PRESS"),
    "push_up": ExerciseDefinition("PUSH_UP", "PUSH_UP"),
    # Pull up / row
    "pull_up": ExerciseDefinition("PULL_UP", "PULL_UP"),
    "chin_up": ExerciseDefinition("PULL_UP", "CHIN_UP"),
    "bent_over_row": ExerciseDefinition("ROW", "BENT_OVER_ROW"),
    "dumbbell_row": ExerciseDefinition("ROW", "DUMBBELL_ROW"),
    # Shoulder press
    "overhead_press": ExerciseDefinition("SHOULDER_PRESS", "OVERHEAD_PRESS"),
    "dumbbell_shoulder_press": ExerciseDefinition("SHOULDER_PRESS", "DUMBBELL_SHOULDER_PRESS"),
    # Plank / core
    "plank": ExerciseDefinition("PLANK", "PLANK"),
    "side_plank": ExerciseDefinition("PLANK", "SIDE_PLANK"),
    # Olympic lifts
    "clean": ExerciseDefinition("OLYMPIC_LIFT", "CLEAN"),
    "clean_and_jerk": ExerciseDefinition("OLYMPIC_LIFT", "CLEAN_AND_JERK"),
    "snatch": ExerciseDefinition("OLYMPIC_LIFT", "SNATCH"),
    "power_clean": ExerciseDefinition("OLYMPIC_LIFT", "POWER_CLEAN"),
    # Sled
    "sled_push": ExerciseDefinition("CARRY", "SLED_PUSH"),
    "sled_pull": ExerciseDefinition("CARRY", "SLED_PULL"),
}


def lookup_exercise(name: str) -> ExerciseDefinition:
    """Look up a Garmin exercise definition by YAML name.

    Raises:
        KeyError: If exercise name is not in the registry.
    """
    if name in EXERCISE_REGISTRY:
        return EXERCISE_REGISTRY[name]
    valid = ", ".join(sorted(EXERCISE_REGISTRY.keys()))
    raise KeyError(f"Unknown exercise '{name}'. Valid exercises: {valid}")
