# Scenario 08: Lane = lite(新能力 + 新测试)

## 目的

体验 Lite floor 的典型形态:新增能力、必须新增测试代码,但单一模块、
无 Complex hard trigger,观察 Lane Resolver 至少选择 `lite`,并走完整的
RED -> GREEN -> coverage 证据闭环。

前置:`demo-project/` 已存在。

## Prompt to paste

```text
用 idc-workflow 处理这个 general coding 需求：

目标：在 demo-project 新增一个金额校验纯函数 is_valid_amount。
行为：
- 输入金额字符串，合法金额返回 true，非法返回 false。
- 合法：正数，整数或最多两位小数，如 "42"、"0.99"、"123.45"。
- 非法：负数、三位以上小数、空串、非数字，如 "-1"、"1.234"、""、"abc"。
- 风格与现有 currency_validator.py 一致：纯函数、无 IO。
验收：
- 配套 unittest，覆盖上述合法/非法样例。
- 现有 currency_validator 的 11 个用例保持通过。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: lite floor（new_capability + new_or_changed_test_required）
  -> selected_lane = lite
  -> Contract Gate -> Human Alignment -> lite 闭环
```

## Should see

- lane_decision 的 reasons 说明命中 Lite floor 信号(新增能力 / 需新增测试)。
- TDD 状态机生效:先 RED(断言级失败),再 GREEN。
- completion gate 包含 `coverage_evidence_or_exemption`(工具报告 ref 或简化口径数字,或显式豁免+原因)。
- Knowledge Load Plan READY,执行后 receipt 机器校验 VERIFIED。
- capability-selection / knowledge-load-plan 使用 per-EU 文件名。
- repository mutation 经 Execution Authorization + subagent 派发(main agent 不直接写码)。

## Should not happen

- 不应该进 fast(存在新增测试,`no_new_test_required` 不成立)。
- 不应该进 complex(无跨模块、无多测试域、无 API 语义变化等 hard trigger)。
- 不应该在无 RED evidence 的情况下声称 GREEN。
- 不应该在 coverage 证据缺失时标记 DONE。
