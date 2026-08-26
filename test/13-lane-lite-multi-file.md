# Scenario 13: Lane = lite(多文件 lite floor,改动机械且零风险)

## 目的

体验 `multi_file_or_multi_component_change` lite floor:一次改动机械、行为
零变化、无需新增测试,但涉及两个文件(新建 constants.py + 修改
currency_validator.py),`localized_change` 不成立,不能进 fast。同时观察
"新建一个内部模块"不应被拔高成 `cross_module_or_layer_impact`
(该 hard trigger 指跨模块行为/契约影响,不是文件数大于一)。

前置:`demo-project/` 已存在;现有测试只 `from currency_validator import
is_valid_currency`,不直接引用内部常量。

## Prompt to paste

```text
用 idc-workflow 处理这个 general coding 需求：

把 demo-project/currency_validator.py 里的 _VALID_CURRENCY_CODES 常量
抽到新建的 demo-project/constants.py，currency_validator.py 改为从
constants 导入该常量。纯结构调整：不改任何行为、不改函数签名、
不改测试文件。
验收：现有 test_currency_validator.py 的 11 个用例原样全绿；
is_valid_currency 行为与改动前完全一致。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: lite floor（multi_file_or_multi_component_change）
     no hard trigger（新内部模块 ≠ cross_module_or_layer_impact）
  -> selected_lane = lite
  -> Contract Gate -> Human Alignment -> lite 闭环
```

## Should see

- lane_decision 的 `fast_disqualified_by` 含多文件信号:改动横跨
  constants.py(新建)与 currency_validator.py(修改),`localized_change` 不成立。
- `no_new_test_required` 成立(纯结构移动,现有测试已覆盖行为),但这只挡掉
  一个 lite floor 信号,挡不掉 multi_file 信号——Fast 仍被取消资格。
- 不升 complex:无行为/契约影响、无多测试域、无 API 变化,reasons 应说明
  为什么 cross_module_or_layer_impact 不成立。
- lite 闭环照常:contract、basic verification(跑现有 11 用例)、completion gate。

## Should not happen

- 不应该因为"改动机械、零风险、就几行"放行 fast(lite floor 是下限,不看难度)。
- 不应该因为"新建了一个模块"就升 complex(把文件数当成跨模块影响)。
- 不应该顺手改行为、改函数签名或动测试文件。
- 不应该在结构移动后不跑现有验证就声称完成。
