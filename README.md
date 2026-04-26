# garmin-workout-pipeline

YAML-defined workouts compiled and pushed to Garmin Connect. Supports running, cycling, and strength/cardio workouts with zone-based targets, exercise definitions, and weekly scheduling.

Available as a **CLI** (`gwp`) and as an **MCP server** for conversational workout building with Claude Desktop, Claude Code, or any MCP-compatible client.

## Install

### From PyPI

```bash
pip install garmin-workout-pipeline
```

### From GitHub (no PyPI account needed)

```bash
uv tool install git+https://github.com/k-schmidt/Garmin-Workout-Pipeline.git
```

### From source

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/k-schmidt/Garmin-Workout-Pipeline.git
cd Garmin-Workout-Pipeline
uv sync
```

## Configuration

Set your Garmin Connect credentials as environment variables or in a `.env` file:

```
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-password
```

Configure your training zones in `workouts/zones.yaml` — the included file has example values you should replace with your own.

## MCP Server (Claude Desktop / Claude Code)

Use the MCP server to build workouts conversationally through Claude. 24 tools available: create workouts, add steps, manage circuits, upload to Garmin Connect, browse exercises and zones.

### Claude Code

If installed via pip or uv:

```bash
claude mcp add garmin-workouts \
  -e GARMIN_EMAIL=your-email@example.com \
  -e GARMIN_PASSWORD=your-password \
  -- garmin-mcp
```

Without installing (runs directly from GitHub):

```bash
claude mcp add garmin-workouts \
  -e GARMIN_EMAIL=your-email@example.com \
  -e GARMIN_PASSWORD=your-password \
  -- uvx --from git+https://github.com/k-schmidt/Garmin-Workout-Pipeline.git garmin-mcp
```

From a local clone:

```bash
claude mcp add garmin-workouts -- uv --directory /path/to/Garmin-Workout-Pipeline run garmin_pipeline/mcp_server.py
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "garmin-workouts": {
      "command": "garmin-mcp",
      "env": {
        "GARMIN_EMAIL": "your-email@example.com",
        "GARMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

### Available MCP Tools

| Category | Tools |
|---|---|
| Workout | `create_workout`, `get_workout`, `set_workout_name`, `clear_workout` |
| Steps | `add_warmup`, `add_cooldown`, `add_run`, `add_bike`, `add_exercise`, `add_rest`, `add_recovery`, `remove_step` |
| Circuits | `add_circuit`, `end_circuit` |
| Garmin Connect | `preview_upload`, `upload_workout`, `list_workouts`, `delete_workout` |
| Reference | `list_exercises`, `get_zones`, `validate_workout` |
| Templates | `save_yaml`, `load_template`, `list_templates` |

## CLI Usage

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
garmin_pipeline/
  mcp_server.py                 # MCP server for Claude Desktop/Code
  cli.py                        # Click CLI (gwp command)
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
