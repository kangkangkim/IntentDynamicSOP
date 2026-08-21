# Scenario 15: Lane = complex(hard trigger:critical_ambiguity,需求自相矛盾)

## 目的

体验 `critical_ambiguity` hard trigger:需求内部自相矛盾(同一函数既要求
抛异常又要求不抛异常),无法确定行为契约,必须 `complex`,且矛盾必须显式
抛回给用户澄清,不允许 resolver 自行选一边实现。澄清后 lane 应基于新事实
重新判定(很可能降回 lite),两次判定都留痕。

前置:`demo-project/` 已存在。

## Prompt to paste

```text
用 idc-workflow 处理这个 general coding 需求：

在 demo-project 新增 normalize_currency(code)：
- 输入支持的货币码，返回规范大写形式，如 "usd" -> "USD"。
- 输入不支持的代码时抛 ValueError。
- 同时该函数必须对任何输入都不抛异常，统一返回 None。
- 加配套测试，现有 11 个用例保持通过。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: hard trigger（critical_ambiguity:抛异常与不抛异常并存）
  -> selected_lane = complex
  -> Contract Gate: 矛盾未消 -> AskUserQuestion 澄清
  -> 消歧后 lane re-evaluation（预期降回 lite: new_capability）
  -> Human Alignment -> 闭环
```

## Should see

- lane_decision 把 critical_ambiguity 列为 hard trigger,事实来源直接引用
  需求里互相矛盾的两句原文。
- 矛盾通过 AskUserQuestion 抛给用户,给出可选项(如"抛异常"/"返回 None"/
  "分层:严格版+宽松版"),不是普通文本追问,更不是自行消歧。
- 用户澄清后输出新的 lane_decision:预计降回 lite(new_capability +
  new_or_changed_test_required 的 lite floor),且 reasons 说明降级依据。
- 两次 lane 判定都可追溯(旧判定保留,新判定注明触发重评的事实)。
- 消歧结果写入 contract 后才进入实现。

## Should not happen

- 不应该 silently 选一边(比如默认抛异常)就开始实现。
- 不应该把矛盾当成"留给实现者自己判断"的实现细节。
- 不应该用普通文本追问用户(规则 12:一律走 AskUserQuestion)。
- 澄清后不应该沿用旧的 complex 理由或旧 lane 继续跑。
- 不应该在矛盾未消时产出 API Contract。
