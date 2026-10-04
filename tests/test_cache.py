from copy import deepcopy
import unittest
from unittest.mock import patch

import configwitness as cw
import configwitness.engine as engine
from raw_reference import Reference, cases, trace, validation


class CachedConflictTests(unittest.TestCase):
    def test_raw_predicates_inheritance_and_all_shared_prefixes(self):
        for number, data in enumerate(cases()):
            expected = Reference(data)
            problem = cw.Problem(data)
            original = deepcopy(problem.data)
            self.assertEqual(cw.validate(problem), validation(data), number)
            for field in data["fields"]:
                self.assertEqual(cw.trace(problem, "租户-Δ", field), trace(data, "租户-Δ", field), number)
            for budget in (0, 5, len(expected.rows), 10000):
                with self.subTest(case=number, budget=budget):
                    self.assertEqual(cw.solve(problem, budget), expected.solve(budget))
                    self.assertEqual(cw.repair(problem, budget, 3), expected.repair(budget, 3))
                    self.assertEqual(cw.conflict(problem, budget), expected.conflict(budget))
            for proposed in cw.repair(problem, max_repairs=100)["repairs"]:
                checked = cw.check_proposal(problem, proposed)
                self.assertTrue(checked["accepted"])
                materialized = cw.apply_edits(problem, proposed["edits"])
                self.assertEqual(checked["configs"], cw.validate(materialized)["configs"])
                self.assertEqual(cw.validate(materialized)["status"], "VALID")
            self.assertEqual(problem.data, original)

    def test_full_cache_and_disabled_cache_keep_logical_reports(self):
        for data in list(cases(count=12)):
            problem, reference = cw.Problem(data), Reference(data)
            for state_cap, byte_cap in ((0, 1_048_576), (2, 1_048_576), (4096, 0), (4096, 8192)):
                with patch.object(engine, "_CACHE_MAX_STATES", state_cap), patch.object(engine, "_CACHE_MAX_BYTES", byte_cap):
                    for budget in (1, 64, 10000):
                        self.assertEqual(cw.conflict(problem, budget), reference.conflict(budget))

    def test_context_does_not_accept_foreign_source_or_changed_predicate(self):
        data = next(cases())
        problem = cw.Problem(data)
        cache = engine._ConflictCache(problem, 10000)
        self.assertIsNone(cache.mask(cw.Problem(data), problem.data["constraints"]))
        changed = deepcopy(problem.data["constraints"])
        self.assertIsNone(cache.mask(problem, changed))
        self.assertEqual(engine._search(problem, changed, engine.Budget(10000), cache=cache), engine.search(problem, changed, engine.Budget(10000)))

    def test_accounting_limits_and_original_source_release(self):
        problem = cw.Problem(next(cases()))
        cache = engine._ConflictCache(problem, 10000)
        mask = cache.mask(problem, problem.data["constraints"])
        for ordinal, (edits, _) in enumerate(engine.candidates(problem)):
            cache.satisfies(ordinal, edits, mask)
            self.assertLessEqual(cache.bytes, engine._CACHE_MAX_BYTES)
            self.assertLessEqual(len(cache.entries), engine._CACHE_MAX_STATES)
        self.assertTrue(all(value is engine._MISSING or value is None or type(value) is bytes for value in cache.entries))
        self.assertFalse(hasattr(problem, "cache"))


if __name__ == "__main__":
    unittest.main()
