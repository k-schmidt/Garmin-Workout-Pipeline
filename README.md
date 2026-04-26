# garmin-workout-pipeline

YAML-defined workouts compiled and pushed to Garmin Connect. Supports running, cycling, and strength/cardio workouts with zone-based targets, exercise definitions, and weekly scheduling.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/yourusername/garmin-workout-pipeline.git
cd garmin-workout-pipeline
uv sync
cp .env.example .env
```

Add your Garmin Connect credentials to `.env`:

```
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-password
```

Then configure your training zones in `workouts/zones.yaml` — the included file has example values you should replace with your own.

## Usage

```bash
# Validate a workout (compile to JSON, don't upload)
gwp validate workouts/templates/hyrox-sim.yaml --zones workouts/zones.yaml

# Push to Garmin Connect
gwp push workouts/templates/hyrox-sim.yaml --zones workouts/zones.yaml

# Push and schedule for a date
gwp push workouts/templates/speed-400s-300s.yaml --zones workouts/zones.yaml --schedule 2026-04-29

# Dry run (print JSON without uploading)
gwp push workouts/templates/hyrox-sim.yaml --zones workouts/zones.yaml --dry-run

# List workouts on Garmin Connect
gwp list

# Delete a workout
gwp delete <workout-id>

# Show resolved zones
gwp zones --zones workouts/zones.yaml
```

## Workout YAML Format

### Running

```yaml
name: "Threshold Intervals"
type: running

steps:
  - warmup: { duration: "10:00", zone: easy }
  - run: { distance: "1km", pace: { min: "6:25/mi", max: "6:40/mi" } }
  - recovery: { duration: "2:00" }
  - run: { duration: "5:00", zone: threshold }
  - cooldown: { duration: lap, zone: easy }
```

### Strength / Cardio

```yaml
name: "Hyrox Strength"
type: strength

steps:
  - warmup: { duration: lap, exercise: rowing_machine }
  - circuit:
      iterations: 4
      steps:
        - exercise: { exercise: wall_ball, reps: 20, weight: 13 }
        - exercise: { exercise: weighted_lunge, reps: 20, weight: 45 }
        - rest: { duration: "2:00" }
  - cooldown: { duration: lap, exercise: rowing_machine }
```

### Cycling

```yaml
name: "Sweet Spot"
type: cycling

steps:
  - warmup: { duration: "10:00", zone: z2 }
  - bike: { duration: "20:00", zone: threshold }
  - cooldown: { duration: "5:00" }
```

## Zones

Training zones are defined in `workouts/zones.yaml` with HR, pace, and power targets per sport. The compiler resolves zone names (e.g., `threshold`, `z2`, `easy`) to Garmin API target values.

## Step Types

| Type | End Conditions | Targets |
|---|---|---|
| `warmup` | duration, lap | zone, exercise |
| `cooldown` | duration, lap | zone, exercise |
| `run` | duration, distance, lap | zone, pace, hr |
| `bike` | duration, distance, lap | zone, power, power_pct |
| `recovery` | duration, distance, lap | zone |
| `exercise` | duration, reps, lap | — |
| `rest` | duration | — |
| `circuit` | iterations | nested steps |

## Project Structure

```
cli.py                          # Click CLI (gwp command)
garmin_pipeline/
  compiler.py                   # Workout model -> Garmin API JSON
  exercises.py                  # Exercise name -> Garmin category/name registry
  loader.py                     # YAML parser with !include support
  models.py                     # Pydantic workout models
  sync.py                       # Garmin Connect auth and upload
  zones.py                      # Zone resolution (HR, pace, power)
workouts/
  zones.yaml                    # Training zone definitions
  templates/                    # Workout YAML files
tests/
  fixtures/                     # Golden reference JSON
  test_compiler.py              # Compiler golden tests
  test_loader.py                # YAML loading and !include
  test_models.py                # Step parsing
  test_zones.py                 # Zone resolution
```

## Development

```bash
uv run pytest -v              # run tests
uv run ruff check . --fix     # lint
uv run ruff format .          # format
```
