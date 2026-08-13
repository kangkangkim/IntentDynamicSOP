# Delegation Router

Delegation Router 约束 main agent 只做 planning 和 delegation。

main agent 不直接承担重型执行任务。它只负责：

```text
understand input
-> select dynamic workflow
-> build plan
-> create Delegation Contract
-> dispatch agent team / subagent
-> summarize returned evidence
-> decide DONE / re-plan / escalate
```

## Main Agent Role

```yaml
main_agent_role: planning_and_delegation_only
```

main agent 允许做：

- 读取最小入口规则。
- 判断 input maturity。
- 选择 Domain Module。
- 选择 Lane。
- 选择 dynamic workflow。
- 生成 execution unit。
- 生成 Context Packet / Layer Context Packet。
- 生成 Delegation Contract。
- 分派 agent team / subagent。
- 汇总 agent result。
- 基于工具 evidence 判断 DONE / re-plan / escalate。

main agent 禁止做：

- 直接消化完整 OKL 文档。
- 直接消化全量 grep / CodeGraph 输出。
- 直接消化完整 build / test log。
- 在 approved Alignment Pack 前写实现代码。
- 直接执行复杂实现。
- 把 subagent session 全量合并回 main session。
- 用 provider finding 替代 tool evidence。

## Dynamic Workflow Selection

```text
raw_idea
  -> intent-discovery team
  -> intent-grilling team
  -> intent-alignment

tr3_doc
  -> tr3 parse / contract gap check
  -> intent-grilling team if needed
  -> intent-alignment

approved_alignment + general
  -> general coding team
  -> verification team

approved_alignment + d3a
  -> d3a planning
  -> d3a layer coding team
  -> dt test / tran build verification team

test_or_build_failed
  -> build-error-analyzer
  -> targeted knowledge team if needed
  -> targeted fix delegation
```

## Agent Teams

### Intent / Alignment Team

```text
intent-discovery
intent-grilling
intent-alignment
```

职责：

- raw idea 发散。
- TR3 或 draft spec 缺口追问。
- Alignment Pack 人类可读确认。

输出给 main：

```text
draft spec summary
critical questions
approved Alignment Pack summary
```

### Knowledge Team

```text
OKL adapter
bounded grep adapter
targeted CodeGraph adapter
repo_search adapter
```

职责：

- 根据 provider-selection-matrix 获取仓库事实和知识线索。
- 只返回 `summary / refs / keywords`。
- 保留 `evidence_ref`。

输出给 main：

```text
provider_findings_summary
refs
keywords
confidence
```

### Planning Team

```text
domain resolver
lane resolver
execution-unit planner
context-packet builder
```

职责：

- 选择 Domain / Lane。
- 拆 execution unit。
- 为 D3A 拆 Layer Context Packet。
- 判断是否需要多个 subagent。

输出给 main：

```text
plan summary
execution units
delegation candidates
context packet refs
```

### Coding Team

```text
general-coder
d3a-layer-coder
dt-test-writer
```

职责：

- 在 approved contract 后执行局部实现。
- 每个 execution unit 控制 `<= 500 LOC`。
- 生成 RED / GREEN / tool evidence。

输出给 main：

```text
changed_paths
evidence_refs
summary
blockers
```

### Verification Team

```text
dt-build
tran-build
build-error-analyzer
evidence summarizer
```

职责：

- 运行或记录 placeholder tool evidence。
- 分析失败并生成 targeted fix task。
- 不宣布 DONE，DONE 仍由 main 根据 gates 判断。

输出给 main：

```text
verification_status
evidence_refs
failure_summary
targeted_fix_task
```

## Delegation Flow

```text
main agent
  -> selects dynamic workflow
  -> creates Delegation Contract
  -> sends bounded Context Packet
  -> subagent / agent team works in isolated session
  -> returns Agent Result
  -> main keeps only summary / evidence_ref / blockers
```

## Mandatory Return Boundary

Subagent / agent team 必须返回：

```text
status
summary
changed_paths
evidence_refs
blockers
context_to_keep
context_to_drop
```

Subagent / agent team 禁止返回：

```text
full_subagent_session
full_logs
full_search_results
unbounded_repo_context
```

## Re-plan Rule

如果 agent result 显示 scope 不满足、evidence 不足、超过 500 LOC、或影响范围扩大：

```text
main agent
  -> does not continue coding directly
  -> creates new Delegation Contract or escalates
```

