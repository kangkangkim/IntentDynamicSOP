# Lane Completion

所有 Lane 都必须自闭环。

Lane 不表示要不要闭环，只表示闭环证据强度。

```text
fast = 小闭环
lite = 标准闭环
complex = 强闭环
```

## Fast 小闭环

Fast 至少需要：

```text
task_summary_exists
acceptance_criteria_checked
changed_files_reviewed
basic_verification_evidence_exists
completion_summary_exists
```

适合 README、注释、typo、小范围无行为变化任务。

## Lite 标准闭环

Lite 至少需要：

```text
task_contract_exists
acceptance_criteria_checked
focused_plan_executed
relevant_context_used
test_or_build_evidence_exists
completion_summary_exists
```

适合普通 bugfix、单模块功能增强、范围可控的开发任务。

## Complex 强闭环

Complex 至少需要：

```text
full_task_contract_exists
detailed_plan_or_dag_executed
knowledge_gate_result_exists
evidence_plan_satisfied
required_tests_or_builds_passed
audit_or_review_completed
completion_summary_exists
```

适合跨模块、高风险、复杂验证、多 subagent 或需要 DAG 的任务。

## 通用规则

- 任何 Lane 都不能无 evidence 标记 DONE。
- 任何 repository mutation 都必须有 Execution Receipt：authorization ID、
  dispatch tool-call ref、executor session ref 和 loaded Domain execution Skill。
- 缺少 Delegation provenance 时，即使测试通过也不能标记 DONE。
- 每个 execution unit 必须有与 Authorization 相同 `knowledge_plan_id` 的
  `Knowledge Consumption Result: VERIFIED`；缺失 required knowledge、缺少
  provider/search result，或加载计划外知识时不能 DONE。
- 任何 Lane 都必须输出 completion summary。
- 如果 Lane 的 minimum requirements 无法满足，必须升级 Lane 或返回 targeted fix / re-plan。
- Domain Module 可以在 Lane requirements 之上追加自己的 completion gate。

例如 D3A：

```text
Lane requirements
+
required DT GREEN
+
tran_build PASS
```
