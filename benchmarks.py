import argparse
import csv
import json
from statistics import mean
from typing import TypedDict

from heuristics import get_heuristic, list_heuristics
from planner import AlgorithmName, get_scenarios, run_planner


class BenchmarkRow(TypedDict):
    scenario: str
    algorithm: str
    heuristic: str
    runs: int
    success_rate: float
    mean_time: float
    mean_nodes_expanded: float
    mean_plan_length: float


def run_benchmarks(
    repeats: int,
    heuristic_name: str,
    algorithms: list[AlgorithmName] | None = None,
) -> list[BenchmarkRow]:
    selected_algorithms = algorithms or ["bfs", "ucs", "gbfs", "astar"]
    rows: list[BenchmarkRow] = []
    heuristic_fn = get_heuristic(heuristic_name)

    for scenario_name, scenario_data in get_scenarios().items():
        initial_state, goal_conditions, all_possible_actions = scenario_data
        for algorithm in selected_algorithms:
            success_count = 0
            times: list[float] = []
            nodes_expanded: list[int] = []
            plan_lengths: list[int] = []

            for _ in range(repeats):
                uses_heuristic = algorithm in {"gbfs", "astar"}
                result = run_planner(
                    initial_state,
                    goal_conditions,
                    all_possible_actions,
                    algorithm=algorithm,
                    heuristic_fn=heuristic_fn if uses_heuristic else None,
                    heuristic_name=heuristic_name if uses_heuristic else "none",
                )
                success = bool(result.get("success"))
                if success:
                    success_count += 1
                    plan_lengths.append(int(result.get("plan_length", 0)))
                times.append(float(result["time_taken"]))
                nodes_expanded.append(int(result["nodes_expanded"]))

            row: BenchmarkRow = {
                "scenario": scenario_name,
                "algorithm": algorithm,
                "heuristic": heuristic_name if algorithm in {"gbfs", "astar"} else "none",
                "runs": repeats,
                "success_rate": success_count / repeats,
                "mean_time": mean(times),
                "mean_nodes_expanded": mean(nodes_expanded),
                "mean_plan_length": mean(plan_lengths) if plan_lengths else 0.0,
            }
            rows.append(row)
    return rows


def print_table(rows: list[BenchmarkRow]) -> None:
    headers = (
        "scenario",
        "algorithm",
        "heuristic",
        "runs",
        "success_rate",
        "mean_time",
        "mean_nodes_expanded",
        "mean_plan_length",
    )
    print(" | ".join(headers))
    print("-" * 108)
    for row in rows:
        print(
            " | ".join(
                [
                    row["scenario"],
                    row["algorithm"],
                    row["heuristic"],
                    str(row["runs"]),
                    f"{row['success_rate']:.2f}",
                    f"{row['mean_time']:.4f}",
                    f"{row['mean_nodes_expanded']:.2f}",
                    f"{row['mean_plan_length']:.2f}",
                ]
            )
        )


def write_json(rows: list[BenchmarkRow], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(rows, file, indent=2)


def write_csv(rows: list[BenchmarkRow], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "scenario",
                "algorithm",
                "heuristic",
                "runs",
                "success_rate",
                "mean_time",
                "mean_nodes_expanded",
                "mean_plan_length",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark planner algorithms across built-in scenarios."
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Runs per scenario-algorithm pair (default: 5).",
    )
    parser.add_argument(
        "--heuristic",
        choices=list_heuristics(),
        default="untreated_victims",
        help="Heuristic for gbfs/astar (default: untreated_victims).",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        choices=["bfs", "ucs", "gbfs", "astar"],
        default=["bfs", "ucs", "gbfs", "astar"],
        help="Algorithms to include (default: all).",
    )
    parser.add_argument("--output-json", help="Optional path to write JSON results.")
    parser.add_argument("--output-csv", help="Optional path to write CSV results.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = run_benchmarks(
        repeats=max(args.repeats, 1),
        heuristic_name=args.heuristic,
        algorithms=args.algorithms,
    )
    print_table(rows)

    if args.output_json:
        write_json(rows, args.output_json)
        print(f"\nWrote JSON report to {args.output_json}")
    if args.output_csv:
        write_csv(rows, args.output_csv)
        print(f"Wrote CSV report to {args.output_csv}")


if __name__ == "__main__":
    main()
