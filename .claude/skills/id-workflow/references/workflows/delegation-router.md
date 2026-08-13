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

三者的层级关系：

```text
Dynamic Workflow = 选择整条流程
Agent Team       = 选择一组能力协作
Subagent         = 执行一个隔离任务单元
```

main agent 必须按这个顺序决策：

```text
1. 先选 dynamic workflow
2. 再选 agent team
3. 最后决定是否启动一个或多个 subagent
```

## Selection Decision Matrix

| 要判断的问题 | 选择对象 | 何时使用 | 输出 |
|---|---|---|---|
| 这是什么类型的输入和生命周期？ | Dynamic Workflow | raw idea、TR3、approved alignment、test/build failed、D3A、General | workflow_id |
| 这一步需要哪一组能力？ | Agent Team | 需要发现/澄清/规划/知识检索/编码/验证中的一组协作 | selected_agent_team |
| 这一步是否需要隔离执行？ | Subagent | 需要读写代码、跑测试、分析失败、处理某个 execution unit 或 D3A Layer | selected_agents |

## When To Use Dynamic Workflow

使用 Dynamic Workflow 的信号：

- 输入类型改变：`raw_idea`、`tr3_doc`、`approved_alignment`。
- 任务生命周期改变：alignment、execution、verification_fix、build_fix。
- Domain 改变：general vs d3a。
- Lane 改变：fast / lite / complex。
- 状态改变：首次执行、测试失败、构建失败、需要 re-plan。

Dynamic Workflow 不直接执行任务；它只决定接下来应该调用哪些 agent team。

## When To Use Agent Team

使用 Agent Team 的信号：

- 需要多个能力串起来完成一个阶段。
- 需要同一阶段内的能力组合，例如 `Knowledge Team` 先 OKL 再 bounded grep。
- 需要 main agent 保留阶段级状态，但不保留所有工作细节。
- 任务处于 pre-alignment，不能启动实现 subagent，但可以使用 Intent / Alignment Team。

Agent Team 可以是串行，也可以由 main agent 拆成多个 subagent 调用。

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

| Lane | Dynamic Workflow | Agent Team | Subagent |
|---|---|---|---|
| fast | 通常单阶段 execution workflow | 通常只用 Planning + Verification，Knowledge 按需 | 默认 0 或 1 个；小改可由 main 生成 delegation 后单 subagent 执行 |
| lite | focused execution workflow | Planning + Knowledge as needed + Coding + Verification | 通常 1 个 coding subagent，失败时再加 analyzer |
| complex | staged workflow / DAG workflow | Planning + Knowledge + Coding + Verification 全部参与 | 多个 subagent；D3A 按 Layer Context Packet 拆 |

## Domain Influence

| Domain | Agent Team | Subagent 策略 |
|---|---|---|
| general | Planning Team -> Coding Team -> Verification Team | `general-coder` per execution unit |
| d3a | Planning Team -> Knowledge Team -> Coding Team -> Verification Team | `d3a-layer-coder` per Layer Context Packet，`dt-test-writer` per required DT domain |
| failure_fix | Verification Team -> Knowledge Team if needed -> Coding Team | `build-error-analyzer` first，再 targeted fix subagent |

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
