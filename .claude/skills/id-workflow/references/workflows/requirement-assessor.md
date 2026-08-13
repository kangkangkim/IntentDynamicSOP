# Requirement Assessor

Requirement Assessor 判断任务信息是否足够进入 specification。

它只负责决策：

```text
NEED_CLARIFICATION
READY_FOR_SPEC
```

它不负责澄清、设计、规划或写代码。

当决策为 `NEED_CLARIFICATION` 时，下一步交给 `workflows/clarification-provider.md`。

## 必查项

| 检查项 | 要回答的问题 |
|---|---|
| Goal | 目标行为是否清楚？ |
| Core behavior | 核心系统行为是否清楚？ |
| API semantics | 是否能在不猜测的情况下写出 API Contract？ |
| Acceptance | 是否能定义 acceptance criteria？ |
| Critical ambiguity | 是否存在两个以上合理解释，并会导致不同实现？ |

## 决策规则

以下任意情况成立，返回 `NEED_CLARIFICATION`：

- Goal 不清楚。
- Core behavior 不清楚。
- API semantics 需要猜。
- Acceptance criteria 无法定义。
- 存在 critical ambiguity。
- 需要把“待定细节”或 open questions 放进 Alignment View 才能继续。

只有所有必查项都通过，才返回 `READY_FOR_SPEC`。

返回 `NEED_CLARIFICATION` 时，不能继续生成 Alignment View。下一步只能是 Clarification Provider。

## 输出形状

```yaml
requirement_assessment:
  decision: NEED_CLARIFICATION
  checks:
    goal_clear: true
    core_behavior_clear: false
    api_semantics_sufficient: false
    acceptance_criteria_definable: false
    critical_ambiguity_exists: true
  missing_information:
    - "需要定义 dummy input 和 output semantics。"
  next: "Clarification Provider"
```
