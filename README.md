# Classical AI Course Project

This repository implements a **Classical AI planning system** for disaster-response logistics, designed to match course requirements (state-space search, planning operators, validated code, and visualization).

## Problem Statement (Domain + Interdisciplinary Angle)

- **Domain focus:** emergency logistics in a disaster-hit city.
- **Department relevance:** civil/disaster management operations and AI-based planning.
- **Interdisciplinary framing:** combines infrastructure constraints (roads/debris) with computational planning (search + heuristics).
- **Classical AI scope:** symbolic state-space planning with explicit preconditions/effects.

Phase-1 style proposal text is available in `PHASE1_PROPOSAL.md`. The full write-up for the project is in **`AIFA_Report.pdf`**.

## Classical AI Formulation

- **State:** immutable set of symbolic facts (e.g., `('at', 'MedTeam1', 'A')`).
- **Initial state:** resource locations, road conditions, untreated victims.
- **Goal conditions:** required victim sites are treated.
- **Operators:**
  - `Move(resource, from, to)`
  - `Clear(bulldozer, from, to)`
  - `Treat(med_team, location)`

## Implemented Techniques

- **Uninformed search:** `bfs`, `ucs`
- **Informed search:** `gbfs`, `astar`
- **Heuristics:** `zero`, `untreated_victims`, `blocked_roads`, `hybrid_response`
- **Planning model:** STRIPS-like add/delete effects over symbolic facts

## Repository Structure

- `domain_models.py`: immutable `State`, executable `Action`
- `disaster_scenario.py`: base scenario + domain action generator
- `complex_scenario.py`: larger scenario for stress/benchmarking
- `planner.py`: search engine + CLI + visualization driver
- `heuristics.py`: heuristic registry and implementations
- `visualization.py`: graph-based plan playback
- `benchmarks.py`: repeated algorithm comparisons (table/JSON/CSV)
- `tests/`: planner/domain/heuristic correctness tests
- `AIFA_Report.pdf`: project report (domain, methods, results)
- `CLAUDE.md`: quick repo map, dependency rules, debugging log

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
# Default: simple scenario, BFS, with visualization
python planner.py

# Complex scenario with A* heuristic (no visualization)
python planner.py --scenario complex --algorithm astar --heuristic untreated_victims --no-viz

# Custom graph/scenario JSON file
python planner.py --custom-scenario-file custom_scenario_example.json --algorithm astar --heuristic untreated_victims --no-viz

# Benchmark all algorithms
python benchmarks.py --repeats 5 --heuristic untreated_victims --output-json benchmark_results.json --output-csv benchmark_results.csv
```

## Custom Graph File Format

Use `--custom-scenario-file <path>` to load your own graph and planning problem.
When this flag is provided, it overrides `--scenario`.

Required JSON fields:

- `locations`: list of location names.
- `roads`: list of roads with:
  - `from`: source location
  - `to`: destination location
  - `status`: `"clear"` or `"blocked"`
- `resources`: object mapping resource name -> starting location.
  - Use `Bulldozer*` names for clearing actions.
  - Use `MedTeam*` names for treatment actions.
- `victims_untreated`: list of locations currently needing treatment.
- `goal_treated`: list of locations that must be treated to satisfy the goal.

Example:

```json
{
  "locations": ["A", "B", "C", "D"],
  "roads": [
    { "from": "A", "to": "B", "status": "clear" },
    { "from": "B", "to": "C", "status": "blocked" },
    { "from": "C", "to": "D", "status": "clear" }
  ],
  "resources": {
    "Bulldozer1": "A",
    "MedTeam1": "A"
  },
  "victims_untreated": ["D"],
  "goal_treated": ["D"]
}
```

Notes:

- Roads are treated as bidirectional internally.
- Every location referenced in roads/resources/victims/goals must exist in `locations`.
- A ready-to-run sample is included at `custom_scenario_example.json`.

## Validation & Quality

```powershell
pytest
ruff check .
mypy .
```

Optional:

```powershell
pre-commit install
pre-commit run --all-files
```

## Visualization Output

The planner can replay state transitions on a road-network graph:
- blocked roads in red
- clear roads in green
- resource positions and victim status annotated per location

Use `--no-viz` for benchmark/performance-only runs.