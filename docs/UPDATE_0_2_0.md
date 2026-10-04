# ConfigWitness 0.2 update evidence

Author: GPT-6.1-Sol / Ultra, 2026-10-05. These are author measurements and
self-reviews, not independent scores or production benefits. Original release
`f238e11eeb6339fc41f88a629d16e56aee1f1c91` is the before baseline. The normal
README-only fast-forward to `b7c0db64c3a431366b9eebaa084c2644cbb037d0` was preserved.

## 1. Repeated evaluation and bounded reuse

The preserved installed before probe has ten constraints and three editable
targets with three options each, plus unchanged: 64 assignments. A conflict
needs 610 logical visits across deletion and removal-witness searches. Before,
those visits performed 610 validated edit applications, 623 resolutions and
3,626 predicate evaluations. The actual assertion that each distinct assignment
be applied at most once failed. This is a performance failure, not a false core
or an incorrect status.

Substantive commit `f3bb333fe9428b5ffe91fdecbcfa1c31da123be1` added the lazy
call-local cache, independent raw reference and four regression methods.
The same unchanged probe passed: 64 applications, 65 resolutions and 640
predicate evaluations. The full report and source input were byte-identical;
all 610 logical visits remained charged. The report SHA-256 is
`1c97e0c9e4bb0253e568f3b0503ff6d124e948b279835e8b6ed3b7dd2f6c18d9`.
The first ordinary installed before/after timing medians were 0.266204/0.020043
seconds; a later serial paired run is reported below. Those observations are
retained separately rather than replacing the original failed run.

The R1 ordinary wheel passed 25 tests. Full schema/protection checks remain on
first evaluation, and cache vectors represent every original predicate. Public
direct search, solve, repair and local baselines remain uncached. The independent
checker implementation was unchanged and reevaluates the original full rules.

## 2. Boundary and oracle review

Commit `be74db4258b1de7ee0ed6efcba21f6ff460f5993` added exact byte-admission and
oversized-snapshot regressions, the runnable work probe, memory-scope documentation
and a version-independent CI wheel install. Its eight runtime modules are
byte-identical to R1. The ordinary installed suite passed 27 tests, including
the original 21 tests/120 reference instances. No new correctness defect was
found in this stage; extra tests and documentation are not counted as bug fixes.

The new reference imports no production functions. It separately expands small
inheritance paths, materializes all finite choices and evaluates all six
predicate kinds, typed null/presence, unset/removal, ordered diamond parents,
shared and leaf edits, zero-cost options and protected layers/environments.
108 distinct seeded scenarios were checked at four budgets (0, 5, 64 and
10,000): 432 distinct shared-budget cases. Full solve/repair/conflict dictionaries,
including statuses, state counts, costs, ordered ties, premises and removal
witnesses, matched this raw reference. Baseline and R1 serialized wire files,
also containing original local-baseline outputs, were exactly equal (593,127
bytes). The aggregate per-case wire SHA-256 is
`a253e449cbdac174c849cd09f42eb751d063318af9951198dd32ca3320c77391`.
88 available proposals passed independent checking and materialized validation;
324 complete field traces matched the separate reference. Input snapshots stayed
unchanged. This finite oracle does not establish general solver correctness.

State caps of 0 and 2, byte caps of 0 and 8,192, exact admission boundary ±1,
foreign source contexts and cloned predicate objects were checked for unchanged
reports or ordinary fallback. A 600-layer, long-string input refused cache
admission yet still returned SAT rather than an extra UNKNOWN. The separately
preserved original independent probe was replayed by the author against the
baseline wheel: 84 cases, 39 OPTIMAL/45 UNSAT, 255 ties/45 minimal cores, typed
protection/forgery checks and a reversed 2,100-layer case passed. This replay is
not a new independent review or certification of the old score.

## Installed serial measurements

Same public `tools/cache_work.py`, exact input and logical budget were used
serially in separately installed old/new environments on Windows/Python 3.14.3.
Counters are instrumented actual calls; wall medians are three separate untraced
runs; peak memory is a separate tracemalloc run with the returned report retained.
Tracemalloc is Python allocation accounting, not RSS. All six complete wire
files and inputs were equal. Timings vary with host load.

