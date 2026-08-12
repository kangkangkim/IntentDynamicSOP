# Discovery Provider

Discovery Provider 负责把 `raw_idea` 输入展开成可以被 Grill Me 收敛的设计草案。

它发生在 Clarification Provider 之前。

```text
Input Adapter
  -> Intent Maturity Router
  -> raw_idea
  -> Discovery Provider
  -> Draft Requirement / Draft Spec
  -> Clarification Provider
  -> Alignment View
```

## Inspiration

本 workflow 吸收 `obra/superpowers` 项目中 `brainstorming` skill 的公开方法论。

详见：

```text
docs/source-attribution.md
```

吸收的是方法论，不是逐字复制原始 skill prompt。

## Provider

V0 支持两个 provider mode：

```text
brainstorming-method
builtin-discovery-questions
```

### brainstorming-method

默认推荐 provider，用于一句话需求或模糊想法。

吸收点：

- 先理解项目上下文，再追问。
- 一次只问一个真正关键的问题。
- 必要时给 2-3 个方案，并说明 trade-off 和推荐。
- 先形成 design / draft spec，再交给用户确认。
- 在 design 被确认前，不进入实现。

### builtin-discovery-questions

默认 fallback provider。

它不依赖外部服务，保密区内也必须可用。

它只做最小展开：

- 目标用户或调用方。
- 期望行为。
- 不做什么。
- 验收信号。
- 已知约束。

## 适用输入

```text
raw_idea:
  - 一句话需求。
  - 目标词很多，但没有行为语义。
  - 没有明确验收标准。
  - 没有 API / 数据 / 测试线索。

structured_requirement:
  - 有目标和主要行为。
  - 可能缺少边界或验收。
  - 通常跳过 Discovery，直接进入 Clarification Provider。

tr3_design_doc:
  - 已有设计、DT、验收或影响范围。
  - 跳过 Discovery，直接进入 TR3 Adapter 和 Clarification Provider。
```

## Discovery Loop

```text
Explore lightweight project context
  -> Ask one key question
  -> Update idea model
  -> Offer 2-3 approaches if design branch exists
  -> Draft spec
  -> User confirms draft direction
  -> Clarification Provider
```

## 输出形状

```yaml
discovery_provider:
  selected_provider: brainstorming-method | builtin-discovery-questions
  fallback_used: false
  input_maturity: raw_idea
  context_refs:
    - "<repo/docs evidence ref>"
  questions_asked:
    - id: DQ1
      question: "<question>"
      answer_summary: "<summary>"
  approaches:
    - id: A
      summary: "<approach>"
      tradeoff: "<tradeoff>"
      recommendation: true
  draft_spec:
    goal: "<goal>"
    users_or_callers: "<who>"
    core_behavior: "<behavior>"
    out_of_scope:
      - "<boundary>"
    acceptance_signals:
      - "<signal>"
  next: Clarification Provider
```

## 规则

- 只在 `raw_idea` 场景默认启用。
- TR3 输入默认跳过 Discovery。
- 不在 Discovery 阶段写实现代码。
- 不把 draft spec 当作 approved contract。
- 用户用中文输入时，Discovery 问题和方案必须用中文。
- 外部环境只能生成非敏感 draft spec。
