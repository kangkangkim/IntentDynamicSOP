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

