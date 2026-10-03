# Architecture and operational limits

`model` validates a snapshot. `resolve` produces complete layer and environment
values plus ordered provider histories. `constraints` evaluates concrete fleet
predicates. `engine` enumerates real layer edits, re-resolves, filters fixed
schema/protection premises, and searches for existence/cheapest repair/conflict.
`checker` independently applies declared edits and reconstructs inheritance with
a topological scan, then reevaluates every original predicate. It imports no
engine/resolver/predicate implementation. `tests/oracle.py` is a third small
exhaustive reference with separate loops, independent of all production modules.

For m targets with d_i explicit options, N = product(1+d_i). Exact repair visits
all N assignments; first witness can terminate satisfiability search early.
Each candidate includes a validated copy of the original input. Search is
exponential in editable targets; declare small release decisions, not a global
cloud fleet optimizer. Conflict deletion requires up to roughly 2C+1 bounded
searches for C predicates. Its shared max_states budget counts every candidate
across all those searches, including removal witnesses.

Inheritance resolution caches each layer snapshot, but a diamond duplicates
provider histories along paths. Time and memory include that expanded trace.
Checker reconstruction trades this trace for repeated ready-layer scans.
The SDK/CLI are synchronous and do not run user commands or contact networks.
No wall-clock deadline is promised by a state budget; graph/input work per state
also matters. Users should supervise oversized untrusted inputs with process
limits. The model is a finite validator, not a distributed consistency system.

Independent checks can find code divergence; the tests also enumerate all repair
costs/ties and validate claimed minimal conflicts for seeded small instances.
They cannot prove every implementation path correct or justify external rollout
safety. Rollout facts, health observations, traffic, zone outages and true capacity
are supplied by the caller and are not inferred.

All APIs return ordinary serializable dictionaries. Input snapshots are copied
at construction and edit application. Do not mutate a Problem's attributes while
using it; construct a new Problem for a new configuration. No concurrent mutation
guarantee. Numeric values and costs use exact arbitrary-precision Python integers;
there is no float/NaN handling in the supported field language.
