# IDC Manual Test Scenarios

这个目录用于手动体验 IDC workflow。

它和 `tests/` 不一样：

- `tests/` 是自动化 harness。
- `test/` 是给人复制到 Claude Code 里体验流程的场景卡。

## 怎么用

在 Claude Code 中打开本仓库，然后把任意场景文件里的 `Prompt to paste` 复制给 Claude。

建议顺序：

```text
01-rough-general.md
02-structured-general.md
03-tr3-d3a.md
04-approved-general-execution.md
05-build-failure-fix.md
06-large-fanout-dynamic-workflow.md
```

## 观察重点

每个场景都看四件事：

```text
1. 入口 skill 是否正确触发。
2. 是否先做 Human Alignment。
3. 是否正确选择 IDC Workflow Router / Official Dynamic Workflow / Agent Team / Subagent。
4. 是否避免未批准就写代码或把 provider finding 当 DONE evidence。
```

## 成功体验标准

- rough / 模糊 general 必须先 Brainstorming。
- 短但结构化的 general 不应该进入 Brainstorming。
- structured general 应该直接 Grill Me / Alignment，不默认 Brainstorming。
- TR3 D3A 默认跳过 Brainstorming，但要做 contract gap check。
- approved 后才进入 execution / subagent。
- failure fix 应该先分析 evidence，再 targeted fix。
- large fan-out 才应该考虑 official dynamic workflow。
