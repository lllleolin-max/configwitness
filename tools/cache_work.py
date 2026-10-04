"""Synthetic installed conflict work, full wire and bounded-cache diagnostics.

Use identical inputs/caps with independently installed old/new packages. Cache
overrides are benchmark diagnostics, not SDK options or changed logical budgets.
"""
import argparse
from copy import deepcopy
from contextlib import ExitStack
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
import tracemalloc
from unittest.mock import patch
import configwitness as cw
import configwitness.engine as engine
import configwitness.constraints as predicates


def fixture(case="dense"):
    data = {"version": 1, "fields": {"n": {"type": "int"}},
            "layers": [{"id": "base", "parents": [], "overrides": {"n": 1}}] + [
                {"id": f"l{i}", "parents": ["base"], "overrides": {}} for i in range(3)],
            "environments": [{"id": f"e{i}", "layer": f"l{i}"} for i in range(3)],
            "constraints": [{"id": "lower", "kind": "sum", "envs": ["e0", "e1", "e2"], "field": "n", "min": 7},
                            {"id": "upper", "kind": "sum", "envs": ["e0", "e1", "e2"], "field": "n", "max": 6}],
            "edits": [{"layer": f"l{i}", "field": "n", "options": [
                {"op": "set", "value": n, "cost": n % 2} for n in (0, 2, 3)]} for i in range(3)], "protected": []}
    data["constraints"] += [{"id": f"noise-{i}", "kind": "range", "envs": [f"e{i % 3}"], "field": "n", "min": 0, "max": 3} for i in range(8)]
    if case == "sparse":
        data["constraints"] = data["constraints"][:2]
    elif case == "sat-small":
        data["constraints"] = data["constraints"][2:3]
        data["edits"] = data["edits"][:1]
    elif case == "single-search":
        data["constraints"] = data["constraints"][2:]
    elif case == "cap-default":
        data["layers"] = data["layers"][:1] + [{"id": f"l{i}", "parents": ["base"], "overrides": {}} for i in range(8)]
        data["environments"] = [{"id": f"e{i}", "layer": f"l{i}"} for i in range(8)]
        data["edits"] = [{"layer": f"l{i}", "field": "n", "options": [
            {"op": "set", "value": n, "cost": 0} for n in (0, 2)]} for i in range(8)]
        for constraint in data["constraints"][:2]:
            constraint["envs"] = [f"e{i}" for i in range(8)]
        data["constraints"][0]["min"] = 9
        data["constraints"][1]["max"] = 8
    elif case == "large-source":
        data = {"version": 1, "fields": {"text": {"type": "string"}},
                "layers": [{"id": "root", "parents": [], "overrides": {"text": "x" * 2000}}] + [
                    {"id": f"l{i}", "parents": ["root" if i == 0 else f"l{i-1}"], "overrides": {}} for i in range(600)],
                "environments": [{"id": "prod", "layer": "l599"}], "constraints": [], "edits": [], "protected": []}
    return data


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--case", choices=["dense", "sparse", "sat-small", "single-search", "cap-default", "large-source"], default="dense")
    p.add_argument("--max-states", type=int, default=100000)
    p.add_argument("--assert-reuse", action="store_true")
    p.add_argument("--cache-states", type=int)
    p.add_argument("--cache-bytes", type=int)
    a = p.parse_args()
    overrides = ExitStack()
    for flag, attribute in ((a.cache_states, "_CACHE_MAX_STATES"), (a.cache_bytes, "_CACHE_MAX_BYTES")):
        if flag is not None and hasattr(engine, attribute):
            if flag < 0:
                p.error("cache diagnostics must be nonnegative")
            overrides.enter_context(patch.object(engine, attribute, flag))
    a.output.mkdir(parents=True, exist_ok=False)
    data = fixture(a.case)
    original = deepcopy(data)
    problem = cw.Problem(data)
    counts = {"resolve_calls": 0, "apply_edits_calls": 0, "admissible_calls": 0,
              "candidate_yields": 0, "constraint_evaluations": 0}
    cache_stats = None
    if hasattr(engine, "_ConflictCache") and a.case != "single-search":
        cache_stats = {"accounted_bytes_peak": 0, "slots": 0, "admitted_states": 0,
                       "scope": "conservative snapshot/index/slot/vector accounting, not OS/RSS or transient-work cap"}
    with ExitStack() as stack:
        if cache_stats is not None:
            old_init = engine._ConflictCache.__init__
            old_satisfies = engine._ConflictCache.satisfies
            def initialized(self, *args, **kwargs):
                old_init(self, *args, **kwargs)
                cache_stats["accounted_bytes_peak"] = max(cache_stats["accounted_bytes_peak"], self.bytes)
                cache_stats["slots"] = len(self.entries)
            def satisfies(self, ordinal, *args, **kwargs):
                missing = ordinal < len(self.entries) and self.entries[ordinal] is engine._MISSING
                result = old_satisfies(self, ordinal, *args, **kwargs)
                if missing and self.entries[ordinal] is not engine._MISSING:
                    cache_stats["admitted_states"] += 1
                cache_stats["accounted_bytes_peak"] = max(cache_stats["accounted_bytes_peak"], self.bytes)
                return result
            stack.enter_context(patch.object(engine._ConflictCache, "__init__", initialized))
            stack.enter_context(patch.object(engine._ConflictCache, "satisfies", satisfies))
        for name in ("resolve", "apply_edits", "admissible"):
            old = getattr(engine, name)
            def wrapper(*args, _old=old, _name=name, **kwargs):
                counts[_name + "_calls"] += 1
                return _old(*args, **kwargs)
            stack.enter_context(patch.object(engine, name, wrapper))
        old_candidates = engine.candidates
        def candidates(*args):
            for value in old_candidates(*args):
                counts["candidate_yields"] += 1
                yield value
        stack.enter_context(patch.object(engine, "candidates", candidates))
        old_evaluate = predicates.evaluate
        def evaluate(*args):
            counts["constraint_evaluations"] += 1
            return old_evaluate(*args)
        stack.enter_context(patch.object(predicates, "evaluate", evaluate))
        action = cw.repair if a.case == "single-search" else cw.conflict
        observed = action(problem, a.max_states)
    frozen = canonical(observed)
    times = []
    for _ in range(3):
        start = time.perf_counter()
        result = action(problem, a.max_states)
        times.append(time.perf_counter() - start)
        assert canonical(result) == frozen
    del result
    gc.collect()
    tracemalloc.start()
    result = action(problem, a.max_states)
    retained, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert canonical(result) == frozen and data == original and problem.data == original
    total = 1
    for edit in data["edits"]:
        total *= 1 + len(edit["options"])
    summary = {"case": a.case, "max_states": a.max_states, "constraints": len(data["constraints"]),
               "edit_targets": len(data["edits"]), "options_per_target": [len(e["options"]) for e in data["edits"]],
               "universe_candidates_including_unchanged": total, "status": result["status"], "logical_states": result["states"],
               "wire_sha256": hashlib.sha256(frozen.encode()).hexdigest(), "actual_counts": counts,
               "wall_seconds_median": statistics.median(times), "tracemalloc_retained_bytes": retained,
               "tracemalloc_peak_bytes": peak, "input_unchanged": True, "cache_accounting": cache_stats,
               "cache_overrides": {"states": a.cache_states, "bytes": a.cache_bytes},
               "cache_override_supported": hasattr(engine, "_ConflictCache")}
    (a.output / "input.json").write_text(canonical(data), encoding="utf-8")
    (a.output / "wire.json").write_text(frozen, encoding="utf-8")
    (a.output / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    overrides.close()
    if a.assert_reuse:
        assert counts["apply_edits_calls"] <= total, "same candidate repeatedly applied across constraint subsets"


if __name__ == "__main__":
    main()
