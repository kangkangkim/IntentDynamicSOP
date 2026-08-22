# Scenario 12: Lane = fast(极小 production bugfix / 回归修复)

## 目的

体验 `small_production_change_can_be_fast` 规则:production code 的修改不是
一律禁 fast。修复一个被现有测试完整覆盖的极小回归,行为契约(以 docstring
和现有测试为准)没有变化,无需新增测试,现有验证足以闭环,应判 `fast`。
核心观察点是 Lane Resolver 能否区分"变更契约"与"恢复契约"。

前置:
1. `demo-project/` 已存在。
2. 先人为制造一个回归——把 `demo-project/currency_validator.py` 中的

   ```python
   return code.upper() in _VALID_CURRENCY_CODES
   ```

   改成

   ```python
   return code.upper().strip() in _VALID_CURRENCY_CODES
   ```

   改完后现有测试中"带空白输入返回 False"的用例会变红。然后再粘贴下面的 prompt。

## Prompt to paste

```text
用 idc-workflow 处理这个需求：

修复 demo-project/currency_validator.py 当前的回归：带空白的输入
（如 " usd "）被错误地接受了，恢复原有行为（与模块 docstring 和
现有测试一致）。只修复这一处行为，不改测试、不新增测试。
验收：现有 demo-project/test_currency_validator.py 的 11 个用例全绿。
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

- lane_decision 把本次改动定性为"恢复既有契约"而不是 behavior_contract_change:
  行为契约以 docstring 与现有测试为准,是实现对契约的偏离被纠正。
- `no_new_test_required` 的理由是"现有测试已完整覆盖该行为"(回归用例已存在),
  不是"用户没要求测试"。
- `existing_verification_available` 落实为执行现有 11 个用例(修复前对应用例
  RED、修复后 GREEN),basic verification 有 evidence。
- `fast_scope_evidence_present` 引用明确的 diff anchor(单行 `strip()` 移除)。
- 逐项列出 fast_required_conditions 且每项为 true、可追溯。

## Should not happen

- 不应该因为"改的是 production code"就一律禁 fast、抬到 lite。
- 不应该反向误判:把回归修复当成 behavior_contract_change 抬到 lite
  (若出现,记录为 resolver 把"恢复契约"与"变更契约"混淆)。
- 不应该在修复前不先跑测试确认 RED、修复后不跑测试声称完成。
- 不应该顺手重构、改测试或加新测试。
- 不应该使用 D3A Layer / DT Domain registry。
