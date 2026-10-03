"""Long acyclic chains must not depend on Python's recursion limit."""
from configwitness import InputError, Problem, validate, trace, repair, check_proposal


def main():
    layers = [{"id": "n0", "parents": [], "overrides": {"replicas": 1}}]
    for i in range(1, 1500):
        layers.append({"id": f"n{i}", "parents": [f"n{i-1}"], "overrides": {}})
    layers.reverse()  # Input layer-list order has no semantic precedence.
    d = {"version": 1, "fields": {"replicas": {"type": "int"}}, "layers": layers,
         "environments": [{"id": "prod", "layer": "n1499"}], "constraints": [], "edits": [], "protected": []}
    p = Problem(d)
    assert validate(p)["status"] == "VALID"
    assert trace(p, "prod", "replicas")["winner"]["layer"] == "n0"
    assert check_proposal(p, repair(p)["repairs"][0])["accepted"]
    # A small, densely repeated diamond should validate without expanding traces.
    d["layers"] = [{"id": "root", "parents": [], "overrides": {"replicas": 1}}]
    prior = ["root"]
    for i in range(20):
        nxt = [f"a{i}", f"b{i}"]
        d["layers"] += [{"id": n, "parents": prior, "overrides": {}} for n in nxt]
        prior = nxt
    d["environments"][0]["layer"] = prior[-1]
    p = Problem(d)
    assert validate(p)["status"] == "VALID"
    try:
        trace(p, "prod", "replicas")
    except InputError as exc:
        assert "trace" in str(exc)
    else:
        raise AssertionError("exponential provenance expanded without explicit resource limit")
    print("deep-inheritance PASS: 1500 layers validate/trace/repair/check; diamond validates without trace expansion and oversized exact trace rejects")


if __name__ == "__main__": main()
