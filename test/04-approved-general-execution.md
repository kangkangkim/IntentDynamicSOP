# Scenario 04: Approved General Execution

## 目的

体验用户明确 approval 后，是否进入 automated closure loop，并通过 Delegation Contract 分派 General subagent。

## Prompt to paste

```text
我 approve 下面这个 Alignment Pack，请继续自动闭环：

Domain: general
Lane: lite
Task contract:
- 创建一个 mock 脚本说明文件，不触碰真实业务代码。
- 文件路径只能在 examples/e2e-general-task/ 下。
Verification contract:
- 需要一个 placeholder RED evidence。
- 需要一个 placeholder GREEN evidence。
- 需要 completion summary。
Scope:
- in scope: examples/e2e-general-task/
- out of scope: .claude/skills/id-workflow/references/domains/d3a/
```

## Expected route

```text
id-workflow
  -> human_alignment_status = approved
  -> IDC Workflow Router selects general_execution
  -> Delegation Router
  -> Delegation Contract
  -> subagent: general-coder
  -> Verification
  -> Completion View
```

## Should see

- Plan / context loaded / execution units / evidence。
- General subagent 或 General Coding route。
- evidence refs，而不是模型自信。

## Should not happen

- 不应该使用 D3A Layer / DT Domain。
- 不应该修改 out-of-scope 路径。
- 不应该单个 execution unit 超过 500 LOC。

