# Scenario 07: Lane = fast(注释类微改动)

## 目的

体验一个真正满足全部 Fast 准入条件的任务:范围极小、不改行为、无需新增测试、
现有验证足以闭环,观察 Lane Resolver 是否逐项给出事实依据后选择 `fast`,
并且 Fast 仍然执行 basic verification(不是"不验证")。

前置:`demo-project/`(货币代码校验 demo 的运行产物)已存在;
不存在时先跑一遍该 demo 任务,或把 prompt 中的路径换成仓库现有代码。

## Prompt to paste

```text
用 idc-workflow 处理这个需求：

给 demo-project/currency_validator.py 的模块 docstring 补充一段使用示例注释
（展示 is_valid_currency("usd") 与 is_valid_currency("XXX") 两个调用的返回值）。
只改 docstring 注释，不改任何代码行、不改任何测试。
验收：现有 demo-project/test_currency_validator.py 的 11 个用例原样全部通过。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: no complex hard trigger, no lite floor signal
  -> fast（10 项 fast_required_conditions 全部显式 true）
  -> Contract Gate -> Human Alignment -> fast 闭环
```

## Should see

- lane_decision 逐项列出 fast_required_conditions 且每项为 true、可追溯。
- `no_new_test_required` 有明确理由(注释/文档类修改,现有测试已覆盖该模块)。
- `fast_scope_evidence_present` 引用明确文件(demo-project/currency_validator.py 的 docstring)。
- `existing_verification_available` 落实为执行现有 11 个单测,basic verification 有 evidence。
- capability selection 仍生成 per-EU 文件(`.idc/capability-selection-<task>-<execution-unit>.yaml`)。
- Fast 不受 coverage 闸门约束(lane-completion 的 coverage 条款只约束 test-based verification 的 lite/complex)。

## Should not happen

- 不应该因为"需求很短、改动只有几行"就直接 fast——必须逐项条件成立。
- 不应该悄悄改到代码行或测试文件。
- 不应该跳过验证(Fast 是小闭环,不是零闭环)。
- 不应该要求 TDD RED evidence(Fast 无强制 TDD)。
- 不应该使用 D3A Layer / DT Domain registry。
