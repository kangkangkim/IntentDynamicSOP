# Scenario 11: Lane = complex(hard trigger:api_semantic_change,改动极小也升级)

## 目的

体验"改动大小"与"执行强度"解耦:核心改动可能只有几行,但 API 返回值语义
变化是 Complex hard trigger,必须 `complex`,并观察调用方与测试的同步调整被
纳入计划而不是事后补救。

前置:`demo-project/` 已存在。

## Prompt to paste

```text
用 idc-workflow 处理这个 general coding 需求：

把 demo-project 里 is_valid_currency 的返回值从 bool 改为
{"valid": bool, "reason": str}：合法时 reason 为空串，
非法时 reason 给出原因（未知代码 / 长度不对 / 格式非法）。
调用方和全部现有测试同步调整。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: hard trigger（api_semantic_change）
  -> selected_lane = complex（decision_rule = hard_trigger）
  -> Contract Gate -> Human Alignment -> complex 闭环
```

## Should see

- lane_decision 把返回值语义变化标注为 api_semantic_change(带事实来源:
  函数签名契约、既有调用方、11 个既有断言全部受影响)。
- 计划包含:契约先行(API Contract 更新先于实现)、全部调用方清单、
  测试断言的批量调整方案。
- RED(新契约断言失败)-> GREEN -> coverage 证据。
- complex completion gate 全项闭合(含 audit_or_review)。

## Should not happen

- 不应该因"核心逻辑只改几行"选择 lite 或 fast。
- 不应该先改实现再"顺手"改调用方(契约先行)。
- 不应该遗漏任何现有调用方或断言。
- 不应该把旧 bool 返回值兼容保留却没有显式决策记录。
