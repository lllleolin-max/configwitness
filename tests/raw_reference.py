"""Raw finite inheritance/predicate/search reference, no production imports.

Path events implement small DAG snapshots; all candidate rows are retained in
the reference so logical shared-prefix accounting can be checked independently.
"""
from copy import deepcopy
from itertools import product
import hashlib
import json
import random


def identity(value):
    return type(value).__name__, value


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def snapshots(data):
    source = {layer["id"]: layer for layer in data["layers"]}
    def events(name):
        layer = source[name]
        inherited = [event for parent in layer["parents"] for event in events(parent)]
        return inherited + [(field, {"layer": name, "value": deepcopy(value)}) for field, value in layer["overrides"].items()]
    layers, provenance = {}, {}
    for name in source:
        paths = events(name)
        raw = {field: event["value"] for field, event in paths}
        layers[name] = {field: value for field, value in raw.items() if type(value) is not dict}
        provenance[name] = {field: [event for f, event in paths if f == field] for field in raw}
    envs = {env["id"]: deepcopy(layers[env["layer"]]) for env in data["environments"]}
    traces = {env["id"]: deepcopy(provenance[env["layer"]]) for env in data["environments"]}
    return layers, envs, traces


def predicate(constraint, envs):
    kind = constraint["kind"]
    if kind == "failover":
        a, b = envs[constraint["primary"]], envs[constraint["backup"]]
        n, m = a.get(constraint["replicas"]), b.get(constraint["replicas"])
        regions = [a.get(constraint["region"]), b.get(constraint["region"])]
        numeric = type(n) is int and type(m) is int and n >= 0 and m >= 0
        textual = all(type(value) is str for value in regions)
        good = numeric and textual and (n == 0 or (m >= constraint["min_backup"] and regions[0] != regions[1]))
        return good, {"primary_replicas": n, "backup_replicas": m, "regions": regions}
    field = constraint["field"]
    values = [envs[name].get(field) for name in constraint["envs"]]
    present = all(field in envs[name] for name in constraint["envs"])
    if kind in ("range", "sum"):
        if not present or not all(type(value) is int for value in values):
            return False, {"values": values, "reason": "integer values required"}
        measured = [sum(values)] if kind == "sum" else values
        good = all(value >= constraint.get("min", value) and value <= constraint.get("max", value) for value in measured)
        return good, {"values": values, "total": sum(values)}
    if kind == "allowed":
        good = present and all(any(identity(value) == identity(option) for option in constraint["values"]) for value in values)
    elif kind == "equal":
        good = present and all(identity(value) == identity(values[0]) for value in values)
    else:
        good = present and all(identity(a) != identity(b) for i, a in enumerate(values) for b in values[i + 1:])
    return good, {"values": values}


def validation(data):
    _, envs, _ = snapshots(data)
    schema = [{"env": name, "field": field, "reason": "required field missing or unset"}
              for name, values in envs.items() for field, spec in data["fields"].items()
              if spec.get("required", True) and field not in values]
    bad = []
    for constraint in data["constraints"]:
        good, evidence = predicate(constraint, envs)
        if not good:
            bad.append({"id": constraint["id"], "kind": constraint["kind"], "evidence": evidence})
    return {"status": "INVALID" if schema or bad else "VALID", "schema_errors": schema, "violations": bad, "configs": envs}


def trace(data, env, field):
    _, envs, traces = snapshots(data)
    events = traces[env].get(field, [])
    return {"env": env, "field": field, "present": field in envs[env], "value": envs[env].get(field),
            "winner": events[-1] if events else None, "providers": events}


