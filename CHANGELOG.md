# Changelog

## 0.2.0 — 2026-10-05

- Reuse candidate schema/protection and full-predicate evaluation within one
  conflict call. Retain at most 4,096 lazy candidate slots within a conservative
  1 MiB accounted-byte budget; fall back to ordinary evaluation when full.
- Preserve logical state counting, UNKNOWN prefixes, ordered core/removal
  witnesses, source/proposal formats and all public search/repair semantics.
- Add an independent finite raw reference, cache admission/fallback regressions,
  and a runnable installed work-count probe. Document measured gains, small-case
  overhead, higher memory in the full-cache case and the scope of byte accounting.
- Make CI install the wheel it actually builds without a hardcoded version.

See [the update record](docs/UPDATE_0_2_0.md) for evidence and limits.

## 0.1.0

Initial finite inherited-fleet validation, provenance, repair, independent
proposal checking and minimal conflict evidence. The actual original correction
history and its attribution corrections remain in [ITERATIONS](docs/ITERATIONS.md).
