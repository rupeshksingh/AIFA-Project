import pytest

from disaster_scenario import goal_conditions, initial_state
from heuristics import (
    blocked_roads_heuristic,
    get_heuristic,
    hybrid_response_heuristic,
    untreated_victims_heuristic,
    zero_heuristic,
)


def test_zero_heuristic_is_zero() -> None:
    assert zero_heuristic(initial_state, goal_conditions) == 0.0


def test_untreated_victims_heuristic_matches_simple_scenario() -> None:
    assert untreated_victims_heuristic(initial_state, goal_conditions) == 1.0


def test_blocked_and_hybrid_heuristics_non_negative() -> None:
    blocked_score = blocked_roads_heuristic(initial_state, goal_conditions)
    hybrid_score = hybrid_response_heuristic(initial_state, goal_conditions)
    assert blocked_score >= 0.0
    assert hybrid_score >= 0.0


def test_get_heuristic_rejects_unknown_name() -> None:
    with pytest.raises(ValueError):
        get_heuristic("does_not_exist")
