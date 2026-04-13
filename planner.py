import argparse
import heapq
import itertools
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Literal, TypedDict

from domain_models import Action, State

AlgorithmName = Literal["bfs", "ucs", "gbfs", "astar"]
HeuristicFn = Callable[[State, frozenset[tuple[str, ...]]], float]
ScenarioData = tuple[State, frozenset[tuple[str, ...]], list[Action]]


class PlannerResult(TypedDict, total=False):
    success: bool
    plan: list[Action]
    nodes_expanded: int
    time_taken: float
    plan_length: int
    algorithm: str
    heuristic: str


class CustomRoad(TypedDict):
    from_location: str
    to_location: str
    status: str


class CustomScenarioDocument(TypedDict):
    locations: list[str]
    roads: list[CustomRoad]
    resources: dict[str, str]
    victims_untreated: list[str]
    goal_treated: list[str]


def get_scenarios() -> dict[str, ScenarioData]:
    """Lazily load scenario modules to keep imports loosely coupled."""
    from complex_scenario import (
        all_possible_actions as complex_all_possible_actions,
    )
    from complex_scenario import (
        goal_conditions as complex_goal_conditions,
    )
    from complex_scenario import (
        initial_state as complex_initial_state,
    )
    from disaster_scenario import (
        all_possible_actions as simple_all_possible_actions,
    )
    from disaster_scenario import (
        goal_conditions as simple_goal_conditions,
    )
    from disaster_scenario import (
        initial_state as simple_initial_state,
    )

    return {
        "simple": (simple_initial_state, simple_goal_conditions, simple_all_possible_actions),
        "complex": (complex_initial_state, complex_goal_conditions, complex_all_possible_actions),
    }


def _as_string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"'{field_name}' must be a list of strings.")
    if not value:
        raise ValueError(f"'{field_name}' must not be empty.")
    return value


def _as_roads(value: object) -> list[CustomRoad]:
    if not isinstance(value, list) or not value:
        raise ValueError("'roads' must be a non-empty list of road entries.")

    normalized_roads: list[CustomRoad] = []
    for road in value:
        if not isinstance(road, dict):
            raise ValueError("Each road entry must be an object.")

        from_location = road.get("from")
        to_location = road.get("to")
        status = road.get("status")
        if not isinstance(from_location, str) or not isinstance(to_location, str):
            raise ValueError("Each road requires string fields: 'from' and 'to'.")
        if from_location == to_location:
            raise ValueError("Road endpoints must be different.")
        if status not in {"clear", "blocked"}:
            raise ValueError("Road 'status' must be either 'clear' or 'blocked'.")

        normalized_roads.append(
            {
                "from_location": from_location,
                "to_location": to_location,
                "status": status,
            }
        )
    return normalized_roads


