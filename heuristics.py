from collections.abc import Callable

from domain_models import State

HeuristicFn = Callable[[State, frozenset[tuple[str, ...]]], float]


def zero_heuristic(_state: State, _goal_conditions: frozenset[tuple[str, ...]]) -> float:
    """Baseline heuristic that provides no guidance."""
    return 0.0


def untreated_victims_heuristic(
    state: State,
    _goal_conditions: frozenset[tuple[str, ...]],
) -> float:
    """
    Count remaining untreated victim locations.

    This is a practical lower bound in this domain because each untreated
    victim location requires at least one Treat action.
    """
    return float(sum(1 for fact in state.facts if fact[0] == "victims_untreated"))


def blocked_roads_heuristic(state: State, _goal_conditions: frozenset[tuple[str, ...]]) -> float:
    """Prefer states with fewer blocked roads (mainly useful for greedy search)."""
    blocked_count = sum(1 for fact in state.facts if fact[0] == "blocked")
    # Divide by two because roads are represented in both directions.
    return float(blocked_count) / 2.0


def hybrid_response_heuristic(
    state: State,
    goal_conditions: frozenset[tuple[str, ...]],
) -> float:
    """Weighted combination for stronger greedy guidance."""
    untreated = untreated_victims_heuristic(state, goal_conditions)
    blocked = blocked_roads_heuristic(state, goal_conditions)
    return untreated + (0.25 * blocked)


_HEURISTICS: dict[str, HeuristicFn] = {
    "zero": zero_heuristic,
    "untreated_victims": untreated_victims_heuristic,
    "blocked_roads": blocked_roads_heuristic,
    "hybrid_response": hybrid_response_heuristic,
}


def get_heuristic(name: str) -> HeuristicFn:
    """Resolve heuristic by name with a clear error message."""
    try:
        return _HEURISTICS[name]
    except KeyError as exc:
        valid = ", ".join(sorted(_HEURISTICS))
        raise ValueError(f"Unknown heuristic '{name}'. Valid choices: {valid}") from exc


def list_heuristics() -> tuple[str, ...]:
    """Return stable heuristic names for CLI help/validation."""
    return tuple(sorted(_HEURISTICS))
