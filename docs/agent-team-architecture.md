# Agent Team Architecture

IDC 的目标是让 main agent 成为 planning / delegation core，而不是全能执行者。

## 核心原则

```text
Main Agent = planner + delegation router + evidence summarizer
Subagent / Agent Team = bounded execution worker
Dynamic Workflow = 根据输入和状态选择 agent team
```

main agent 长期持有：

- 用户意图。
- approved contract。
- Domain / Lane / workflow decision。
- execution unit 队列。
- Delegation Contract 摘要。
- subagent 返回的 evidence summary。
- blocker / re-plan / escalation 状态。

main agent 不长期持有：

- 完整 OKL 文档。
- 完整 grep / CodeGraph 输出。
- 完整 build / test log。
- 完整 subagent session。
- 大量临时实现上下文。

## Agent Team

```text
Intent / Alignment Team
  -> intent-discovery
  -> intent-grilling
  -> intent-alignment

Knowledge Team
  -> OKL adapter
  -> bounded grep adapter
  -> targeted CodeGraph adapter

Planning Team
  -> domain resolver
  -> lane resolver
  -> execution-unit planner
  -> context-packet builder

Coding Team
  -> general-coder
  -> d3a-layer-coder
  -> dt-test-writer

Verification Team
  -> dt-build
  -> tran-build
  -> build-error-analyzer
  -> evidence summarizer
```

## 什么时候用谁

先区分三个层级：

```text
Dynamic Workflow:
  选择整条路怎么走。

Agent Team:
  多个 subagent 需要交流、交接或共享中间结果。

Subagent:
  执行一个隔离的 execution unit / Layer Context Packet / failure analysis。
```

### 用 Dynamic Workflow 的时候

当问题是“现在该走哪条流程”时，用 Dynamic Workflow。

典型触发：

- 输入是一句话需求。
- 输入是 TR3 文档。
- 用户已经 approve Alignment Pack。
- Domain 是 General。
- Domain 是 D3A。
- 测试或 build 失败，需要修复闭环。
- Lane 从 fast/lite 升级到 complex。

输出是：

```text
workflow_id
next_agent_team
next_required_contract
```

### 用 Agent Team 的时候

当问题是“多个 subagent 是否需要交流、交接或共享中间结果”时，用 Agent Team。

典型触发：

- subagent A 的输出是 subagent B 的输入。
- 多个 subagent 并行工作后，需要合并成一个阶段结果。
- analyzer / fixer / verifier 之间需要形成闭环。
- D3A 多 Layer 之间需要由 planner 汇总交接结果。
- build-error-analyzer 的结论要交给 targeted fix subagent。

不要用 Agent Team 的情况：

- 只有一个 execution unit。
- 只有一个 subagent 可以独立完成。
- 只是 main agent 做流程选择。
- 只是一次 OKL / grep / CodeGraph provider query。
- 只是生成 Delegation Contract。

输出是：

```text
selected_agent_team
team_result_summary
subagent_handoff_graph
delegation_candidates
```

### 用 Subagent 的时候

当问题是“需要隔离执行一个具体任务”时，用 Subagent。

必须同时满足：

- 已有 approved Alignment Pack。
- 已有 Delegation Contract。
- 已有 execution unit 或 Layer Context Packet。
- 有明确 allowed_paths / constraints / expected_return。

典型触发：

- 写一个 General execution unit。
- 写一个 D3A Layer execution unit。
- 准备一个 DT domain 的 RED evidence。
- 分析一次 build/test failure。
- 做一个 targeted fix。

不要用 Subagent 的情况：

- Brainstorming。
- Grill Me。
- Human Alignment。
- Domain / Lane 选择。
- 只是规划或生成 Delegation Contract。

## 选择规则表

| 场景 | Dynamic Workflow | Agent Team | Subagent |
|---|---|---|---|
| 一句话需求 | raw_idea_alignment | 只有 discovery / grilling 需要 handoff 时使用 | 不启动实现 subagent |
| TR3 文档 | tr3_alignment | 只有 parser / gap-check / grilling 需要 handoff 时使用 | 不启动实现 subagent |
| General 已批准 | general_execution | 多个 execution unit、coder/verifier 需要交接时使用 | `general-coder` per execution unit |
| D3A 已批准 | d3a_execution | Layer coder / DT writer / tran build verifier 需要交接时使用 | `d3a-layer-coder` per Layer Context Packet |
| DT 测试准备 | d3a_execution | test writer 和 layer coder 需要 RED/GREEN handoff 时使用 | `dt-test-writer` per DT domain |
| build/test 失败 | verification_fix / build_fix | analyzer -> fixer -> verifier 需要闭环时使用 | `build-error-analyzer` then targeted fix subagent |
| complex lane | staged workflow / DAG workflow | 多 subagent 存在 DAG、review、handoff、merge 时使用 | 多 subagent，按 packet 拆 |

## Dynamic Workflow

```text
一句话需求
  -> Intent / Alignment Team
  -> Planning Team
  -> Coding Team
  -> Verification Team

TR3 文档
  -> Planning Team
  -> Intent / Alignment Team if contract gap exists
  -> Coding Team
  -> Verification Team

General Coding
  -> Planning Team
  -> Knowledge Team as needed
  -> general-coder
  -> Verification Team

D3A Coding
  -> Planning Team
  -> Knowledge Team as needed
  -> d3a-layer-coder per Layer Context Packet
  -> dt-test-writer
  -> tran-build

失败修复
  -> build-error-analyzer
  -> Knowledge Team if needed
  -> targeted fix delegation
```

## Delegation Contract

每次派活前，main agent 生成 Delegation Contract：

```yaml
delegation_contract:
  workflow_id: d3a_execution
  selected_agent_team: coding
  selected_agents:
    - d3a-layer-coder
  main_agent_role: planning_and_delegation_only
  context_packet_ref: layer-context-packet-do
  expected_return:
    - summary
    - changed_paths
    - evidence_refs
    - blockers
    - context_to_keep
    - context_to_drop
  forbidden_return:
    - full_subagent_session
    - full_logs
    - full_search_results
```

## Context Boundary

```text
Main -> Subagent:
  approved contract
  execution unit
  Context Packet
  allowed paths
  verification contract

Subagent internal:
  local file reads
  bounded provider queries
  local test/build attempts

Subagent -> Main:
  summary
  changed paths
  evidence refs
  blockers
  context_to_keep
  context_to_drop
```

## DONE Authority

Subagent 不能宣布整个任务 DONE。

DONE 只能由 main agent 根据以下证据判断：

- Lane completion requirements。
- Domain completion gate。
- TDD RED then GREEN evidence。
- D3A required DT GREEN。
- D3A `tran_build PASS`。
- General required tests / build / static checks。