def _as_resource_locations(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError("'resources' must be a non-empty object mapping resource to location.")

    normalized_resources: dict[str, str] = {}
    for resource_name, location in value.items():
        if not isinstance(resource_name, str) or not isinstance(location, str):
            raise ValueError("'resources' keys and values must be strings.")
        normalized_resources[resource_name] = location
    return normalized_resources


def custom_scenario_from_document(document_raw: dict[str, object]) -> ScenarioData:
    """Convert a custom scenario object (file or API JSON) into planner-ready data."""
    from disaster_scenario import generate_domain_actions

    locations = _as_string_list(document_raw.get("locations"), "locations")
    roads = _as_roads(document_raw.get("roads"))
    resources_to_locations = _as_resource_locations(document_raw.get("resources"))
    victims_untreated = _as_string_list(document_raw.get("victims_untreated"), "victims_untreated")
    goal_treated = _as_string_list(document_raw.get("goal_treated"), "goal_treated")
    custom_document: CustomScenarioDocument = {
        "locations": locations,
        "roads": roads,
        "resources": resources_to_locations,
        "victims_untreated": victims_untreated,
        "goal_treated": goal_treated,
    }

    location_set = set(custom_document["locations"])
    for road in custom_document["roads"]:
        if road["from_location"] not in location_set or road["to_location"] not in location_set:
            raise ValueError("Road endpoints must reference known locations.")

    for resource_name, resource_location in custom_document["resources"].items():
        if resource_location not in location_set:
            raise ValueError(
                f"Resource '{resource_name}' starts at unknown location "
                f"'{resource_location}'."
            )

    for victim_location in custom_document["victims_untreated"]:
        if victim_location not in location_set:
            raise ValueError(f"Victim location '{victim_location}' is not in locations.")

    for goal_location in custom_document["goal_treated"]:
        if goal_location not in location_set:
            raise ValueError(f"Goal location '{goal_location}' is not in locations.")

    directional_roads: list[tuple[str, str]] = []
    initial_facts: set[tuple[str, ...]] = set()
    for road in custom_document["roads"]:
        source = road["from_location"]
        target = road["to_location"]
        status = road["status"]

        directional_roads.extend([(source, target), (target, source)])
        initial_facts.update(
            {
                ("connected", source, target),
                ("connected", target, source),
            }
        )

        if status == "clear":
            initial_facts.update({("clear", source, target), ("clear", target, source)})
        else:
            initial_facts.update({("blocked", source, target), ("blocked", target, source)})

    resource_names = list(custom_document["resources"].keys())
    for resource_name, resource_location in custom_document["resources"].items():
        initial_facts.add(("at", resource_name, resource_location))

    for location in custom_document["victims_untreated"]:
        initial_facts.add(("victims_untreated", location))

    goal_conditions = frozenset(
        {("victims_treated", location) for location in custom_document["goal_treated"]}
    )
    actions = generate_domain_actions(
        custom_document["locations"],
        resource_names,
        directional_roads,
    )
    return State(frozenset(initial_facts)), goal_conditions, actions


def load_custom_scenario(file_path: str) -> ScenarioData:
    """Load a custom scenario JSON file and convert it to planner-ready data."""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"Custom scenario file not found: {path}")

    try:
        document_raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Custom scenario JSON is invalid: {exc.msg}") from exc

    if not isinstance(document_raw, dict):
        raise ValueError("Custom scenario file must contain a JSON object.")

    return custom_scenario_from_document(document_raw)


def run_planner(
    initial_state: State,
    goal_conditions: frozenset[tuple[str, ...]],
    actions: list[Action],
    algorithm: AlgorithmName = "bfs",
    heuristic_fn: HeuristicFn | None = None,
    heuristic_name: str = "none",
) -> PlannerResult:
    """Run a graph-search planner and return plan + performance metrics."""
    start_time = time.time()
    heuristic = heuristic_fn or (lambda _state, _goal: 0.0)
    tie_breaker = itertools.count()
    frontier: list[tuple[float, int, int, State, list[Action]]] = []
    best_cost = {initial_state.facts: 0}
    nodes_expanded = 0

    def score_state(state: State, path_cost: int, plan_length: int) -> float:
        if algorithm == "bfs":
            return float(plan_length)
        if algorithm == "ucs":
            return float(path_cost)
        h_val = float(heuristic(state, goal_conditions))
        if algorithm == "gbfs":
            return h_val
        if algorithm == "astar":
            return float(path_cost) + h_val
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    def push_state(state: State, plan: list[Action], path_cost: int) -> None:
        priority = score_state(state, path_cost, len(plan))
        heapq.heappush(frontier, (priority, next(tie_breaker), path_cost, state, plan))

    push_state(initial_state, [], 0)

    while frontier:
        _priority, _order, path_cost, current_state, current_path = heapq.heappop(frontier)
        if path_cost > best_cost.get(current_state.facts, float("inf")):
            continue

        if current_state.satisfies(goal_conditions):
            return {
                "success": True,
                "plan": current_path,
                "nodes_expanded": nodes_expanded,
                "time_taken": time.time() - start_time,
                "plan_length": len(current_path),
                "algorithm": algorithm,
                "heuristic": heuristic_name,
            }

        nodes_expanded += 1
        for action in actions:
            if not action.is_applicable(current_state):
                continue

            next_state = action.execute(current_state)
            next_cost = path_cost + 1
            previous_best = best_cost.get(next_state.facts)
            if previous_best is not None and next_cost >= previous_best:
                continue

            best_cost[next_state.facts] = next_cost
            push_state(next_state, current_path + [action], next_cost)

    return {
        "success": False,
        "nodes_expanded": nodes_expanded,
        "time_taken": time.time() - start_time,
        "algorithm": algorithm,
        "heuristic": heuristic_name,
    }


