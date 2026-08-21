# Scenario 17: Lane 动态重判:lite -> complex(对齐阶段揭示新事实)

## 目的

体验 lane 不是一次定终身:初始信息下判 `lite`,在 Human Alignment /
追问阶段用户揭示新事实(多个测试域 + 面向用户的输出契约),触发 hard
trigger,必须重新输出 lane_decision 升级为 `complex`,两次判定都留痕、
理由可追溯。这是唯一测"lane 随事实重评"的探针。

前置:`demo-project/` 已存在。
本场景需要两次粘贴:第一次是初始 prompt,当被 AskUserQuestion 问到影响面
或验收细节时,按剧本补答;若没有触发追问,主动粘贴补充 prompt。

## Prompt to paste(第一次)

```text
用 idc-workflow 处理这个需求：

给 demo-project 的货币校验失败加一个中文原因函数
invalid_currency_reason(code)：非法输入返回中文原因字符串
（如"不支持的货币代码：XYZ"），合法输入返回空串。
```

## 被追问时按剧本补答(或直接粘贴第二次)

```text
补充两个关键事实：
1. 这个原因字符串是直接给终端用户看的，会作为 CLI 的 stderr 输出，
   不同失败类型（非字符串/空串/不支持的代码）要有可区分的文案，
   文案本身就是对外契约。
2. 测试要分两个域：单元测试（函数本身）+ CLI 行为测试
   （stderr 文案与退出码），两个域都要新增用例。
```

## Expected route

```text
id-workflow
  -> 初始 lane_decision = lite（lite floor: new_capability + 新测试）
  -> Human Alignment / 追问 -> 用户揭示: 对外文案契约 + 两个测试域
  -> lane re-evaluation: hard trigger
     （api_semantic_change[面向用户契约] + multiple_test_domains）
  -> selected_lane = complex（新 lane_decision,注明重评依据）
  -> complex 闭环
```

## Should see

- 第一次 lane_decision = lite,reasons 基于当时已知事实(新函数、需新测试)。
- 补充事实到达后产生新的 lane_decision:decision_rule = hard_trigger,
  并引用用户补充的原文作为事实来源;旧判定保留可追溯。
- complex required_outputs 补齐:full_task_contract(含文案契约)、
  dependency_dag、evidence_plan(两个测试域)、subagent_split、audit。
- 升级后 execution 结构随之变化(测试域拆分),不是沿用 lite 的执行计划。

## Should not happen

- 不应该沿用初始 lite 判定继续跑("lane 已经定过了"不是理由)。
- 不应该把升级当成口头说明而不输出新的 lane_decision 记录。
- 不应该在用户尚未补充时预判 complex(信息没到就不算命中)。
- 不应该把"文案"当成无关紧要的实现细节而不纳入契约。
- 追问应该走 AskUserQuestion,不是普通文本。
