# Automated Closure Loop

Automated Closure Loop 是 Human Alignment 通过后的默认执行模式。

它负责：

```text
Planner
  -> Knowledge Gate
  -> Knowledge Load Plan
  -> Capability Selector
  -> Technical Plan Confirmation (AskUserTool, framework floor)
  -> Delegation Router
  -> Execution Authorization Gate
  -> Agent Team / Subagent Execution
  -> Knowledge Consumption Verification
  -> Verification
  -> Error Analyzer / Targeted Fix / Re-plan
  -> verify_completion.py
  -> DONE
```

## 默认不人工卡点

Human Alignment approve 后，后续步骤默认自动执行和验证。

Plan Check 以 Technical Plan Confirmation 的形式按框架 floor 恢复：d3a 与
全部 lane（fast / lite / complex）在 Execution Authorization 前都必须经
`AskUserTool` 确认技术方案三件（计划件本体、API Contract、DT 设计）；它只确认
技术方案，不重新对齐任务方向 / scope，floor 不可通过 team-config 关闭。

不再默认设置：

- Evidence Check。
- Completion Check。

这些检查由 workflow gate 和工具证据自动完成。

## Pre-execution Gap Check

Before entering the Knowledge Gate, if `effective.self_optimization.mode != disabled`:

```
scan event_store_ref for adaptation-events matching:
  - domain == current domain
  - selected_lane == current lane
  - execution_unit_ref == current execution unit
  - gap_class == knowledge_gap

if matching_event_count >= 2:
  emit AskUserTool:
    title: "Pre-execution Warning: Repeated Knowledge Gap Detected"
    body: |
      This execution unit has triggered knowledge_gap events N times in prior runs.
      Recommended: add knowledge_hints to team-config.yaml before proceeding.
    options:
      - "Continue execution"
      - "Pause to update team-config knowledge_hints first"
```

## 自动闭环要求

- Planner 必须遵守已批准的 scope / contract / completion gate。
- Planner 必须把代码变更拆成不超过 500 行的 execution unit。
- Technical Plan Confirmation 必须在 Execution Authorization 前完成（框架 floor：d3a 与全部 lane），且计划件必须先落盘。
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

## Error Pattern Library Hook

When `build-error-analyzer` processes a build failure, and
`effective.self_optimization.mode != disabled`:

```
1. Query error-patterns library:
   load: references/knowledge/error-patterns.md
   match: current error signature against known patterns
   if match found:
     apply fast-fix path from matched pattern
     write adaptation-event:
       event_type: verification_failed
       gap_class: verification_gap
       observed_summary: "known pattern matched: <pattern_id>, fast-fix applied"
   if no match:
     proceed with normal build-error-analyzer analysis
     after fix is identified, append new pattern entry to error-patterns.md:
       pattern_id: auto-generated from run_id + error hash
       error_signature: bounded redacted error fingerprint
       fast_fix_hint: the fix approach identified
       first_seen_run: current run_id
       occurrence_count: 1

2. Hard rules:
   - Error signatures must be redacted (no private paths, internal APIs, real symbols).
   - Pattern library is append-only from automation; human may edit or remove entries.
   - Fast-fix hints are suggestions only; executor must still verify GREEN evidence.
```

## Routing Gap Hook

When a re-plan is triggered or escalation signal `domain_or_lane_reclassification_required`
fires, and `effective.self_optimization.mode != disabled`, write a routing gap event:

```
if re_plan_triggered OR escalation == domain_or_lane_reclassification_required:
  if effective.self_optimization.mode != disabled:
    write adaptation-event to event_store_ref:
      event_type: route_corrected
      gap_class: routing_gap
      original_decision_ref: the original route/lane decision ref
      corrected_decision_ref: the corrected route/lane decision ref
      observed_summary: bounded redacted summary of what changed and why
      evidence_refs: link to current run's alignment pack ref
```

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

## Post-DONE: Self-Optimization Observe Hook

After `verify_completion.py` returns `DONE`, run the following conditional block
before returning `automated_closure_result`:

```
if effective.self_optimization.mode != disabled:
  1. Write one adaptation-event to `effective.self_optimization.event_store_ref`
     using the schema at:
     references/schemas/adaptation-event.schema.yaml
     Fields to populate:
       - run_id: current run_id
       - execution_unit_ref: current execution unit
       - domain / lane_applicability / selected_lane: from current context
       - event_type: set based on any routing corrections, knowledge gaps,
           verification failures, or workflow deviations observed in this run
       - gap_class: classify from the 7 gap classes defined in self-optimization.md
       - observed_summary: bounded, redacted, portable summary
       - evidence_refs: link to any RED/GREEN/build evidence from this run

  2. Count adaptation-events with matching gap_class in the event_store.
     If count >= effective.self_optimization.pattern_threshold (default: 3):
       Emit proposal via AskUserTool:
         - Title: "Self-Optimization Proposal Available"
         - Body: gap_class, supporting_event_refs count, proposed team-overlay
           change (per optimization-proposal.schema.yaml)
         - Options: [Generate Proposal, Skip]
       If user selects "Generate Proposal":
         invoke idc-self-optimization in propose_only mode.

  3. Hard rules (always enforced):
     - Never modify team-config.yaml, IDC Core, or any completion gate automatically.
     - Never infer enterprise facts from model guesses.
     - Redact private code, logs, paths, APIs from event summaries.
     - promotion_requires_human_alignment: true (always).
```
