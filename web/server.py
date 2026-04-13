"""Serve the static showcase UI and a JSON API for live planner runs (FastAPI + uvicorn).

Run from the repository root:

    python web/server.py

Imports resolve against the repo root via sys.path insertion below.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

WEB_DIR = Path(__file__).resolve().parent
REPO_ROOT = WEB_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from starlette.requests import Request  # noqa: E402

from domain_models import Action, State  # noqa: E402
from planner import (  # noqa: E402
    AlgorithmName,
    PlannerResult,
    custom_scenario_from_document,
    load_scenario_data,
    run_planner,
)


def _facts_to_jsonable(facts: frozenset[tuple[str, ...]]) -> list[list[str]]:
    return [list(f) for f in sorted(facts, key=lambda t: t)]


def _plan_steps(initial_state: State, plan: list[Action]) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = [
        {"title": "Step 0: Initial State", "facts": _facts_to_jsonable(initial_state.facts)}
    ]
    current = initial_state
    for step_num, action in enumerate(plan, 1):
        current = action.execute(current)
        steps.append(
            {
                "title": f"Step {step_num}: {action}",
                "facts": _facts_to_jsonable(current.facts),
            }
        )
    return steps


def _build_response_body(
    initial_state: State,
    results: PlannerResult,
) -> dict[str, object]:
    body: dict[str, object] = {
        "success": results["success"],
        "algorithm": results["algorithm"],
        "heuristic": results.get("heuristic", "none"),
        "nodes_expanded": results["nodes_expanded"],
        "time_taken": results["time_taken"],
    }
    if results["success"]:
        plan = results["plan"]
        body["plan_length"] = results["plan_length"]
        body["plan"] = [str(a) for a in plan]
        body["steps"] = _plan_steps(initial_state, plan)
    return body


class PlanRequest(BaseModel):
    algorithm: str = "bfs"
    heuristic: str = "untreated_victims"
    scenario: str = "simple"
    custom_scenario: dict[str, Any] | None = None


app = FastAPI(title="AIFA showcase API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    if not errors:
        detail = "Invalid request body."
    else:
        first = errors[0]
        loc = " -> ".join(str(part) for part in first.get("loc", ()))
        msg = str(first.get("msg", "Invalid value"))
        detail = f"{loc}: {msg}" if loc else msg
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": detail},
    )


@app.post("/api/plan")
async def api_plan(body: PlanRequest) -> JSONResponse:
    algorithm_raw = body.algorithm
    heuristic_raw = body.heuristic

    if algorithm_raw not in ("bfs", "ucs", "gbfs", "astar"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": f"Unknown algorithm '{algorithm_raw}'."},
        )
    algorithm = cast(AlgorithmName, algorithm_raw)

    from heuristics import get_heuristic

    heuristic_fn = None
    heuristic_name = "none"
    if algorithm in ("gbfs", "astar"):
        try:
            heuristic_fn = get_heuristic(heuristic_raw)
            heuristic_name = heuristic_raw
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": str(exc)},
            )

    try:
        if body.custom_scenario is not None:
            initial_state, goal_conditions, actions = custom_scenario_from_document(
                body.custom_scenario
            )
        else:
            scenario_name = body.scenario
            if scenario_name not in ("simple", "complex"):
                msg = (
                    f"Unknown scenario '{scenario_name}'. "
                    "Use 'simple' or 'complex', or send custom_scenario."
                )
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": msg},
                )
            initial_state, goal_conditions, actions = load_scenario_data(scenario_name)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(exc)},
        )

    results = run_planner(
        initial_state,
        goal_conditions,
        actions,
        algorithm=algorithm,
        heuristic_fn=heuristic_fn,
        heuristic_name=heuristic_name,
    )
    response = _build_response_body(initial_state, results)
    status = 200 if results["success"] else 422
    return JSONResponse(status_code=status, content=response)


app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")


def main() -> None:
    import uvicorn

    host = "127.0.0.1"
    port = 3000
    print(f"Showcase server at http://{host}:{port}/ (repo root: {REPO_ROOT})")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
