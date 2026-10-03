# ConfigWitness

Review an inherited rollout as a fleet, trace the values that caused a failure,
and propose edits to real override layers within a declared finite universe.
The proposal is independently re-resolved and checked before it is materialized.

A standby can satisfy its own replica range while lacking enough capacity for
its paired primary. A local validator will approve that configuration; the
synthetic example below needs a cost-2 standby edit to satisfy both fleet total
and failover constraints. Costs and capacity thresholds are caller assumptions,
not measured production costs or availability forecasts.

## Install and run / 安装与运行

Python 3.11 or later. From this repository:

```sh
python -m pip wheel . --no-deps --wheel-dir dist
python -m pip install dist/configwitness-0.1.0-py3-none-any.whl
configwitness validate examples/failover.json
configwitness trace examples/failover.json prod-west replicas
configwitness solve examples/failover.json
configwitness repair examples/failover.json --output proposal.json
configwitness check examples/failover.json proposal.json
configwitness apply examples/failover.json proposal.json --output rollout.repaired.json
configwitness validate rollout.repaired.json
python tools/workflow.py
python tools/contrast.py
python -m unittest discover -s tests -v
```

Output filenames must be new; existing files are preserved and rejected.
`validate` initially returns exit 1 and `INVALID`: the declared fleet total is
5 rather than 6 and standby replicas are 1 rather than the required 2.
`trace` shows base=2, standby=1, winning provider `standby`.
`solve` returns `SAT`; `repair` returns `OPTIMAL`, cost 2, one optimum after
examining 9 assignments. The proposal sets `standby.replicas` to 2. The actual
new input file validates as `VALID`. `tools/workflow.py` drives the installed
console command and asserts this whole sequence using temporary files.

中文：本工具面向审核多环境发布配置的平台工程师。它先检查当前发布是否满足
副本总数、区域放置和主备配对等约束，随后追溯继承来源，再在明确列出的可编辑
选项内求修复。修复作用在父层或叶层源配置上，不直接篡改解析后的字典。最后
独立检查所有原始约束与保护值并生成实际新配置，供用户审核后集成到自己的发布流程。
示例是合成场景，成本是调用者填写的相对整数，不代表真实费用或上线安全结论。

## SDK / 程序接口

```python
from configwitness import load, validate, trace, solve, repair, check_proposal, apply_edits

p = load("examples/failover.json")
assert validate(p)["status"] == "INVALID"
assert solve(p)["status"] == "SAT"
r = repair(p, max_states=100_000, max_repairs=20)
if r["repairs"]:
    proposed = r["repairs"][0]
    assert check_proposal(p, proposed)["accepted"]
    changed = apply_edits(p, proposed["edits"])
    assert validate(changed)["status"] == "VALID"
```

Search does not deploy anything. `OPTIMAL` is asserted only after the complete
finite universe has been enumerated. A truncated repair returns `UNKNOWN`,
possibly with a feasible incumbent and upper-bound cost. An incumbent can be
checked but is not certified cheapest. `SAT` is a concrete existence witness;
`UNSAT` needs complete enumeration. Current validity is independent of this
future-assignment question. The checker certifies feasibility and declared cost;
it deliberately does not certify optimality.

`configwitness conflict examples/no-finite-repair.json` returns an
inclusion-minimal constraint subset under fixed schema, inheritance, finite
domains, unedited overrides and protection snapshots. It can return an empty
subset if those premises alone cannot produce concrete required fields.
It does not find the smallest-cardinality conflict. Exhausted conflict work
returns `UNKNOWN` with `minimal=false`, and does not publish a partial core.

## Demonstrated distinction and boundaries

`tools/contrast.py` runs local-only minimum-cost repair and single-target greedy
local repair with the **same** original input, editable options, costs, schema,
and protected-value rules. Both baselines omit only relational constraints.
The output checks their proposed choices against the full original fleet:

| Synthetic case | Fleet repair | Local-only / greedy |
|---|---|---|
| legal local replicas, invalid failover | cost 2, valid | cost 0, invalid |
| already good fleet | cost 0, valid | cost 0, valid |
| finite universe cannot meet total | UNSAT | locally legal, fleet invalid |
| two independent local replica fixes | cost 2, valid | cost 2, valid |

This demonstrates the interaction of inherited provenance, actual layer edits,
fleet predicates and protection-aware finite repair. It is not a benchmark
against CUE or OPA and makes no claim that either lacks these capabilities.
[CUE's specification](https://cuelang.org/docs/reference/spec/) describes typed
constraints, unification, disjunctions and comprehensions.
[OPA's policy testing](https://www.openpolicyagent.org/docs/policy-testing)
supports parameterized policy tests and data-loaded test cases. These approaches
and finite constraint search/minimal-conflict techniques are prior art, not
new inventions here. Sources verified 2026-10-03. This project's JSON language
is custom, with no CUE/Rego compatibility claim.

See [format and subset](docs/FORMAT.md), [architecture](docs/ARCHITECTURE.md),
[pilot rationale](docs/PILOT.md), [security](SECURITY.md),
[contributing](CONTRIBUTING.md), and [review corrections](docs/ITERATIONS.md).

Actual customers, adoption, revenue and willingness to pay are unknown. Local
tests and checked-in CI are evidence of this artifact, not production assurance.
