# Automated Closure Loop

Automated Closure Loop 是 Human Alignment 通过后的默认执行模式。

它负责：

```text
Planner
  -> Knowledge Gate
  -> Knowledge Load Plan
  -> Capability Selector
  -> Delegation Router
  -> Execution Authorization Gate
  -> Agent Team / Subagent Execution
  -> Knowledge Consumption Verification
  -> Verification
  -> Error Analyzer / Targeted Fix / Re-plan
  -> verify_completion.rb
  -> DONE
```

## 默认不人工卡点

Human Alignment approve 后，后续步骤默认自动执行和验证。

不再默认设置：

- Plan Check。
- Evidence Check。
- Completion Check。

这些检查由 workflow gate 和工具证据自动完成。

## 自动闭环要求

- Planner 必须遵守已批准的 scope / contract / completion gate。
- Planner 必须把代码变更拆成不超过 500 行的 execution unit。
- Delegation Router 必须生成 Delegation Contract。
- Execution Authorization Gate 必须在任何 repo mutation 前返回 `AUTHORIZED`。
- Execution Authorization 必须绑定同一 execution unit 的 READY Knowledge Load Plan。
- Completion 前必须验证 Knowledge Consumption Receipt；计划外知识或缺失 provider result 会阻断。
- Main agent 只做 planning_and_delegation_only；任何 Lane 都不得直接修改代码、测试、构建文件或 targeted fix。
- General executor 必须加载 `idc-general-coding`；GC Adapter 只能作为已选择的内层原子能力。
- 如果无法真实派发 subagent / agent team，返回 `BLOCKED_DELEGATION_REQUIRED`，不能由 main agent 兜底实现。
- Knowledge Gate 只能加载当前执行单元需要的知识。
- Agent Team / Subagent Execution 必须产出工具证据。
- Subagent 只能回传 summary / changed_paths / evidence_refs / blockers / context_to_keep / context_to_drop。
- 每个 execution unit 都必须有自己的 evidence。
- Verification Gate 必须检查 Lane completion requirements。
- Verification Gate 必须检查 authorization ID、dispatch tool-call ref 和 executor session ref。
- Domain Module 可以追加自己的 completion gate。
- 失败时先进入 Error Analyzer / Targeted Fix / Re-plan。

## 异常回流

只有命中 Escalation Policy 才回到 Human Alignment：

```text
scope_expansion_required
api_contract_change_required
planner_cannot_satisfy_scope
tool_evidence_unavailable
repeated_fix_failure
domain_or_lane_reclassification_required
tr3_conflicts_with_repo_facts
completion_gate_cannot_be_satisfied
execution_unit_too_large
```

需要用户做 escalation 决策时，必须通过 `AskUserTool` 发出 Escalation View 的选项；如果 `AskUserTool` 不可用，返回 `BLOCKED_NEEDS_ASK_USER_TOOL`。

## 输出

```yaml
automated_closure_result:
  status: done | fixed | replanned | escalated
  evidence: []
  completion_summary: string
  escalation_trigger: null
```
