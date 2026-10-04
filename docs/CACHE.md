# Bounded conflict candidate reuse

Version 0.2 reuses work only inside one `conflict` invocation. The original
validated Problem and full ordered predicate universe stay fixed. Each repeated
candidate ordinal has the same declared option tuple, including unchanged and
zero-cost/no-op choices. A lazy entry contains either schema/protection rejection
or a byte vector of **all original** predicate failures. Subset searches test
that vector against the requested original constraint mask. They never cache
only the subset being tested, edit resolved maps, or collapse different choices
that happen to produce equal values. No edited Problem or candidate resolution
is retained. Candidate materialization, validation and protected source-layer
presence/type/value checks still run when first evaluating an entry.

Every candidate visit still consumes the shared logical state budget, including
cache hits. Candidate order, SAT witness choice, UNKNOWN prefixes, exact
minimum-cost/tie semantics and conflict deletion/removal order are unchanged.
All original report fields and source/proposal formats remain compatible.
`solve`, `repair`, direct `search` and both single-search baselines use their
original uncached evaluation path. The independent proposal checker remains
separate and rechecks **all original** constraints and protections; a removal
witness is still not a full-fleet repair.

## State and accounted-byte bounds

The cache allocates no more than 4,096 ordinal slots, also limited by the declared
candidate universe and whole-call state budget. It evaluates entries only as
they are visited; it does not enumerate the universe up front. Retained original
resolution, constraint identity index, allocated slots and admitted vectors use
a 1,048,576-byte conservative object-accounting budget, with a 4,096-byte context
reserve. `sys.getsizeof` includes container allocation; nested scalar/container
sizes are counted repeatedly when shared, deliberately overestimating retention.
Entry vectors have one bit per original predicate. Unsupported object-size
accounting disables admission conservatively.

If the original resolution/index already exceeds admission budget, the cache is
disabled and those objects are released. If slots or vector capacity fill,
later candidates use ordinary uncached evaluation. This is transparent: the
same logical state count/status/core/witnesses are returned. It does not produce
an extra UNKNOWN, silently shrink the predicate universe or publish a partial
minimal core. The fallback may be slower; a disabled cache can add an initial
resolution before ordinary evaluation begins.

This bounds admitted memoized content, **not OS memory, RSS, source size or
transient per-candidate work**. Caller Problem data, outputs, fresh edited copies,
schema/resolution work and interpreter overhead still scale with input.
Conservative counting can disable caching even when physical shared-string
memory is smaller. Predicate-index and original-resolution construction occur
before admission and can create temporary input-sized work. External process
limits remain necessary for strict memory/time guarantees.

The finite enumeration and deletion algorithm are unchanged. With S logical
visits, U distinct visited candidates, C predicates and input resolution cost R,
an admitted repeated prefix avoids repeating O(R) work and evaluates C predicate
results once per cached candidate. Candidate generation still runs for every
logical visit. Beyond capacity, ordinary subset work repeats. Single search and
small/SAT-first cases may see no benefit, and all-constraint vector computation
can cost more than a tiny subset on first evaluation. This is bounded reuse,
not branch-and-bound or a scalable symbolic solver.

## Actual installed measurement

Run this same script against separately installed old/new wheels, with fresh
output directories. It stores the exact input, full report, actual resolve/
apply/admissible/candidate/predicate counts, three untraced wall times (median),
and a separate tracemalloc run with the result retained:

```console
python tools/cache_work.py --output .local/dense --assert-reuse
python tools/cache_work.py --case sparse --output .local/sparse
python tools/cache_work.py --case sat-small --output .local/small
python tools/cache_work.py --case single-search --output .local/repair
python tools/cache_work.py --case cap-default --max-states 10000 --output .local/cap-default
python tools/cache_work.py --case large-source --output .local/large-source
python tools/cache_work.py --cache-states 2 --output .local/cap-diagnostic
python tools/cache_work.py --cache-bytes 0 --output .local/disabled-diagnostic
```

Cache overrides are controlled benchmark diagnostics, not public SDK options or
changes to logical max_states. The main fixture has ten constraints, three edit
targets and three options each: unchanged is a fourth choice, so there are 64
candidate combinations. The default-cap case has 6,561 combinations; a 10,000
whole-call budget still yields UNKNOWN if conflict minimality is unfinished.
The large-source case shows conservative snapshot admission refusal. Accounted
cache bytes are separate from Python peak memory. Timings depend on interpreter,
host load and fixture; use counters and byte equality rather than a speed promise.
See the update record for actual values and retained adverse results.
