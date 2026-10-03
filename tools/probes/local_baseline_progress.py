"""A shared unary rule must count each failing environment during greedy repair."""
from configwitness import Problem, check_proposal, repair
from configwitness.baselines import greedy_local, per_environment


def fixture():
    return {"version": 1, "fields": {"replicas": {"type": "int"}},
            "layers": [{"id": "a", "parents": [], "overrides": {"replicas": 0}},
                       {"id": "b", "parents": [], "overrides": {"replicas": 0}}],
            "environments": [{"id": "a", "layer": "a"}, {"id": "b", "layer": "b"}],
            "constraints": [{"id": "local", "kind": "range", "envs": ["a", "b"], "field": "replicas", "min": 1, "max": 2},
                            {"id": "fleet-total", "kind": "sum", "envs": ["a", "b"], "field": "replicas", "max": 4}],
            "edits": [{"layer": e, "field": "replicas", "options": [{"op": "set", "value": 1, "cost": 1}, {"op": "set", "value": 2, "cost": 2}]} for e in ("a", "b")],
            "protected": []}


def main():
    p = Problem(fixture())
    greedy = greedy_local(p)
    assert greedy["actual_rollout"] == "VALID", "greedy stalled while two independent unary violations were fixable"
    assert greedy["proposal"]["cost"] == 2
    assert check_proposal(p, greedy["proposal"])["accepted"]
    assert per_environment(p)["actual_rollout"] == "VALID"
    assert repair(p)["cost"] == 2
    print("local-baseline-progress PASS: greedy repairs two grouped unary violations at cost=2, matching local-only and fleet optima")


if __name__ == "__main__": main()
