# Delegation Router

Delegation Router 约束 main agent 只做 planning 和 delegation。

main agent 不直接承担重型执行任务。它只负责：

```text
understand input
-> select IDC workflow route
-> decide whether official dynamic workflow is needed
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
- 选择 IDC workflow route。
- 判断是否需要 official dynamic workflow。
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

## Workflow Router Selection

三者的层级关系：

```text
IDC Workflow Router      = 选择普通生命周期流程
Official Dynamic Workflow = 脚本化、大规模、可复跑的 subagent 编排
Agent Team               = 多个 subagent 需要交流或交接
Subagent                 = 执行一个隔离任务单元
```

main agent 必须按这个顺序决策：

```text
1. 先选 IDC workflow route
2. 再选 agent team
3. 最后决定是否启动一个或多个 subagent
4. 只有大规模、可复跑、脚本化 fan-out 时，才升级到 official dynamic workflow
```

## Selection Decision Matrix

| 要判断的问题 | 选择对象 | 何时使用 | 输出 |
|---|---|---|---|
| 这是什么类型的输入和生命周期？ | IDC Workflow Router | raw idea、TR3、approved alignment、test/build failed、D3A、General | workflow_id |
| 是否需要脚本化、大规模、可复跑编排？ | Official Dynamic Workflow | many files / many execution units / fan-out collect verify / repeat-until-pass / background run | dynamic_workflow_required |
| 多个 subagent 是否需要交流、交接或共享中间结果？ | Agent Team | subagent 之间存在依赖、握手、审查、并行汇总或 failure handoff | selected_agent_team |
| 这一步是否需要隔离执行？ | Subagent | 需要读写代码、跑测试、分析失败、处理某个 execution unit 或 D3A Layer | selected_agents |

## When To Use IDC Workflow Router

使用 IDC Workflow Router 的信号：

- 输入类型改变：`raw_idea`、`tr3_doc`、`approved_alignment`。
- 任务生命周期改变：alignment、execution、verification_fix、build_fix。
- Domain 改变：general vs d3a。
- Lane 改变：fast / lite / complex。
- 状态改变：首次执行、测试失败、构建失败、需要 re-plan。

IDC Workflow Router 不直接执行任务；它只决定接下来应该调用哪些 agent team / subagent。

## IDC Workflow Trigger Model

IDC Workflow Router 是事件触发的状态路由，不是 official dynamic workflow。

main agent 每次收到以下事件，都必须重新判断 workflow：

```text
new_user_input
normalized_request_ready
human_alignment_approved
domain_or_lane_resolved
agent_result_returned
test_failed
build_failed
fix_failed
scope_changed
completion_gate_blocked
```

### Workflow Trigger Inputs

```yaml
workflow_trigger_input:
  input_maturity: raw_idea | structured_requirement | tr3_design_doc | approved_alignment
  human_alignment_status: missing | pending | approved
  selected_domain: unknown | general | d3a
  selected_lane: unknown | fast | lite | complex
  current_state: intake | alignment | planning | execution | verification | fix | done | escalated
  latest_event: new_user_input | agent_result_returned | test_failed | build_failed | scope_changed | completion_gate_blocked
  failure_kind: none | test | build | tool_evidence_unavailable | repeated_fix_failure
```

### Workflow Routing Priority

按优先级选择第一个命中的 workflow：

| Priority | Trigger | workflow_id | Entry condition | Exit condition |
|---:|---|---|---|---|
| 1 | `human_alignment_status != approved` and `input_maturity = raw_idea` | `raw_idea_alignment` | 用户输入只有目标或愿望 | 产出 approved Alignment Pack 或 escalation |
| 2 | `human_alignment_status != approved` and `input_maturity = tr3_design_doc` | `tr3_alignment` | TR3 已解析但未批准 | 产出 approved Alignment Pack 或 escalation |
| 3 | `failure_kind = test` or `latest_event = test_failed` | `verification_fix` | 已有失败测试 evidence | targeted fix evidence 或 escalation |
| 4 | `failure_kind = build` or `latest_event = build_failed` | `build_fix` | 已有失败 build evidence | targeted fix evidence 或 escalation |
| 5 | `human_alignment_status = approved` and `selected_domain = d3a` | `d3a_execution` | approved Alignment Pack + D3A module | required DT GREEN + `tran_build PASS` |
| 6 | `human_alignment_status = approved` and `selected_domain = general` | `general_execution` | approved Alignment Pack + general module | required test/build/static evidence pass |
| 7 | no route matched | `escalation_required` | 缺少关键路由信息 | Human Alignment / clarification |

### Workflow Switch Conditions

运行中只允许在这些情况下切换 workflow：

- Human Alignment 从 pending 变 approved：alignment workflow -> execution workflow。
- Domain 从 unknown 变 general/d3a：planning route -> domain execution workflow。
- Test evidence failed：execution workflow -> `verification_fix`。
- Build evidence failed：execution workflow -> `build_fix`。
- Scope 或 API contract 变化：当前 workflow -> alignment workflow 或 escalation。
- Repeated fix failure：fix workflow -> escalation。
- Completion gate satisfied：current workflow -> done。

### Workflow Output

IDC Workflow Router 必须输出：

```yaml
workflow_selection_result:
  workflow_id: raw_idea_alignment | tr3_alignment | general_execution | d3a_execution | verification_fix | build_fix | escalation_required
  trigger_event: string
  trigger_reason: string
  entry_condition_matched: string
  next_agent_team_candidate: intent_alignment | planning | coding | verification | none
  allowed_next_states: []
