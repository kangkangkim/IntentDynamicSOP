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
07-lane-fast.md
08-lane-lite-new-capability.md
09-lane-anti-fast-one-liner.md
10-lane-complex-hard-trigger.md
11-lane-api-contract-change.md
12-lane-fast-production-bugfix.md
13-lane-lite-multi-file.md
14-lane-complex-concurrency.md
15-lane-complex-critical-ambiguity.md
16-lane-lite-scope-unknown.md
17-lane-upgrade-lite-to-complex.md
```

07–17 是 Lane 判定探针组,以 `demo-project/`(demo 货币校验任务的运行产物)
为对象;本地没有 demo-project 时,先跑一遍该 demo 任务,或把 prompt 里的
路径换成仓库现有代码。03 同时兼作 D3A Lane bypass(not_applicable)的观察入口。
12 需要先按场景卡里的说明人为制造一个回归,再粘贴 prompt;
17 需要两次粘贴(初始 prompt + 追问时的补充事实)。

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
- 注释/文档类微改动可以 fast，但 10 项 Fast 条件必须逐项显式成立，且仍执行 basic verification。
- 新能力或新测试至少 lite，并闭合 RED/GREEN + coverage 证据或豁免。
- "一行"改动只要改变行为契约，就不能进 fast（unknown 信号不算否定条件）。
- 命中 hard trigger（跨模块、多测试域、API 语义变化等）必须 complex，不因改动小降级。
- 极小 production 回归修复可以 fast，前提是现有测试已覆盖该行为（恢复契约 ≠ 变更契约）。
- 多文件改动即使机械、零行为变化，也至少 lite；但"新建内部模块"不等于跨模块影响。
- 并发/性能/安全类要求是 hard trigger，行为不变、改动小也不能降级。
- 需求自相矛盾时必须 complex + AskUserQuestion 澄清，不允许自行选边；消歧后按新事实重判 lane。
- 影响范围 unknown 直接取消 fast 资格，先探索盘点收敛 scope 再锁定改动。
- lane 可随对齐阶段的新事实重判（升级或降级），重判必须输出新的 lane_decision 且两次留痕。
