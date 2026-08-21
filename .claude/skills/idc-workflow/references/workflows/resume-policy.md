# Resume Policy

Resume Policy 负责让接入团队配置后中断的任务能接上。

核心原则：

```text
不靠会话记忆恢复
只靠 checkpoint / contract / evidence ref 恢复
恢复后先判断状态，再决定继续、重验或升级
```

## 何时使用

当用户说：

- “继续上次任务”。
- “中断了，接着跑”。
- “从之前 checkpoint 恢复”。
- 团队配置内会话、subagent、official dynamic workflow 中断后重新进入。

必须先读取：

```text
references/schemas/runtime-state.schema.yaml
references/schemas/delegation-contract.schema.yaml
references/workflows/delegation-router.md
references/workflows/automated-closure-loop.md
```

## Checkpoint 写入时机

每个阶段结束后都要更新 runtime state：

```text
Input normalized
Discovery completed
Clarification completed
Alignment approved
Plan created
Delegation Contract created
Subagent / Agent Team dispatched
Agent result returned
Verification evidence recorded
Fix loop entered
DONE / escalated
```

阶段中断时，写入：

```text
latest_event: interrupted
current_state: <last known stable state>
in_progress_step: <interrupted step>
```

## 恢复流程

```text
Load runtime_state
  -> Validate checkpoint refs exist
  -> Reload approved_alignment_ref if approved
  -> Reload delegation_contract_ref if execution started
  -> Reload context_packet_ref for the current execution unit
  -> Re-run IDC Workflow Router with latest_event = resumed
  -> Decide continue / re-verify / re-plan / align / escalate
```

## 状态恢复规则

| current_state | 恢复动作 |
|---|---|
| `discovery` | 重放 Brainstorming View 摘要，继续 `intent-grilling` 或通过 `AskUserTool` 重新问用户。 |
| `clarification` | 重新展示未回答的 Clarification View 选择题卡，并通过 `AskUserTool` 收集回答。 |
| `alignment` | 重新展示 Alignment View，通过 `AskUserTool` 等待 approve。 |
| `planning` | 重新生成或校验 plan；不直接执行。 |
| `execution` | 读取 delegation/context packet；如果无法证明 subagent 完成，重新派发或进入 verification。 |
| `verification` | 重新运行 verification；不复用模型记忆判断 GREEN。 |
| `fix` | 读取 last_failure_ref 和 retry_count，进入 targeted fix 或 escalation。 |
| `done` | 只展示 completion summary 和 evidence refs，不重复执行。 |
| `escalated` | 展示 Escalation View，通过 `AskUserTool` 等待人工处理。 |

## Official Dynamic Workflow

如果 `official_dynamic_workflow.required = true`：

- 优先使用官方 workflow run id 恢复，例如 `resumeFromRunId`。
- 如果 run id 不可用，用 `runtime_state.workflow_snapshot` 和 workflow args 的 `baseline` 重新跑。
- 大规模 fan-out 的中间结果必须在 Collect barrier 后写入 runtime state 或 baseline。
- 恢复后不能重复提交已完成的文件变更；必须先 diff / verify。

## 不允许

- 不允许凭 main agent 记忆说“刚才做到哪了”。
- 不允许把 provider finding 当作完成证据。
- 不允许跳过 Human Alignment approval。
- 不允许在 execution 中断后直接标 DONE。
- 不允许 checkpoint 缺失时猜测执行结果。
- 不允许用普通文本询问恢复、approval 或 escalation 决策；必须使用 `AskUserTool`，不可用时返回 `BLOCKED_NEEDS_ASK_USER_TOOL`。

## 恢复输出

恢复时先给用户一个短的 Resume View：

```text
## 恢复任务

- Run：<run_id>
- 当前状态：<current_state>
- 上次稳定 checkpoint：<checkpoint_ref>
- 已有证据：<evidence_refs summary>
- 下一步：<continue / re-verify / re-plan / alignment / escalate>
```

Resume View 是状态摘要，不是 approval，也不是 DONE evidence。
