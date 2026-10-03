"""Independent feasibility checker: no engine resolver/predicate/search imports.

It checks a proposed edit's feasibility and cost, not its global optimality.
"""
import copy
import hashlib
import json
from .model import InputError, Problem


def _values(problem):
    remaining, states = dict(problem.layers), {}
    while remaining:
        ready = [n for n, l in remaining.items() if all(p in states for p in l["parents"])]
        if not ready:
            raise InputError("checker: inheritance cycle")
        for n in ready:
            l = remaining.pop(n)
            raw = {}
            for p in l["parents"]:
                raw.update(states[p])
            raw.update(l["overrides"])
            states[n] = raw
    layers = {n: {f: v for f, v in raw.items() if not isinstance(v, dict)} for n, raw in states.items()}
    return layers, {e: layers[l] for e, l in problem.envs.items()}


def _identity(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=True)


def _predicate(c, configs):
    k = c["kind"]
    if k == "failover":
        a, b = configs[c["primary"]], configs[c["backup"]]
        r, s = a.get(c["replicas"]), b.get(c["replicas"])
        x, y = a.get(c["region"]), b.get(c["region"])
        if type(r) is not int or type(s) is not int or r < 0 or s < 0 or type(x) is not str or type(y) is not str:
            return False
        return r == 0 or (s >= c["min_backup"] and x != y)
    f = c["field"]
    if any(f not in configs[e] for e in c["envs"]):
        return False
    v = [configs[e][f] for e in c["envs"]]
    if k in ("range", "sum"):
        if any(type(x) is not int for x in v):
            return False
        v = [sum(v)] if k == "sum" else v
        return all(x >= c.get("min", x) and x <= c.get("max", x) for x in v)
    if k == "allowed":
        return all(_identity(x) in [_identity(y) for y in c["values"]] for x in v)
    if k == "equal":
        return len({_identity(x) for x in v}) == 1
    return len({_identity(x) for x in v}) == len(v)


def check_proposal(problem, proposed):
    """Reject forgeries, unknown options, cost changes and protected-value changes."""
    try:
        if type(proposed) is not dict or set(proposed) != {"version", "source_sha256", "cost", "edits"}:
            raise InputError("checker: proposal shape")
        digest = hashlib.sha256(json.dumps(problem.data, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
        if type(proposed["version"]) is not int or proposed["version"] != 1 or proposed["source_sha256"] != digest:
            raise InputError("checker: source/version mismatch")
        if type(proposed["cost"]) is not int or proposed["cost"] < 0 or type(proposed["edits"]) is not list:
            raise InputError("checker: cost/edits type")
        d = copy.deepcopy(problem.data)
        targets = {(e["layer"], e["field"]): e["options"] for e in d["edits"]}
        layers = {l["id"]: l for l in d["layers"]}
        seen, cost = set(), 0
        for e in proposed["edits"]:
            if type(e) is not dict or not {"layer", "field", "op", "cost"} <= set(e):
                raise InputError("checker: edit shape")
            t = (e["layer"], e["field"])
            op = {k: v for k, v in e.items() if k not in ("layer", "field")}
            if t in seen or t not in targets or _identity(op) not in [_identity(o) for o in targets[t]]:
                raise InputError("checker: undeclared/duplicate option")
            seen.add(t)
            cost += op["cost"]
            overrides = layers[t[0]]["overrides"]
            if op["op"] == "remove":
                overrides.pop(t[1], None)
            elif op["op"] == "unset":
                overrides[t[1]] = {"$unset": True}
            else:
                overrides[t[1]] = op["value"]
        if cost != proposed["cost"]:
            raise InputError("checker: wrong declared cost")
        changed = Problem(d)
        old_l, old_e = _values(problem)
        new_l, new_e = _values(changed)
        errors = []
        for p in d["protected"]:
            k = "env" if "env" in p else "layer"
            a = (old_e if k == "env" else old_l)[p[k]]
            b = (new_e if k == "env" else new_l)[p[k]]
            f = p["field"]
            if (f in a, _identity(a.get(f))) != (f in b, _identity(b.get(f))):
                errors.append("protected value changed: " + _identity(p))
        for e, config in new_e.items():
            for f, spec in problem.fields.items():
                if spec.get("required", True) and f not in config:
                    errors.append(f"missing required {e}.{f}")
        errors.extend("constraint failed: " + c["id"] for c in d["constraints"] if not _predicate(c, new_e))
        return {"accepted": not errors, "errors": errors, "cost": cost, "configs": new_e}
    except (InputError, KeyError, TypeError) as exc:
        return {"accepted": False, "errors": [str(exc)]}
