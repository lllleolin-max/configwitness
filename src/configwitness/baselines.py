"""Executable declared baselines, not emulations/benchmarks of CUE or OPA."""
from .engine import (Budget, admissible, apply_edits, candidates, proposal, search, validate)
from .resolve import resolve
from .constraints import violations


def _local(problem):
    return [c for c in problem.data["constraints"] if c["kind"] in ("range", "allowed")]


def per_environment(problem, max_states=100_000):
    """Cheapest assignment satisfying all unary constraints in the SAME universe.

    Relational predicates are deliberately omitted; protections/schema remain.
    Only the first local optimum is selected, so ties have no fleet-aware ranking.
    """
    result = search(problem, _local(problem), Budget(max_states), True, 1)
    if result["repairs"]:
        result["actual_rollout"] = validate(apply_edits(problem, result["repairs"][0]["edits"]))["status"]
    return result


def greedy_local(problem, max_states=100_000):
    """Single-target changes that strictly reduce unary violation count.

    Same domains, costs, schema/protections. Stops at a local minimum; no proof.
    Full assignment enumeration supplies neighbors, charged against work budget.
    """
    budget = Budget(max_states)
    before = resolve(problem)
    current, edits, cost = problem, [], 0
    def score(p):
        _, envs = resolve(p)
        return len(violations(_local(problem), {e: r["values"] for e, r in envs.items()}))
    while score(current):
        neighbors = []
        current_targets = {(e["layer"], e["field"]): e for e in edits}
        for nxt, expense in candidates(problem):
            if not budget.take():
                return {"status": "UNKNOWN", "states": budget.used, "proposal": proposal(problem, edits, cost), "actual_rollout": validate(current)["status"]}
            next_targets = {(e["layer"], e["field"]): e for e in nxt}
            differing = sum(current_targets.get(t) != next_targets.get(t) for t in set(current_targets) | set(next_targets))
            if differing != 1:
                continue
            p = apply_edits(problem, nxt)
            allowed, _ = admissible(problem, p, before)
            if allowed and score(p) < score(current):
                neighbors.append((score(p), expense, nxt, p))
        if not neighbors:
            break
        _, cost, edits, current = min(neighbors, key=lambda x: (x[0], x[1]))
    return {"status": "LOCAL_STOP", "states": budget.used, "proposal": proposal(problem, edits, cost), "actual_rollout": validate(current)["status"]}