class Reference:
    def __init__(self, data):
        self.data = deepcopy(data)
        self.digest = hashlib.sha256(canonical(data).encode()).hexdigest()
        old_layers, old_envs, _ = snapshots(data)
        self.rows = []
        for choices in product(*(range(-1, len(edit["options"])) for edit in data["edits"])):
            changed = deepcopy(data)
            overrides = {layer["id"]: layer["overrides"] for layer in changed["layers"]}
            edits = []
            for edit, choice in zip(data["edits"], choices):
                if choice < 0:
                    continue
                option = edit["options"][choice]
                edits.append({"layer": edit["layer"], "field": edit["field"], **option})
                dest, field = overrides[edit["layer"]], edit["field"]
                if option["op"] == "remove":
                    dest.pop(field, None)
                else:
                    dest[field] = option["value"] if option["op"] == "set" else {"$unset": True}
            layers, envs, _ = snapshots(changed)
            allowed = all(not spec.get("required", True) or field in values
                          for values in envs.values() for field, spec in data["fields"].items())
            for pin in data["protected"]:
                old = (old_layers if "layer" in pin else old_envs)[pin.get("layer", pin.get("env"))]
                new = (layers if "layer" in pin else envs)[pin.get("layer", pin.get("env"))]
                field = pin["field"]
                allowed &= (field in old, identity(old.get(field))) == (field in new, identity(new.get(field)))
            satisfied = {c["id"] for c in data["constraints"] if predicate(c, envs)[0]}
            self.rows.append((allowed, satisfied, {"version": 1, "source_sha256": self.digest,
                                                   "cost": sum(edit["cost"] for edit in edits), "edits": edits}))

    def search(self, ids, limit, used=0, optimize=False, max_repairs=20):
        required = set(ids)
        feasible = []
        complete = True
        for allowed, satisfied, proposed in self.rows:
            if used == limit:
                complete = False
                break
            used += 1
            if allowed and required <= satisfied:
                if not optimize:
                    return {"status": "SAT", "witness": deepcopy(proposed), "states": used}
                feasible.append(proposed)
        if not optimize:
            return {"status": "UNSAT" if complete else "UNKNOWN", "witness": None, "states": used}
        least = min((p["cost"] for p in feasible), default=None)
        best = [p for p in feasible if p["cost"] == least]
        return {"status": ("OPTIMAL" if best else "UNSAT") if complete else "UNKNOWN",
                "cost": least, "repairs": deepcopy(best[:max_repairs]), "states": used,
                "tie_count": len(best) if complete else None, "ties_complete": complete and len(best) <= max_repairs,
                "search_complete": complete}

    def solve(self, limit):
        return self.search([c["id"] for c in self.data["constraints"]], limit)

    def repair(self, limit, max_repairs=20):
        return self.search([c["id"] for c in self.data["constraints"]], limit, optimize=True, max_repairs=max_repairs)

    def conflict(self, limit):
        data = self.data
        ids = [c["id"] for c in data["constraints"]]
        result = self.search(ids, limit)
        premises = {"source_sha256": self.digest, "edit_scope": data.get("edit_scope", "leaf"),
                    "protected": data["protected"], "universe": data["edits"],
                    "fixed": "all schema, inheritance, unedited overrides and protection snapshots"}
        used = result["states"]
        def incomplete(status):
            return {"status": status, "constraints": [], "minimal": False, "premises": deepcopy(premises), "states": used}
        if result["status"] != "UNSAT":
            return incomplete(result["status"])
        for ident in list(ids):
            reduced = [value for value in ids if value != ident]
            result = self.search(reduced, limit, used)
            used = result["states"]
            if result["status"] == "UNKNOWN":
                return incomplete("UNKNOWN")
            if result["status"] == "UNSAT":
                ids = reduced
        witnesses = {}
        for ident in ids:
            result = self.search([value for value in ids if value != ident], limit, used)
            used = result["states"]
            if result["status"] != "SAT":
                return incomplete("UNKNOWN")
            witnesses[ident] = result["witness"]
        return {"status": "UNSAT", "constraints": ids, "minimal": True, "premises": deepcopy(premises),
                "removal_witnesses": witnesses, "premises_alone_unsatisfiable": not ids, "states": used}


def cases(seed=781093, count=108):
    rng = random.Random(seed)
    for index in range(count):
        data = {"version": 1, "description": f"finite raw scenario {index}", "edit_scope": "declared-layers" if index % 2 == 0 else "leaf",
                "fields": {"n": {"type": "int", "nullable": True, "required": index % 3 != 0},
                           "region": {"type": "string", "nullable": True}, "flag": {"type": "bool", "nullable": True, "required": False}},
                "layers": [{"id": "base", "parents": [], "overrides": {"n": rng.choice([0, 1, 2, None]), "region": "east", "flag": True}},
                           {"id": "a", "parents": ["base"], "overrides": {"n": rng.choice([1, 3, None])}},
                           {"id": "b", "parents": ["base"], "overrides": {"region": rng.choice(["east", "west", None])}},
                           {"id": "tip", "parents": ["a", "b"] if index % 4 else ["b", "a"], "overrides": {}},
                           {"id": "other", "parents": ["base"], "overrides": {"n": rng.choice([0, 2, None]), "region": "west"}}],
                "environments": [{"id": "租户-Δ", "layer": "tip"}, {"id": "backup", "layer": "other"}],
                "constraints": [], "edits": [], "protected": []}
        if index % 7 == 0:
            data["layers"][3]["overrides"]["flag"] = {"$unset": True}
        targets = [("base", "n"), ("a", "region"), ("other", "flag")] if index % 2 == 0 else [("tip", "n"), ("other", "region"), ("tip", "flag")]
        for layer, field in targets:
            value = {"n": rng.choice([0, 2, None]), "region": rng.choice(["west", "north", None]), "flag": rng.choice([False, True, None])}[field]
            data["edits"].append({"layer": layer, "field": field, "options": [
                {"op": "set", "value": value, "cost": rng.randrange(3)}, {"op": "unset", "cost": 0}, {"op": "remove", "cost": rng.randrange(2)}]})
        envs = ["租户-Δ", "backup"]
        data["constraints"] = [
            {"id": "range", "kind": "range", "envs": envs, "field": "n", "min": 0, "max": rng.randint(1, 4)},
            {"id": "sum", "kind": "sum", "envs": envs, "field": "n", "max": rng.randint(0, 6)},
            {"id": "allowed", "kind": "allowed", "envs": envs, "field": "flag", "values": [True] if index % 3 else [False, None]},
            {"id": "equal", "kind": "equal", "envs": envs, "field": "flag" if index % 2 else "n"},
            {"id": "distinct", "kind": "distinct", "envs": envs, "field": "region"},
            {"id": "failover", "kind": "failover", "primary": envs[0], "backup": envs[1], "replicas": "n", "region": "region", "min_backup": rng.randint(1, 2)}]
        data["constraints"] += [{"id": f"extra-{i}", "kind": "range", "envs": [envs[i % 2]], "field": "n", "min": -2} for i in range(index % 4)]
        if index % 5 == 0:
            data["protected"] = [{"layer": "base", "field": "n"}]
        elif index % 5 == 1:
            data["protected"] = [{"env": envs[1], "field": "region"}]
        rng.shuffle(data["constraints"])
        rng.shuffle(data["layers"])
        yield data