| Case | Logical states old=new | Resolve calls old→new | Apply calls old→new | Predicate evaluations old→new | Median seconds old→new | Python peak bytes old→new |
|---|---:|---:|---:|---:|---:|---:|
| dense, 64 choices/10 constraints | 610 | 623→65 | 610→64 | 3,626→640 | 0.152872→0.014226 | 49,990→39,141 |
| sparse, 64 choices/2 constraints | 98 | 103→65 | 98→64 | 162→128 | 0.016880→0.012608 | 40,670→33,142 |
| small first-witness SAT | 1 | 2→2 | 1→1 | 1→1 | 0.000134→0.000391 | 18,310→18,612 |
| single-search repair | 64 | 65→65 | 64→64 | 512→512 | 0.013731→0.013182 | 61,833→62,033 |
| 6,561 choices, budget 10,000 | 10,000 | 10,004→6,562 | 10,000→6,561 | 96,561→65,610 | 3.364373→2.540638 | 80,910→257,040 |
| oversized snapshot, SAT | 1 | 2→3 | 1→1 | 0→0 | 0.005262→0.007698 | 981,216→982,248 |

The 6,561-choice case remains UNKNOWN: its aggregate conflict work is unfinished.
It has 10,001 yielded candidates because the original generator yields the next
candidate before the budget rejects the visit. This behavior was preserved.
Its cache fills 4,096 slots and accounts 192,688 bytes; higher Python peak memory
is the explicit CPU/memory tradeoff. The dense case accounts 12,756 bytes. The
oversized snapshot releases admission objects and accounts zero retained cache
bytes but pays one extra initial resolution.

Controlled diagnostics also preserve adverse evidence: a two-slot cache on the
dense input still applies 588 candidates (589 resolutions/3,508 evaluations),
and measured 0.125145 seconds/51,752 peak bytes versus the earlier old
0.123433/49,990 run. Disabled 0-byte and 8,192-byte caches apply all 610 candidates
and resolve 624 times. These overrides are probe diagnostics, not new SDK options.
No claim of a universal speedup or OS memory bound follows.

## 3. Installed delivery and version

The final delivery stage updates version 0.2.0, changelog and operational docs,
preserving the user-provided clone/venv instructions. Runtime code is unchanged
from R1; the 27-test suite is unchanged from R2. No third defect was invented.
Canonical archives explicitly use `git -c core.autocrlf=false archive`; raw Git
module blobs, LF archive files, ordinary wheel members and isolated installed
site files are compared byte for byte. Source-history injection is not used for
these installed checks. New final-SHA receipts are produced after committing.

The installed integration probe was already run on R2: 55 actual sysconfig
console calls passed in native, PYTHONUTF8=0/1 and strict cp1252/cp936 modes.
Complete SDK and CLI reports matched, including trace, repair, check, apply,
conflict and UNKNOWN. A proposal written by the baseline wheel remained accepted
and identical. Source/proposal/hardlink alias outputs were rejected with exit 2
without changing original bytes; forged cost/source/typed edits were rejected,
and zero-state UNKNOWN did not create a proposal file. Both original workflow
and four-case contrast tools passed. Final installed checks rerun these actions.

All four original genuine correction pairs in [ITERATIONS](ITERATIONS.md) were
also replayed using five fresh ordinary historical wheels and the same preserved
probes: each direct-parent before returned exit 1 and after exit 0. Original
failed evidence and attribution corrections remain unchanged. This maintenance
replay adds zero new defect cycles. The declared Linux/Windows Python 3.11/3.14
CI matrix requires separate remote execution after publication; only the local
Windows/Python 3.14 runs are asserted here.

To reproduce finite measurements, install the intended revision normally and
run the commands in [CACHE](CACHE.md), using new output directories. Run
`python -m unittest discover -s tests -v`, `python tools/workflow.py` and
`python tools/contrast.py` for the full suite and original workflow. Search stays
exponential; byte accounting is conservative admitted retention, not a limit on
input/transient work or process lifetime memory. Customer adoption, revenue and
production rollout safety remain unknown.
