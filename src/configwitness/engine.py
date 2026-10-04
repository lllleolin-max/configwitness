"""Bounded enumeration over edits to real layers; never edits resolved maps."""
from __future__ import annotations
import copy
import hashlib
import itertools
import json
import sys
from . import constraints as predicates
from .model import InputError, Problem, integer, token
from .resolve import resolve, schema_errors
from .constraints import violations


def fingerprint(problem):
    return hashlib.sha256(json.dumps(problem.data, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def validate(problem):
    _, envs = resolve(problem)
    errors = schema_errors(problem, envs)
    bad = violations(problem.data["constraints"], {e: r["values"] for e, r in envs.items()})
    return {"status": "INVALID" if errors or bad else "VALID", "schema_errors": errors,
            "violations": bad, "configs": {e: r["values"] for e, r in envs.items()}}


def trace(problem, env, field):
    if env not in problem.envs or field not in problem.fields:
        raise InputError("unknown trace environment/field")
    _, envs = resolve(problem, include_trace=True)
    events = envs[env]["trace"].get(field, [])
    return {"env": env, "field": field, "present": field in envs[env]["values"],
            "value": envs[env]["values"].get(field), "winner": events[-1] if events else None,
            "providers": events}


def apply_edits(problem, edits):
    """Apply declared option records [{layer, field, op, value?, cost}]."""
    d = copy.deepcopy(problem.data)
    layers = {l["id"]: l for l in d["layers"]}
    seen = set()
    for e in edits:
        target = (e["layer"], e["field"])
        if target in seen:
            raise InputError("duplicate applied edit")
        seen.add(target)
        options = [t for t in problem.data["edits"] if (t["layer"], t["field"]) == target]
        op = {k: v for k, v in e.items() if k not in ("layer", "field")}
        if not options or not any(json.dumps(op, sort_keys=True) == json.dumps(o, sort_keys=True) for o in options[0]["options"]):
            raise InputError("edit is not a declared option")
        overrides = layers[e["layer"]]["overrides"]
        if e["op"] == "remove":
            overrides.pop(e["field"], None)
        else:
            overrides[e["field"]] = e["value"] if e["op"] == "set" else {"$unset": True}
    return Problem(d)


def protections_hold(original, modified, before=None, after=None):
    before = before or resolve(original)
    after = after or resolve(modified)
    for p in original.data["protected"]:
        index, key = (1, "env") if "env" in p else (0, "layer")
        a, b = before[index][p[key]]["values"], after[index][p[key]]["values"]
        f = p["field"]
        if (f in a, token(a.get(f))) != (f in b, token(b.get(f))):
            return False
    return True


def candidates(problem):
    universe = problem.data["edits"]
    for choice in itertools.product(*[[None] + e["options"] for e in universe]):
        edits = [{"layer": e["layer"], "field": e["field"], **o}
                 for e, o in zip(universe, choice) if o is not None]
        yield edits, sum(e["cost"] for e in edits)


class Budget:
    def __init__(self, limit):
        integer(limit, "max_states", 0)
        self.limit, self.used = limit, 0

    def take(self):
        if self.used >= self.limit:
            return False
        self.used += 1
        return True


def admissible(problem, edited, original_resolution):
    resolution = resolve(edited)
    return (not schema_errors(edited, resolution[1])
            and protections_hold(problem, edited, original_resolution, resolution)), resolution


def proposal(problem, edits, cost):
    return {"version": 1, "source_sha256": fingerprint(problem), "cost": cost, "edits": edits}


_CACHE_MAX_STATES = 4096
_CACHE_MAX_BYTES = 1_048_576
_MISSING = object()


def _bounded_size(value, remaining):
    """Conservative container/scalar accounting, stopping once over budget.

    Counting shared scalars repeatedly overestimates retention. Resolutions and
    the index have fixed shallow structure, irrespective of inheritance depth.
    This is interpreter object accounting, not an OS/RSS or transient-work cap.
    """
    size = sys.getsizeof(value, remaining + 1)
    if size > remaining:
        return size
    children = (item for pair in value.items() for item in pair) if type(value) is dict else iter(value) if type(value) in (list, tuple) else ()
    for child in children:
        size += _bounded_size(child, remaining - size)
        if size > remaining:
            break
    return size


class _ConflictCache:
    """One immutable source and full predicate universe, bounded lazy entries."""

    def __init__(self, problem, limit):
        self.problem = problem
        self.constraints = problem.data["constraints"]
        capacity = min(_CACHE_MAX_STATES, limit)
        combinations = 1
        for edit in problem.data["edits"]:
            combinations = min(capacity, combinations * (len(edit["options"]) + 1))
        capacity = min(capacity, combinations)
        self.entries = [_MISSING] * capacity
        self.before = resolve(problem)
        self.index = {id(c): i for i, c in enumerate(self.constraints)}
        self.width = (len(self.constraints) + 7) // 8
        # Reserve context overhead, then include the retained original resolution,
        # identity index, allocated slot array and every admitted byte vector.
        self.bytes = 4096 + sys.getsizeof(self.entries, _CACHE_MAX_BYTES + 1)
        self.bytes += _bounded_size(self.before, max(0, _CACHE_MAX_BYTES - self.bytes))
        self.bytes += _bounded_size(self.index, max(0, _CACHE_MAX_BYTES - self.bytes))
        if self.bytes > _CACHE_MAX_BYTES:
            self.before, self.index, self.entries = None, None, []
            self.bytes = 0  # Disabled: no admitted snapshot/index/state content.
        self.entry_bound = max(sys.getsizeof(None, _CACHE_MAX_BYTES + 1),
                               sys.getsizeof(b"", _CACHE_MAX_BYTES + 1) + self.width)

    def mask(self, problem, constraints):
        if problem is not self.problem or self.index is None:
            return None
        mask = 0
        for c in constraints:
            i = self.index.get(id(c))
            if i is None or self.constraints[i] is not c:
                return None  # A changed/foreign predicate needs ordinary evaluation.
            mask |= 1 << i
        return mask

    def satisfies(self, ordinal, edits, mask):
        if ordinal >= len(self.entries):
            return None
        value = self.entries[ordinal]
        if value is _MISSING:
            if self.bytes + self.entry_bound > _CACHE_MAX_BYTES:
                return None
            edited = apply_edits(self.problem, edits)
            allowed, (_, envs) = admissible(self.problem, edited, self.before)
            value = None
            if allowed:
                configs = {e: r["values"] for e, r in envs.items()}
                bad = 0
                for i, c in enumerate(self.constraints):
                    if not predicates.evaluate(c, configs)[0]:
                        bad |= 1 << i
                value = bad.to_bytes(self.width, "little")
            size = sys.getsizeof(value, _CACHE_MAX_BYTES + 1)
            if self.bytes + size <= _CACHE_MAX_BYTES:
                self.entries[ordinal] = value
                self.bytes += size
            return value is not None and not (int.from_bytes(value, "little") & mask)
        return value is not None and not (int.from_bytes(value, "little") & mask)


def search(problem, constraints, budget, optimize=False, max_repairs=20):
    return _search(problem, constraints, budget, optimize, max_repairs)


def _search(problem, constraints, budget, optimize=False, max_repairs=20, cache=None):
    mask = cache.mask(problem, constraints) if cache is not None else None
    before = cache.before if mask is not None else resolve(problem)
    best, repairs, ties = None, [], 0
    complete = True
    for ordinal, (edits, cost) in enumerate(candidates(problem)):
        if not budget.take():
            complete = False
            break
        accepted = cache.satisfies(ordinal, edits, mask) if mask is not None else None
        if accepted is None:
            edited = apply_edits(problem, edits)
            allowed, (_, envs) = admissible(problem, edited, before)
            accepted = allowed and not violations(constraints, {e: r["values"] for e, r in envs.items()})
        if not accepted:
            continue
        p = proposal(problem, edits, cost)
        if not optimize:
            return {"status": "SAT", "witness": p, "states": budget.used}
        if best is None or cost < best:
            best, repairs, ties = cost, [p], 1
        elif cost == best:
            ties += 1
            if len(repairs) < max_repairs:
                repairs.append(p)
    if not optimize:
        return {"status": "UNSAT" if complete else "UNKNOWN", "witness": None, "states": budget.used}
    return {"status": ("OPTIMAL" if best is not None else "UNSAT") if complete else "UNKNOWN",
            "cost": best, "repairs": repairs, "states": budget.used,
            "tie_count": ties if complete else None, "ties_complete": complete and ties <= max_repairs,
            "search_complete": complete}


def solve(problem, max_states=100_000):
    return search(problem, problem.data["constraints"], Budget(max_states))


def repair(problem, max_states=100_000, max_repairs=20):
    integer(max_repairs, "max_repairs", 1)
    return search(problem, problem.data["constraints"], Budget(max_states), True, max_repairs)


def conflict(problem, max_states=100_000):
    """Deletion-minimal constraint subset under immutable schema/edit/protection premises.

    Shared budget covers every subset and final removal witness. Not minimum size.
    """
    budget = Budget(max_states)
    cache = _ConflictCache(problem, budget.limit)
    constraints = list(problem.data["constraints"])
    initial = _search(problem, constraints, budget, cache=cache)
    premises = {"source_sha256": fingerprint(problem), "edit_scope": problem.data.get("edit_scope", "leaf"),
                "protected": problem.data["protected"], "universe": problem.data["edits"],
                "fixed": "all schema, inheritance, unedited overrides and protection snapshots"}
    if initial["status"] != "UNSAT":
        return {"status": initial["status"], "constraints": [], "minimal": False,
                "premises": premises, "states": budget.used}
    for c in list(constraints):
        subset = [x for x in constraints if x["id"] != c["id"]]
        result = _search(problem, subset, budget, cache=cache)
        if result["status"] == "UNKNOWN":
            return {"status": "UNKNOWN", "constraints": [], "minimal": False,
                    "premises": premises, "states": budget.used}
        if result["status"] == "UNSAT":
            constraints = subset
    witnesses = {}
    for c in constraints:
        result = _search(problem, [x for x in constraints if x["id"] != c["id"]], budget, cache=cache)
        if result["status"] != "SAT":
            return {"status": "UNKNOWN", "constraints": [], "minimal": False,
                    "premises": premises, "states": budget.used}
        witnesses[c["id"]] = result["witness"]
    return {"status": "UNSAT", "constraints": [c["id"] for c in constraints], "minimal": True,
            "premises": premises, "removal_witnesses": witnesses,
            "premises_alone_unsatisfiable": not constraints, "states": budget.used}
