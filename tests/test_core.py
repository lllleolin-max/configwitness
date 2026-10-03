import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

from configwitness import InputError, Problem, load, validate, trace, solve, repair, conflict, apply_edits, check_proposal
from configwitness.baselines import per_environment, greedy_local
from oracle import enumerate_feasible, identity

ROOT = Path(__file__).resolve().parents[1]


def tiny():
    return {"version": 1, "fields": {"n": {"type": "int"}},
            "layers": [{"id": "base", "parents": [], "overrides": {"n": 1}},
                       {"id": "a", "parents": ["base"], "overrides": {}},
                       {"id": "b", "parents": ["base"], "overrides": {}}],
            "environments": [{"id": "a", "layer": "a"}, {"id": "b", "layer": "b"}],
            "constraints": [], "edits": [], "protected": []}


class ModelTests(unittest.TestCase):
    def test_diamond_later_parent_snapshot_then_child(self):
        d = tiny()
        d["layers"] += [{"id": "leaf", "parents": ["a", "b"], "overrides": {}}]
        d["layers"][1]["overrides"]["n"] = 3
        d["environments"] = [{"id": "prod", "layer": "leaf"}]
        p = Problem(d)
        self.assertEqual(validate(p)["configs"]["prod"]["n"], 1)
        self.assertEqual([e["layer"] for e in trace(p, "prod", "n")["providers"]], ["base", "a", "base"])
        d["layers"][-1]["overrides"]["n"] = 4
        self.assertEqual(trace(Problem(d), "prod", "n")["winner"]["layer"], "leaf")

    def test_cycles_missing_parents_duplicate_ids(self):
        for mutation in (lambda d: d["layers"][0]["parents"].append("a"),
                         lambda d: d["layers"][1]["parents"].append("missing"),
                         lambda d: d["layers"].append(copy.deepcopy(d["layers"][0])),
                         lambda d: d["environments"].append(copy.deepcopy(d["environments"][0]))):
            d = tiny(); mutation(d)
            with self.assertRaises(InputError): Problem(d)

    def test_bool_int_null_unset_missing(self):
        d = tiny(); d["layers"][0]["overrides"]["n"] = True
        with self.assertRaises(InputError): Problem(d)
        d["fields"]["n"]["nullable"] = True; d["layers"][0]["overrides"]["n"] = None
        self.assertEqual(validate(Problem(d))["status"], "VALID")
        d["layers"][1]["overrides"]["n"] = {"$unset": True}
        self.assertEqual(validate(Problem(d))["status"], "INVALID")
        d["fields"]["n"]["required"] = False
        t = trace(Problem(d), "a", "n")
        self.assertFalse(t["present"])
        self.assertEqual(t["winner"]["value"], {"$unset": True})

    def test_strict_options_constraints_and_nonfinite(self):
        d = tiny(); d["edits"] = [{"layer": "a", "field": "n", "options": [{"op": "set", "value": 2, "cost": True}]}]
        with self.assertRaises(InputError): Problem(d)
        d["edits"][0]["options"][0]["cost"] = 0
        d["edits"][0]["options"].append(copy.deepcopy(d["edits"][0]["options"][0]))
        with self.assertRaises(InputError): Problem(d)
        d = tiny(); d["constraints"] = [{"id": "x", "kind": "range", "envs": ["a", "a"], "field": "n", "min": 0}]
        with self.assertRaises(InputError): Problem(d)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"input.json"; path.write_text('{"version": NaN}', encoding="utf-8")
            with self.assertRaises(InputError): load(path)

    def test_leaf_scope_and_shared_parent_actual_reresolve(self):
        d = tiny(); d["edits"] = [{"layer": "base", "field": "n", "options": [{"op": "set", "value": 2, "cost": 1}]}]
        with self.assertRaises(InputError): Problem(d)
        d["edit_scope"] = "declared-layers"
        d["constraints"] = [{"id": "total", "kind": "sum", "envs": ["a", "b"], "field": "n", "min": 4}]
        p = Problem(d); r = repair(p)
        self.assertEqual(r["cost"], 1)
        self.assertEqual(check_proposal(p, r["repairs"][0])["configs"], {"a": {"n": 2}, "b": {"n": 2}})
        self.assertEqual(p.data["layers"][0]["overrides"]["n"], 1)

    def test_protected_ancestor_and_environment(self):
        d = tiny(); d["edit_scope"] = "declared-layers"
        d["edits"] = [{"layer": "base", "field": "n", "options": [{"op": "set", "value": 2, "cost": 0}]}]
        d["constraints"] = [{"id": "minimum", "kind": "sum", "envs": ["a", "b"], "field": "n", "min": 4}]
        for protect in ({"layer": "base", "field": "n"}, {"env": "b", "field": "n"}):
            d["protected"] = [protect]
            p = Problem(d)
            self.assertEqual(repair(p)["status"], "UNSAT")
            self.assertEqual(conflict(p)["constraints"], ["minimum"])

    def test_remove_reveals_parent_unset_suppresses_it(self):
        d = tiny(); d["layers"][1]["overrides"]["n"] = 3
        d["edits"] = [{"layer": "a", "field": "n", "options": [{"op": "remove", "cost": 1}, {"op": "unset", "cost": 0}]}]
        d["constraints"] = [{"id": "eq", "kind": "equal", "envs": ["a", "b"], "field": "n"}]
        p = Problem(d); r = repair(p)
        self.assertEqual(r["cost"], 1)
        self.assertEqual(r["repairs"][0]["edits"][0]["op"], "remove")
        self.assertTrue(check_proposal(p, r["repairs"][0])["accepted"])


