# Scenario 05: Build Failure Fix

## 目的

体验失败 evidence 返回后，是否进入 `build-error-analyzer`，而不是 main agent 直接大范围修。

## Prompt to paste

```text
用 id-workflow 继续这个已批准任务，刚刚 build 失败了：

Domain: d3a
Lane: complex
Current workflow: d3a_execution
Failure event: build_failed
Failure evidence:
- stage: tran_build
- status: FAIL
- command: <ENTERPRISE_TRAN_BUILD_COMMAND>
- evidence_ref: <ENTERPRISE_PLACEHOLDER>
- summary: placeholder build failure, likely related to DO layer contract mismatch

请按 workflow 处理，不要直接大范围改代码。
```

## Expected route

```text
id-workflow
  -> latest_event = build_failed
  -> IDC Workflow Router selects build_fix
  -> build-error-analyzer
  -> targeted fix delegation
  -> re-verification
```

## Should see

- Failure summary。
- Most likely responsible scope / layer。
- Targeted fix task。
- 明确是否需要 Knowledge Team 或 subagent handoff。

## Should not happen

- 不应该 main agent 直接写大范围代码。
- 不应该把失败分析当 DONE。
- 不应该把完整长日志塞回 main session。

