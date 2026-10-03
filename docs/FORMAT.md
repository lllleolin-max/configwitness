# Strict format v1

All object keys are closed to unknown members. The top-level required keys are
`version`, `fields`, `layers`, `environments`, `constraints`, `edits`, `protected`.
Optional `edit_scope` defaults to `leaf`; optional `description` is text.
Identifiers are exact, case-sensitive, nonempty strings up to 128 characters,
without control characters. No Unicode normalization or filesystem mapping.

Fields support exact JSON/Python `int`, `bool`, `string`, plus `nullable: true`.
Booleans are not integers. `required` defaults to true. No floats, nested maps,
lists, coercion, templates, expressions, remote imports or arbitrary code.
All source override values are type-checked, even if later overridden.

Each layer has unique `id`, ordered unique `parents`, and `overrides` mapping
declared fields to scalars or `{"$unset": true}`. Parent snapshots merge left to
right, shallowly by whole field, then the child overrides. A later parent's
inherited base value can override an earlier parent's own override. This is
intentional ordered snapshot precedence, not C3 linearization or CUE unification.
A diamond repeats provider events once per inheritance path. Missing parents
and cycles reject. Explicit null is present; unset suppresses inherited values;
absence has no provider. Required absent/unset fields make the current rollout
invalid but may be fixable by a future assignment.

Environments have unique `id` and one known `layer`. Multiple environments may
reference one layer. The same parent edit may affect many environments. Trace
lists providers in precedence order, including overridden values and unset;
the final event is the winning provider, even when it removes presence.

Supported predicates (nonempty unique known `envs` where applicable):

| Kind | Parameters | Meaning |
|---|---|---|
| range | envs, field:int, min and/or max:int | each concrete integer in bounds |
| sum | envs, field:int, min and/or max:int | exact replica/value total in bounds |
| allowed | envs, field, nonempty typed values | each present value belongs to list |
| equal | envs, field | every present value equal with exact type |
| distinct | envs, field | all present values pairwise different |
| failover | primary, backup, replicas:int field, region:string field, min_backup>=1 | nonnegative concrete counts and string regions; active primary requires backup minimum and different regions |

Null is a legal allowed/equal/distinct operand when its field is nullable;
integer predicates and failover reject null. A zero primary has no pairing
capacity requirement but both counts and regions must still be concrete.
Negative values are legal integers; reject them through range/failover constraints
when they represent replicas. Constraint IDs must be unique.

Each edit target has `layer`, `field`, nonempty `options`. An option has nonnegative
integer `cost` and `op` of `set` (typed `value` required), `unset` or `remove`
(value forbidden). KEEP is implicit, cost zero. Remove clears the direct override
and reveals parent precedence; unset suppresses it. The finite universe is the
Cartesian product of KEEP plus each target's options. One choice per target;
options and targets cannot repeat. No minimum budget/spend requirement. Equivalent
resolved configurations may have different source edits and remain distinct ties.

Scope `leaf` permits only environment layers never used as any layer's parent.
`declared-layers` permits any explicitly named source layer. Only those targets
can change; layers, graph, schema, environment IDs and constraints cannot change.
The optimum is relative to this universe, not all imaginable edits or costs.

Protected records use `env` + `field` or `layer` + `field`. They pin the original
**resolved** presence and value of that environment/layer field. Missing and
explicit null differ. Ancestor pins are checked even when its field is shadowed
in every environment. Pins do not lock a source syntax/provenance representation.

Conflict search removes only constraints. All other premises remain fixed.
Removal witnesses satisfy the returned subset without one member, not necessarily
the complete original constraint set. The independent proposal checker always
checks the complete original set, so removal witnesses are not rollout repairs.

Proposal v1 contains `source_sha256` of canonical input, exact declared `cost`,
and chosen edit option records. Hashes bind inputs but are not signatures or
authentication. Checker rejects stale source, altered cost, undeclared options,
duplicate targets, changed protections and failed original constraints.

CLI stdout is JSON. Exit 0: valid/SAT/optimal/trace/accepted; 1: invalid/UNSAT/rejected;
2: input/I/O errors; 3: UNKNOWN. `repair` can write a feasible incumbent on exit 3;
read its status before treating it as optimal. `apply` writes only an accepted
proposal. Inputs must be trusted as configuration assumptions, not as guarantees
that these finite predicates accurately describe an external system.
