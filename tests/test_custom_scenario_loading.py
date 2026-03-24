import json
from pathlib import Path

import pytest

from planner import load_custom_scenario, run_planner


def test_load_custom_scenario_produces_solvable_problem(tmp_path: Path) -> None:
    scenario_file = tmp_path / "custom_scenario.json"
    scenario_file.write_text(
        json.dumps(
            {
                "locations": ["A", "B", "C"],
                "roads": [
                    {"from": "A", "to": "B", "status": "clear"},
                    {"from": "B", "to": "C", "status": "blocked"},
                ],
                "resources": {"Bulldozer1": "A", "MedTeam1": "A"},
                "victims_untreated": ["C"],
                "goal_treated": ["C"],
            }
        ),
        encoding="utf-8",
    )

    initial_state, goal_conditions, actions = load_custom_scenario(str(scenario_file))
    result = run_planner(initial_state, goal_conditions, actions, algorithm="bfs")
    assert result["success"] is True
    assert result["plan_length"] >= 1


def test_load_custom_scenario_rejects_unknown_location(tmp_path: Path) -> None:
    scenario_file = tmp_path / "invalid_custom_scenario.json"
    scenario_file.write_text(
        json.dumps(
            {
                "locations": ["A", "B"],
                "roads": [{"from": "A", "to": "B", "status": "clear"}],
                "resources": {"Bulldozer1": "A", "MedTeam1": "A"},
                "victims_untreated": ["C"],
                "goal_treated": ["C"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Victim location 'C' is not in locations."):
        load_custom_scenario(str(scenario_file))
