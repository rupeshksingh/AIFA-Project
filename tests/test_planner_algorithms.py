from disaster_scenario import all_possible_actions, goal_conditions, initial_state
from heuristics import get_heuristic
from planner import run_planner


def test_bfs_finds_shortest_known_plan_on_simple_scenario() -> None:
    result = run_planner(initial_state, goal_conditions, all_possible_actions, algorithm="bfs")
    assert result["success"] is True
    assert result["plan_length"] == 5


def test_ucs_matches_bfs_plan_length_on_uniform_cost_domain() -> None:
    bfs_result = run_planner(initial_state, goal_conditions, all_possible_actions, algorithm="bfs")
    ucs_result = run_planner(initial_state, goal_conditions, all_possible_actions, algorithm="ucs")
    assert ucs_result["success"] is True
    assert bfs_result["plan_length"] == ucs_result["plan_length"]


def test_astar_returns_valid_plan() -> None:
    result = run_planner(
        initial_state,
        goal_conditions,
        all_possible_actions,
        algorithm="astar",
        heuristic_fn=get_heuristic("untreated_victims"),
        heuristic_name="untreated_victims",
    )
    assert result["success"] is True
    assert result["plan_length"] >= 1


def test_gbfs_returns_valid_plan() -> None:
    result = run_planner(
        initial_state,
        goal_conditions,
        all_possible_actions,
        algorithm="gbfs",
        heuristic_fn=get_heuristic("hybrid_response"),
        heuristic_name="hybrid_response",
    )
    assert result["success"] is True
    assert result["plan_length"] >= 1
