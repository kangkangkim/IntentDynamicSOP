# Discovery Provider

Discovery Provider 负责把 `raw_idea` 输入展开成可以被 Grill Me 收敛的设计草案。

Discovery 阶段所有需要用户回答的问题或方向选择都必须通过 `AskUserTool` 发出，遵守 `workflows/ask-user-tool-policy.md`。

它发生在 Clarification Provider 之前。

若存在有效团队配置，Discovery 可按需读取
`knowledge.feature_docs_root_ref` 和 `knowledge.architecture_doc_ref` 的有界摘要；
这些 refs 只提供背景，不能替代用户决策或批准。

```text
Input Adapter
  -> Intent Maturity Router
  -> raw_idea
  -> Discovery Provider
  -> Draft Requirement / Draft Spec
  -> Clarification Provider
  -> Alignment View
```

## Upstream Baseline

本 workflow 以 `obra/superpowers` 项目中的 `brainstorming` skill 为 upstream baseline。

本仓库已经把方法主体内置在：

```text
.claude/skills/idc-brainstorming/references/superpowers-brainstorming-method.md
```

详见：

```text
docs/source-attribution.md
```

IDC 在 upstream baseline 上做轻量 overlay，而不是另起一套无关流程。

## Provider

V0 支持三个 provider mode：

```text
upstream-superpowers-brainstorming
idc-brainstorming-overlay
builtin-discovery-questions
```

### upstream-superpowers-brainstorming

默认 baseline provider，只用于 `raw_idea` / 模糊想法。

不要因为需求很短就默认 Brainstorming；如果短需求已经包含目标、行为和验收线索，它是 `structured_requirement`，应跳过 Discovery。

保留 upstream 的核心流程：

- 先分 `Spike / Bounded / Architectural` 三条路径。
- 隐藏复杂度只能升级路径，不能中途降级。
- 先理解项目上下文，再追问。
- 使用 focused discovery questions，一次只问一个真正影响设计的 frontier question；不因上下文裁剪牺牲需求探索质量。
- 必要时给 2-3 个方案，并说明 trade-off 和推荐。
- 先形成 path-sized design / draft spec，完成 placeholder、consistency、scope、ambiguity 自检，再交给用户确认。
- 在 design 被确认前，不进入实现。

### idc-brainstorming-overlay

IDC overlay 只做接线和边界微调：

- 只在 `raw_idea` 场景默认启用。
- TR3 默认跳过 Discovery。
- upstream design 输出不直接进入实现，而是进入 `intent-grilling`。
- draft spec 不等于 approved contract。
- 最终人工 gate 仍然是 `intent-alignment` 的 Alignment View。
- 外部环境只能生成公开 draft spec。
- `Spike / Bounded / Architectural` 只表示 Discovery 深度，不是 Lane。
- Discovery 可以补充 `lane_signals`，但不能把 path 直接映射为 `fast / lite / complex`；Domain Module Lane applicability 优先，只有 applicable dynamic-lane route 才由 Lane Resolver 判断。D3A 的 Lane 为 `not_applicable`。

### builtin-discovery-questions

默认 fallback provider。

它不依赖外部服务，团队配置内也必须可用。

它只做最小展开：

- 目标用户或调用方。
- 期望行为。
- 不做什么。
- 验收信号。
- 已知约束。

## 适用输入

```text
raw_idea:
  - 一句话但仍然模糊的需求。
  - 目标词很多，但没有行为语义。
  - 没有明确验收标准。
  - 没有 API / 数据 / 测试线索。

structured_requirement:
  - 有目标和主要行为。
  - 可能缺少边界或验收。
  - 通常跳过 Discovery，直接进入 Clarification Provider。
  - 即使只有一句话，只要目标、行为和验收线索已出现，也不进入 Brainstorming。

tr3_design_doc:
  - 已有设计、DT、验收或影响范围。
  - 跳过 Discovery，直接进入 TR3 Adapter 和 Clarification Provider。
```

## Discovery Loop

```text
Explore lightweight project context
  -> Classify Spike / Bounded / Architectural
  -> AskUserTool one material discovery question at a time
  -> Update idea model
  -> Offer 2-3 approaches if design branch exists
  -> Present path-sized design
  -> Draft spec self-review
  -> User confirms draft direction
  -> Clarification Provider
```

## 输出形状

```yaml
discovery_provider:
  selected_provider: upstream-superpowers-brainstorming | idc-brainstorming-overlay | builtin-discovery-questions
  fallback_used: false
  upstream_baseline: obra/superpowers/skills/brainstorming
  local_method_ref: .claude/skills/idc-brainstorming/references/superpowers-brainstorming-method.md
  overlay: idc-brainstorming-overlay
  input_maturity: raw_idea
  superpowers_path: spike | bounded | architectural
  path_reason: "<reason>"
  observed_lane_signals: []
  lane_decision_deferred: true
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
    alternatives_and_tradeoffs: []
    unresolved_decisions: []
    self_review_result: pass | needs_revision
  next: Clarification Provider
```

## 规则

- 只在 `raw_idea` 场景默认启用。
- TR3 输入默认跳过 Discovery。
- upstream brainstorming 是 baseline，IDC overlay 只做接线和边界微调。
- Superpowers path 不得直接决定 IDC Lane；Discovery 只输出观察到的 lane signals，随后交给固定 module policy 或 Lane Resolver。
- 不在 Discovery 阶段写实现代码。
- 不把 draft spec 当作 approved contract。
- 用户用中文输入时，Discovery 问题和方案必须用中文。
- 外部环境只能生成公开 draft spec。
- 不允许用普通文本直接追问用户；如果 `AskUserTool` 不可用，返回 `BLOCKED_NEEDS_ASK_USER_TOOL`。