def visualize_plan_execution(
    initial_state: State,
    plan: list[Action],
    pause_seconds: float = 1.2,
) -> None:
    """Replay a plan and visualize each intermediate state."""
    try:
        from visualization import play_world_states
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "a required dependency"
        print(
            f"\nVisualization skipped: missing dependency '{missing_module}'. "
            "Install requirements with: pip install -r requirements.txt"
        )
        return

    states_with_titles = [(initial_state.facts, "Step 0: Initial State")]
    current_state = initial_state

    for step_num, action in enumerate(plan, 1):
        current_state = action.execute(current_state)
        states_with_titles.append((current_state.facts, f"Step {step_num}: {action}"))

    play_world_states(states_with_titles, pause_seconds=pause_seconds)


def load_scenario_data(scenario_name: str) -> ScenarioData:
    """Load scenario data based on the CLI selection."""
    return get_scenarios()[scenario_name]


def parse_args() -> argparse.Namespace:
    from heuristics import list_heuristics

    scenario_names = tuple(get_scenarios().keys())
    parser = argparse.ArgumentParser(
        description="Classical planner for disaster response scenarios."
    )
    parser.add_argument(
        "--scenario",
        choices=scenario_names,
        default="simple",
        help="Scenario to execute (default: simple).",
    )
    parser.add_argument(
        "--custom-scenario-file",
        type=str,
        default=None,
        help=(
            "Path to a custom scenario JSON file. "
            "If provided, this overrides --scenario."
        ),
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Disable state-by-state visualization.",
    )
    parser.add_argument(
        "--viz-speed",
        type=float,
        default=1.2,
        help="Seconds between visualization frames (default: 1.2).",
    )
    parser.add_argument(
        "--algorithm",
        choices=["bfs", "ucs", "gbfs", "astar"],
        default="bfs",
        help="Search algorithm to execute (default: bfs).",
    )
    parser.add_argument(
        "--heuristic",
        choices=list_heuristics(),
        default="untreated_victims",
        help="Heuristic name for gbfs/astar (default: untreated_victims).",
    )
    return parser.parse_args()


def print_results(results: PlannerResult) -> None:
    if results["success"]:
        print("\n--- Plan Found! ---")
        print(f"Algorithm:      {results['algorithm']}")
        if results.get("heuristic") and results["heuristic"] != "none":
            print(f"Heuristic:      {results['heuristic']}")
        print(f"Time Taken:     {results['time_taken']:.4f} seconds")
        print(f"Nodes Expanded: {results['nodes_expanded']}")
        print(f"Plan Length:    {results['plan_length']} steps\n")

        print("Execution Sequence:")
        for step_num, action in enumerate(results["plan"], 1):
            print(f"  Step {step_num}: {action}")
        return

    print("\nPlanner Failed: No valid plan exists to reach the goal.")


def main() -> None:
    args = parse_args()
    if args.custom_scenario_file:
        initial_state, goal_conditions, all_possible_actions = load_custom_scenario(
            args.custom_scenario_file
        )
    else:
        initial_state, goal_conditions, all_possible_actions = load_scenario_data(args.scenario)
    heuristic_fn: HeuristicFn | None = None
    heuristic_name = "none"

    if args.algorithm in {"gbfs", "astar"}:
        from heuristics import get_heuristic

        heuristic_fn = get_heuristic(args.heuristic)
        heuristic_name = args.heuristic

    results = run_planner(
        initial_state,
        goal_conditions,
        all_possible_actions,
        algorithm=args.algorithm,
        heuristic_fn=heuristic_fn,
        heuristic_name=heuristic_name,
    )
    print_results(results)

    if results["success"] and not args.no_viz:
        visualize_plan_execution(
            initial_state,
            results["plan"],
            pause_seconds=max(args.viz_speed, 0.05),
        )


if __name__ == "__main__":
    main()