```

## When To Use Official Dynamic Workflow

Official Dynamic Workflow 只在“编排复杂到值得脚本化”时使用。

使用信号：

- `many_files`: 需要处理很多文件或模块。
- `many_execution_units`: execution unit 数量很多。
- `fanout_collect_verify`: 需要 fan-out -> collect -> merge -> verify。
- `repeat_until_pass`: 需要循环执行 fix -> verify，直到通过或触发停止条件。
- `large_migration`: 大规模迁移、批量替换、跨模块更新。
- `cross_checked_research`: 多 subagent 交叉调研、互相校验。
- `background_run_needed`: 任务很长，需要后台运行和进度查看。
- `save_and_rerun_needed`: 这个编排以后要保存复用。

不要使用 Official Dynamic Workflow 的情况：

- 只是 raw idea / TR3 / approved alignment 的路由判断。
- 只是 Domain / Lane 判断。
- 只有一个 execution unit。
- 一个 subagent 能独立完成。
- 多个 subagent 只是简单串行，且不需要脚本化循环 / fan-out / collect。
- 只是 pre-alignment 或人工确认。
- 普通失败修复，除非进入多轮 repeat-until-pass。

## When To Use Agent Team

使用 Agent Team 的信号：

- 至少两个 subagent 需要交流、交接或共享中间结果。
- 一个 subagent 的输出会成为另一个 subagent 的输入。
- 多个 subagent 可以并行，但必须由 team 汇总成一个阶段结果。
- 需要 reviewer / analyzer / fixer 之间形成闭环。
- 需要 planner 把多个 subagent 的结果合并成下一轮 Delegation Contract。

不要使用 Agent Team 的情况：

- 只有一个隔离 execution unit。
- 只是流程选择。
- 只是读取一个 provider summary。
- main agent 自己可以生成 plan 或 Delegation Contract。

Agent Team 的核心不是“能力很多”，而是“subagent 之间必须交流”。

## When To Use Subagent

启动 Subagent 的信号：

- 已经有 approved Alignment Pack。
- 已经有 Delegation Contract。
- 已经有明确 execution unit 或 Layer Context Packet。
- 需要隔离读写代码、准备测试、跑验证或分析失败。
- 任务可能污染 main session，例如长日志、局部搜索、局部实现细节。

不要启动 Subagent 的情况：

- 还在 raw idea Brainstorming。
- 还在 Grill Me / Human Alignment。
- 只是选择 Domain / Lane。
- 只是生成 plan 或 Delegation Contract。
- 没有明确 Context Packet。

## Lane Influence

| Lane | IDC Workflow Router / Official Dynamic Workflow | Agent Team | Subagent |
|---|---|---|---|
| fast | 通常单阶段 execution workflow | 通常不用 agent team，除非验证和修复之间必须交接 | 默认 0 或 1 个；小改可由 main 生成 delegation 后单 subagent 执行 |
| lite | focused execution workflow | 有 coding -> verification 或 analyzer -> fixer 交接时使用 | 通常 1 个 coding subagent，失败时再加 analyzer |
| complex | staged workflow / DAG workflow | 多 subagent 存在 DAG、review、handoff、merge 时使用 | 多个 subagent；D3A 按 Layer Context Packet 拆 |

## Domain Influence

| Domain | Agent Team | Subagent 策略 |
|---|---|---|
| general | 只有多个 general-coder / verifier 需要交接时升级 team | `general-coder` per execution unit |
| d3a | Layer coder、DT writer、tran build verifier 需要交接时升级 team | `d3a-layer-coder` per Layer Context Packet，`dt-test-writer` per required DT domain |
| failure_fix | analyzer 结果需要交给 fixer / verifier 时升级 team | `build-error-analyzer` first，再 targeted fix subagent |

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
  -> selects IDC workflow route
  -> decides whether official dynamic workflow is needed
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
