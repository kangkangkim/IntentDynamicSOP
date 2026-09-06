# AskUserTool Policy

IDC 所有面向用户的问题都必须通过 `AskUserTool` 发出。

这个 policy 覆盖 Discovery、Clarification、Human Alignment、Plan Confirmation、Re-alignment、Resume 和 Escalation。Human View 可以负责展示结构和摘要，但真正需要用户回答的 prompt、选项、approval 或决策必须进入 `AskUserTool`。

## 触发

必须调用 `AskUserTool` 的情况：

- Discovery Provider 需要用户补充 raw idea、选择方向或确认 draft direction。
- Clarification Provider 生成 Grill Me / Grill With Docs / builtin critical question cards。
- Human Alignment 请求 approve、request clarification、request reclassify 或 reject。
- Plan Confirmation 请求确认技术方案三件（计划件本体、API Contract、DT 设计）；这是框架 floor，d3a 与全部 lane 都适用。The AskUserQuestion input for plan confirmation must include the plan file path (used by the PreToolUse hook to bind the interaction to the specific plan artifact).
- Resume Policy 需要用户选择从哪个 checkpoint / stage 恢复。
- Escalation View 需要用户决定修改 scope、修改 contract、允许重新规划或停止任务。

## 最小契约

```yaml
ask_user_tool:
  prompt_ref: "<human-view-ref-or-workflow-ref>"
  blocks_execution_until_answered: true
  questions:
    - id: "<stable-question-id>"
      prompt: "<user-facing question>"
      answer_style: multiple_choice | short_text | approval
      options:
        - id: A
          label: "<short option>"
          recommended: true
          effect: "<what this choice changes>"
      blocks:
        - api_contract
        - scope_boundary
        - completion_gate
      why_needed: "<why the workflow cannot continue without this answer>"
```

## 宿主工具名映射

`AskUserTool` 是 harness 层的契约名，不要求宿主工具字面同名。宿主绑定示例：

```text
Claude Code -> AskUserQuestion
CodeAgent -> AskUserQuestion
Codex Plan -> request_user_input
Codex Default -> explicit user text approval + persisted approval record
```

按工具契约语义解析宿主工具：凡是「向用户发出带选项 / approval 语义的交互
提问，并阻塞等待回答」的工具即满足本 policy。只有当宿主确实不存在语义
等价工具时，才返回 `BLOCKED_NEEDS_ASK_USER_TOOL`；不得因为字面名字找不到
而阻塞。

## 规则

- 优先使用宿主提供的结构化确认工具。
- Codex Default 没有结构化确认工具时，允许使用用户明确文本批准。
- 文本批准必须来自真实用户消息，不得由模型自我声明。
- Technical Plan Confirmation 必须引用具体的落盘计划文件。
- 批准结果必须生成 approval record，并绑定 plan hash 和用户消息引用。
- 没有结构化确认、也没有明确文本批准时，返回 `BLOCKED_NEEDS_ASK_USER_TOOL`。