class SearchTests(unittest.TestCase):
    def test_current_invalid_but_future_sat(self):
        p = load(ROOT/"examples"/"failover.json")
        self.assertEqual(validate(p)["status"], "INVALID")
        self.assertEqual(solve(p)["status"], "SAT")
        self.assertEqual(repair(p)["cost"], 2)
        self.assertEqual(per_environment(p)["actual_rollout"], "INVALID")
        self.assertEqual(greedy_local(p)["actual_rollout"], "INVALID")

    def test_zero_cost_multiple_ties_and_tie_cap(self):
        d = tiny()
        d["edits"] = [{"layer": x, "field": "n", "options": [{"op": "set", "value": 2, "cost": 0}]} for x in ("a", "b")]
        d["constraints"] = [{"id": "total", "kind": "sum", "envs": ["a", "b"], "field": "n", "min": 3}]
        r = repair(Problem(d), max_repairs=1)
        self.assertEqual((r["status"], r["cost"], r["tie_count"], r["ties_complete"]), ("OPTIMAL", 0, 3, False))

    def test_exceeded_bound_does_not_prove_optimal_or_conflict(self):
        p = load(ROOT/"examples"/"failover.json")
        self.assertEqual(solve(p, 0)["status"], "UNKNOWN")
        r = repair(p, 2)
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertIsNotNone(r["cost"])
        self.assertIsNone(r["tie_count"])
        self.assertEqual(validate(p)["status"], "INVALID")
        adverse = load(ROOT/"examples"/"no-finite-repair.json")
        c = conflict(adverse, 1)
        self.assertEqual(c["status"], "UNKNOWN")
        self.assertFalse(c["minimal"])
        self.assertEqual(c["constraints"], [])

    def test_contradictions_and_minimal_conflict_independent_oracle(self):
        d = tiny()
        d["edits"] = [{"layer": x, "field": "n", "options": [{"op": "set", "value": 2, "cost": 1}]} for x in ("a", "b")]
        d["constraints"] = [{"id": "lo", "kind": "sum", "envs": ["a", "b"], "field": "n", "min": 4},
                            {"id": "hi", "kind": "sum", "envs": ["a", "b"], "field": "n", "max": 3},
                            {"id": "noise", "kind": "range", "envs": ["a", "b"], "field": "n", "min": 0}]
        p = Problem(d); c = conflict(p)
        self.assertEqual(set(c["constraints"]), {"lo", "hi"})
        self.assertFalse(enumerate_feasible(d, c["constraints"]))
        for cid in c["constraints"]:
            self.assertTrue(enumerate_feasible(d, [x for x in c["constraints"] if x != cid]))
        self.assertEqual(repair(p)["status"], "UNSAT")

    def test_premises_alone_can_be_unsatisfiable(self):
        d = tiny(); d["layers"][0]["overrides"].clear()
        p = Problem(d); c = conflict(p)
        self.assertTrue(c["premises_alone_unsatisfiable"])
        self.assertEqual(c["constraints"], [])
        self.assertFalse(enumerate_feasible(d, []))

    def test_checker_rejects_forgery_and_all_original_constraints(self):
        p = load(ROOT/"examples"/"failover.json"); good = repair(p)["repairs"][0]
        self.assertTrue(check_proposal(p, good)["accepted"])
        for mutate in (lambda r: r.update(cost=0), lambda r: r.update(source_sha256="0"*64),
                       lambda r: r["edits"][0].update(value=True), lambda r: r["edits"].append(copy.deepcopy(r["edits"][0])),
                       lambda r: r.update(edits=[], cost=0), lambda r: r["edits"][0].update(cost=0)):
            bad = copy.deepcopy(good); mutate(bad)
            self.assertFalse(check_proposal(p, bad)["accepted"])

    def test_seeded_exhaustive_cost_ties_satisfiability_and_minimality(self):
        rng = random.Random(918)
        for case in range(80):
            d = tiny()
            d["layers"][0]["overrides"]["n"] = rng.randrange(3)
            d["edits"] = [{"layer": x, "field": "n", "options": [{"op": "set", "value": n, "cost": rng.randrange(3)} for n in (1, 2, 3)]} for x in ("a", "b")]
            d["constraints"] = [{"id": "lower", "kind": "sum", "envs": ["a", "b"], "field": "n", "min": rng.randrange(8)},
                                {"id": "upper", "kind": "sum", "envs": ["a", "b"], "field": "n", "max": rng.randrange(8)}]
            if rng.randrange(3) == 0:
                d["protected"] = [{"env": "a", "field": "n"}]
            p = Problem(d); possibilities = enumerate_feasible(d); actual = repair(p)
            self.assertEqual(solve(p)["status"], "SAT" if possibilities else "UNSAT", case)
            if possibilities:
                cheapest = min(c for c, _ in possibilities)
                expected = {identity(e) for c, e in possibilities if c == cheapest}
                self.assertEqual(actual["status"], "OPTIMAL")
                self.assertEqual(actual["cost"], cheapest)
                self.assertEqual({identity(r["edits"]) for r in actual["repairs"]}, expected)
                for r in actual["repairs"]:
                    self.assertTrue(check_proposal(p, r)["accepted"])
            else:
                c = conflict(p)
                self.assertTrue(c["minimal"])
                self.assertFalse(enumerate_feasible(d, c["constraints"]))
                for cid in c["constraints"]:
                    self.assertTrue(enumerate_feasible(d, [x for x in c["constraints"] if x != cid]))


if __name__ == "__main__":
    unittest.main()
