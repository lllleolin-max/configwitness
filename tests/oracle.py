"""Small exhaustive reference implementation, independent of all production modules.

This deliberately trades speed for auditable loops. No checker/solver imports.
"""
import copy
import itertools
import json


def identity(v):
    return json.dumps(v, sort_keys=True)


def resolve(data):
    layers = {l["id"]: l for l in data["layers"]}
    def walk(n):
        raw = {}
        for parent in layers[n]["parents"]:
            raw.update(walk(parent))
        raw.update(layers[n]["overrides"])
        return raw
    raw = {n: walk(n) for n in layers}
    vals = {n: {f: v for f, v in r.items() if type(v) is not dict} for n, r in raw.items()}
    return vals, {e["id"]: vals[e["layer"]] for e in data["environments"]}


def valid_constraint(c, envs):
    if c["kind"] == "failover":
        a, b = envs[c["primary"]], envs[c["backup"]]
        r, s, x, y = a.get(c["replicas"]), b.get(c["replicas"]), a.get(c["region"]), b.get(c["region"])
        if type(r) is not int or type(s) is not int or r < 0 or s < 0 or type(x) is not str or type(y) is not str:
            return False
        if r == 0:
            return True
        return s >= c["min_backup"] and x != y
    if any(c["field"] not in envs[e] for e in c["envs"]):
        return False
    vals = [envs[e][c["field"]] for e in c["envs"]]
    kind = c["kind"]
    if kind in ("range", "sum"):
        if any(type(x) is not int for x in vals):
            return False
        if kind == "sum":
            vals = [sum(vals)]
        for x in vals:
            if "min" in c and x < c["min"]:
                return False
            if "max" in c and x > c["max"]:
                return False
        return True
    if kind == "equal":
        return all(identity(x) == identity(vals[0]) for x in vals)
    if kind == "distinct":
        return all(identity(x) != identity(y) for i, x in enumerate(vals) for y in vals[i+1:])
    return all(any(identity(x) == identity(y) for y in c["values"]) for x in vals)


def enumerate_feasible(data, constraint_ids=None):
    orig_l, orig_e = resolve(data)
    feasible = []
    for choices in itertools.product(*[range(-1, len(e["options"])) for e in data["edits"]]):
        changed = copy.deepcopy(data)
        layers = {l["id"]: l for l in changed["layers"]}
        edits, cost = [], 0
        for target, selected in zip(data["edits"], choices):
            if selected == -1:
                continue
            op = target["options"][selected]
            cost += op["cost"]
            edits.append({"layer": target["layer"], "field": target["field"], **op})
            dest = layers[target["layer"]]["overrides"]
            if op["op"] == "remove":
                dest.pop(target["field"], None)
            else:
                dest[target["field"]] = op["value"] if op["op"] == "set" else {"$unset": True}
        new_l, new_e = resolve(changed)
        if any(s.get("required", True) and f not in env for env in new_e.values() for f, s in data["fields"].items()):
            continue
        protected = True
        for p in data["protected"]:
            if "env" in p:
                a, b = orig_e[p["env"]], new_e[p["env"]]
            else:
                a, b = orig_l[p["layer"]], new_l[p["layer"]]
            f = p["field"]
            protected &= (f in a, identity(a.get(f))) == (f in b, identity(b.get(f)))
        if not protected:
            continue
        constraints = [c for c in data["constraints"] if constraint_ids is None or c["id"] in constraint_ids]
        if all(valid_constraint(c, new_e) for c in constraints):
            feasible.append((cost, edits))
    return feasible
