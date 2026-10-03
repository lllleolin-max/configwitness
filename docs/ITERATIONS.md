# Actual self-review corrections

Authoring/review date: 2026-10-03. Builder: GPT-6.1-Sol / Ultra. These are builder
self-reviews, not independent portfolio scores. Each defect was found and its
probe failed after the initially complete implementation had been committed.
No intentionally planted defect or sliced initial feature work is counted.

Initial complete implementation: `5dca550e9d742db892f0ba7e0de49774b3dd554f`.
An ordinary wheel installed in a dedicated venv, 14 tests (including 80 seeded
small exhaustive instances), the actual console workflow and contrast all passed.
That initial test set missed the following real failures.

## 1. Ambiguous JSON and malformed identifiers

Before: `5dca550e9d742db892f0ba7e0de49774b3dd554f`.
After: `d7dd29b549998de62a347ed76795df9dd81c124e`.

Reviewing the strict-input claim found that a duplicate nested `replicas` key
silently accepted the last value. `python tools/probes/input_boundary.py` actually
failed with `AssertionError: duplicate JSON field accepted: last value silently
won`. A separate malformed parent-list probe raised raw `TypeError` rather than
the documented `InputError`.

Correction: duplicate-key parsing at every object nesting level for both source
and proposal JSON; validate identifier shape before hashing/indexing. The probe
also checks five malformed target/reference shapes. Rebuilt and reinstalled the
ordinary wheel; this probe printed `input-boundary PASS` and all 15 tests passed.
Strict field language still excludes floats/nested values and expressions.

## 2. Deep DAG and exponential provenance resource behavior

Before: `d7dd29b549998de62a347ed76795df9dd81c124e`.
After: `d3b4b5906e93eba52ef31259a088c124bedfabc5`.

Reviewing input permutation/resource behavior found that a reversed 1500-layer
acyclic chain raised `RecursionError: maximum recursion depth exceeded`.
The same graph in topological input order passed, so input-list order accidentally
controlled support. A 20-level repeated diamond also expanded provenance without
a resource refusal (the preliminary probe ran for more than 10 seconds).

Correction: iterative DFS for validation/topological order, iterative resolution,
value-only validation/search, and a 20,000 cached-provider-event cap for explicitly
requested exact traces. The trace rejects rather than silently abbreviates.
`python tools/probes/deep_inheritance.py` then passed reversed 1500-layer
validate/trace/repair/independent-check and verified that the dense diamond's
values validate while its oversized exact trace raises `InputError`. Ordinary
wheel reinstalled; all 16 tests passed. State bounds are not wall-clock limits.

## 3. Source/artifact preservation in the actual CLI

Before: `d3b4b5906e93eba52ef31259a088c124bedfabc5`.
After: `01f168166df56a9a67374ff0accb90c99f8b8377`.

Reviewing materialization showed `repair input.json --output input.json` replaced
the original source with the proposal. The portable temporary-file probe actually
failed with `AssertionError: repair clobbered its original source file`.

Correction: exclusive output-file creation for repair and apply; existing source
and proposal paths/aliases reject with exit 2. No racy exists-check/truncate pair.
`python tools/probes/output_preservation.py` passed source/existing-proposal byte
preservation, fresh proposal creation, actual rollout creation and validation.
Ordinary wheel reinstalled; all 17 tests, actual console workflow and three-case
contrast passed. An interrupted new-file write may leave incomplete new output;
no fsync durability or atomic deployment promise.

## 4. Fair local baseline progress on grouped unary constraints

Before: `01f168166df56a9a67374ff0accb90c99f8b8377`.
After: `d691c12a8ad093c6f08d0ea9c4fc2ca977e3da4d`.

Broadening the baseline-good contrast from a no-op to an actual two-environment
repair found that greedy local repair counted a grouped range rule as only one
violation. Fixing one environment did not reduce that count, so it stopped while
two independently fixable unary failures remained. The actual portable probe
failed with `AssertionError: greedy stalled while two independent unary violations
were fixable`.

Correction: split grouped unary rules into one evaluation per environment for
local-baseline scoring, preserving the same underlying constraints and universe.
`python tools/probes/local_baseline_progress.py` passes; all 20 tests (including
120 seeded independent exhaustive cases) pass. Four-case contrast now exercises
greedy's real neighborhood search: both local baselines and fleet optimum perform
the two required fixes at cost 2. This corrects the baseline fairly and does not
inflate the claimed distinction. Greedy still has only a local stopping guarantee.

## Additional parser/copy boundary hardening and probe correction

Before code: `d691c12a8ad093c6f08d0ea9c4fc2ca977e3da4d`.
After code: `fc071ad15c17967c1ca5b64066f9afc994ae4f81`.
Corrected probe: `07cf1cc2845cbb08190323159b6f2c96c0f84bcd`.

The final portable `parser_limits.py` exercises public `load`, which previously
leaked RecursionError during copying of excessively nested decoded input. The
fix translates JSON integer conversion/nesting and input-copy runtime limits
into InputError. The first draft probe mistakenly exercised the lower-level
JSON reader: Python 3.14 can decode its nested list, so that test assertion was
wrong and failed even after the code correction. The separate probe commit
corrects it to the public schema-loading entry point. This mistake is preserved
in history; that intermediate test run is not claimed as passing.

The final probe passes and the historical replay independently confirms public
load's old RecursionError versus corrected InputError. All 21 final tests pass.
The first four documented correction cycles meet the iteration requirement
independently of this additional hardening/probe correction.

## Replay the evidence

`python tools/review_replay.py` extracts each exact before/after Git source into
temporary directories, invokes the preserved current portable probe against that
source using a subprocess-specific PYTHONPATH, and asserts expected failure before
and pass after. This is a source-history check, distinct from normal wheel testing.
It prints portable summaries rather than local absolute paths. Requires the full
repository history, Python >=3.11 and Git; no global config or network changes.

Each correction commit contains the code changes and new regression. The final
evidence commit adds this log, replay tool and broader reference cases. Linux and
Python 3.11/3.14 CI is declared but remote execution remains unverified until
publication. No score, customer, revenue or production safety conclusion follows.
