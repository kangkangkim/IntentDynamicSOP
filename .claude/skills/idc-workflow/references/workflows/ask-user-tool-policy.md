# AskUserTool Policy

IDC 所有面向用户的问题都必须通过 `AskUserTool` 发出。

这个 policy 覆盖 Discovery、Clarification、Human Alignment、Re-alignment、Resume 和 Escalation。Human View 可以负责展示结构和摘要，但真正需要用户回答的 prompt、选项、approval 或决策必须进入 `AskUserTool`。

## 触发

必须调用 `AskUserTool` 的情况：

- Discovery Provider 需要用户补充 raw idea、选择方向或确认 draft direction。
- Clarification Provider 生成 Grill Me / Grill With Docs / builtin critical question cards。
- Human Alignment 请求 approve、request clarification、request reclassify 或 reject。
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

## 规则

- 不允许把问题只写在普通 prose 里等用户自由回复。
- 不允许在 final prose 里请求 approval；approval 必须是 `AskUserTool` 事件。
- 不允许把 `AskUserTool` 的问题埋进完整 YAML 给用户看。
- Human View 的问题卡是展示模板，`AskUserTool` 是交互出口。
- 如果当前环境没有可用的 `AskUserTool`，返回 `BLOCKED_NEEDS_ASK_USER_TOOL`，不要继续伪造用户确认。
