# Pilot rationale / 为什么做

The prospective user is a platform engineer reviewing a bounded set of deployment
layer changes. A prospective buyer could be the team responsible for release
reliability and configuration governance. Neither has been validated with customer
interviews, usage or payment evidence.

The costly task is understanding how inherited settings combine across paired
regions, locating the actual source layer behind a failure, and reviewing a
small concrete repair without accidentally changing protected configurations.
CUE and OPA already establish configuration and policy validation as practical
workflows. ConfigWitness supplies an opinionated finite review bundle: provider
trace, separate current/future questions, protected layer edits, conflict premises,
complete repair ties when available, and an independent materialization check.

The executable contrast shows a local-only cost-zero choice fails the declared
standby requirement, while the full model chooses cost 2 and passes. The good
fixture shows no advantage, and the adverse fixture shows no finite solution.
The fourth fixture requires two actual local fixes and both baselines match the
full fleet optimum, illustrating another case with no distinctive benefit.
These are constructed engineering examples, not customer incidents, time savings,
avoided outage estimates or comparisons against an executed incumbent.

A pilot can export its small declarative slice to JSON, run validation/trace,
review the proposed source edit, then translate the generated configuration into
its existing deployment system. Measure reviewer minutes, number of rejected
locally-valid fleet changes, and agreement between these predicates and the team's
real capacity rules before any commercial claim. If a review currently takes T
minutes and this workflow takes t, the potential time change is T-t; both must
be measured, and maintenance/translation cost subtracted. Current T, t, adoption,
willingness to pay and actual revenue are all unknown.

中文：建设目的不是再写一份通用配置语言，而是提供一个可审查的小型发布修复流程。
继承来源、跨环境关系、不可更改字段和有限选项需要一起推理。它适合先做范围有限
的试点：人工定义关键约束，比较原流程与工具流程的审核用时，并核实配置规则与真实
部署是否一致。现阶段没有客户、收入或生产安全收益证据，不应把示例成本解释为钱。
