# Reproducible local validation

Verified 2026-10-03 on Windows, CPython 3.14.3. Only a normal wheel installed
into dedicated virtual environments was used for principal SDK/console tests;
no editable install or source-path injection. `configwitness.__file__` was
asserted to contain `site-packages`. Historical replay intentionally uses
temporary extracted source to compare exact commits and is a separate check.

Commands (activate your chosen venv first):

```sh
python -m pip wheel . --no-deps --wheel-dir dist
python -m pip install dist/configwitness-0.1.0-py3-none-any.whl
python -m unittest discover -s tests -v
python tools/workflow.py
python tools/contrast.py
python tools/review_replay.py
```

Observed final code verification: all 21 tests pass, including 80 seeded
integer-sum search cases and 40 seeded typed relational/ancestor edit cases.
The separate exhaustive oracle checks satisfiability, all least-cost repair
ties, claimed inclusion-minimal cores and each core's removal satisfiability.
Adversarial tests cover deterministic diamond order, cycles, missing parents,
duplicate identities/JSON keys, malformed types, bool/int distinction,
nullable/missing/unset/remove, protected ancestor and environment values,
zero-cost ties, truncated search, forged proposal cost/source/options,
source preservation and runtime parsing/copy limits.

The actual installed console workflow prints:

```text
console workflow: INVALID -> traced standby -> OPTIMAL cost=2 -> independently checked -> actual rollout VALID; conflict and UNKNOWN verified
```

Measured synthetic contrast (all input costs are caller assumptions):

| Fixture | Assignments | Fleet | Local-only fleet valid / cost | Greedy fleet valid / cost |
|---|---:|---|---|---|
| failover.json | 9 | OPTIMAL 2, valid | false / 0 | false / 0 |
| already-good.json | 4 | OPTIMAL 0, valid | true / 0 | true / 0 |
| no-finite-repair.json | 2 | UNSAT | false / 0 | false / 0 |
| local-repair-good.json | 9 | OPTIMAL 2, valid | true / 2 | true / 2 |

The replay prints expected FAIL then PASS for each historical source pair in
`tools/review_replay.py`. It confirms the four required correction rounds and
additional parser boundary change; details and the corrected draft-probe mistake
are preserved in [ITERATIONS.md](ITERATIONS.md).

Normal wheel metadata was inspected: version `0.1.0`, `Requires-Python: >=3.11`,
`License-Expression: MIT`, `License-File: LICENSE`, `Root-Is-Purelib: true`,
tag `py3-none-any`, built by setuptools 84.0.0 using the declared
`setuptools>=77.0.3` build requirement. Raw local execution transcripts reside
in ignored `.local/`; public evidence includes no machine-specific absolute paths.

No Linux run or Python 3.11 runtime was available locally. The checked-in Actions
matrix declares Ubuntu/Windows and Python 3.11/3.14 ordinary wheel, tests, actual
workflow and contrast, but remote CI remains unverified until publication.
No incumbent CUE/OPA executable, customer workflow, revenue, production forecast,
or measured economic savings was claimed or tested.
