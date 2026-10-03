"""Fleet predicates evaluate concrete values only. Missing/null arithmetic fails."""
from .model import token


def evaluate(c, configs):
    if c["kind"] == "failover":
        p, b = configs[c["primary"]], configs[c["backup"]]
        count = p.get(c["replicas"])
        backup = b.get(c["replicas"])
        regions = (p.get(c["region"]), b.get(c["region"]))
        good = (type(count) is int and count >= 0 and type(backup) is int and backup >= 0
                and all(type(r) is str for r in regions)
                and (count == 0 or (backup >= c["min_backup"] and regions[0] != regions[1])))
        return good, {"primary_replicas": count, "backup_replicas": backup, "regions": list(regions)}
    f = c["field"]
    values = [configs[e].get(f) for e in c["envs"]]
    present = all(f in configs[e] for e in c["envs"])
    kind = c["kind"]
    if kind in ("range", "sum"):
        if not present or any(type(v) is not int for v in values):
            return False, {"values": values, "reason": "integer values required"}
        numbers = [sum(values)] if kind == "sum" else values
        good = all(("min" not in c or v >= c["min"]) and ("max" not in c or v <= c["max"]) for v in numbers)
        return good, {"values": values, "total": sum(values)}
    if kind == "allowed":
        good = present and all(token(v) in {token(x) for x in c["values"]} for v in values)
    elif kind == "equal":
        good = present and len({token(v) for v in values}) == 1
    else:
        good = present and len({token(v) for v in values}) == len(values)
    return good, {"values": values}


def violations(constraints, configs):
    result = []
    for c in constraints:
        ok, detail = evaluate(c, configs)
        if not ok:
            result.append({"id": c["id"], "kind": c["kind"], "evidence": detail})
    return result
