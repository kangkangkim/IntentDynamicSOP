# Clarification Provider

Clarification Provider 负责在 Human Alignment 之前生成关键澄清问题。

它只解决一个问题：

```text
当前任务是否还缺少进入 contract / scope / completion gate 的关键信息？
```

## 位置

```text
Requirement Assessor
  -> NEED_CLARIFICATION
  -> Clarification Provider
  -> Clarification View
  -> 用户回答
  -> 更新 normalized_request / contracts
  -> Requirement Assessor
```

## Inspiration

本 workflow 吸收 `mattpocock/skills` 项目中 `grill-me` / `grill-with-docs` 的公开方法论。

详见：

```text
docs/source-attribution.md
```

吸收的是方法论，不是逐字复制原始 prompt。

## Provider

V0 支持三个 provider mode：

```text
builtin-critical-questions
grill-me-method
grill-with-docs-method
```

### builtin-critical-questions

默认 fallback provider。

它不依赖外部服务，保密区内也必须可用。

它只能基于当前 request、repo context summary、contract gap 和 completion gate gap 提问。

### grill-me-method

默认推荐 provider。

它吸收公开 Grill Me 的提问方式：

- relentless interview：持续追问，直到需求能被明确承诺。
- decision tree：先分叉关键决策，再沿选中分支追问。
- frontier round：每一轮只问当前前置条件已经满足的问题。
- commitment check：每轮结束判断是否已经能生成 Alignment View。
- no implementation during grilling：澄清阶段不写代码。

### grill-with-docs-method

可选 docs mode。

当澄清结果需要沉淀为团队知识时使用。

Use the project skill:

```text
.claude/skills/idc-intent-grilling-with-docs/SKILL.md
.claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md
```

它可以产出非敏感的决策记录草案，例如：

```text
docs/decision-records/<placeholder>.md
```

在外部环境只能写 placeholder 级文档；进入保密区后才能填真实内部细节。

## Provider 边界

Clarification Provider 只能输出澄清问题、阻塞原因和回答后的更新建议，不能直接：

- 决定 Domain / Lane。
- 修改 scope。
- 修改 contract。
- 写代码。
- 判断 DONE。

如果 `grill-me-method` 或 `grill-with-docs-method` 所需上下文不足，必须自动降级到 `builtin-critical-questions`。

## Grilling Loop

```text
Build decision tree
  -> Select current frontier
  -> Ask multiple-choice question cards
  -> User answers
  -> Update assumptions and blockers
  -> Commitment check
  -> READY_FOR_ALIGNMENT / NEXT_FRONTIER / ESCALATE
```

## 问题预算

一次 frontier round 最多问 5 个问题。

Grill Me 阶段默认不输出长篇开放式追问。每个问题必须是一个可选择的问题卡：

- 每题提供 2-4 个互斥选项。
- 如果存在安全默认值，必须标出推荐选项。
- 选项文案要短，用户可以直接复制编号或选项名回答。
- 只有当选项无法覆盖真实决策时，才在选项后追加 `其他 / 补充说明`。
- 不把多个独立决策塞进同一道题。

优先级：

1. 会导致不同实现路径的问题。
2. 会影响 API Contract 的问题。
3. 会影响 completion gate 的问题。
4. 会影响 test evidence 的问题。
5. 会影响 scope boundary 的问题。

## 输出形状

```yaml
clarification_provider:
  selected_provider: builtin-critical-questions | grill-me-method | grill-with-docs-method
  fallback_used: false
  reason: "<why this provider was selected>"
  decision_tree:
    root_decision: "<main uncertainty>"
    settled:
      - "<settled decision>"
    open_frontier:
      - "<current unresolved decision>"
  questions:
    - id: Q1
      priority: critical
      question: "<question>"
      answer_style: multiple_choice
      options:
        - id: A
          label: "<short option>"
          recommended: true
          effect: "<what this choice changes>"
        - id: B
          label: "<short option>"
          recommended: false
          effect: "<what this choice changes>"
      blocks:
        - api_contract
        - completion_gate
      why_needed: "<why this must be answered before alignment>"
  commitment_check:
    status: READY_FOR_ALIGNMENT | NEXT_FRONTIER | ESCALATE
    reason: "<why>"
```

## 规则

- 不问“好不好”“你怎么看”这类无约束问题。
- 不用长篇文章式追问用户；默认使用选择题问题卡。
- 能用 2-4 个具体选项覆盖的决策，不允许改成开放题。
- 不把完整 YAML 展示给用户。
- 不要求用户 approve；clarification 完成后才进入 Alignment View。
- 不把 clarification 回答当作 DONE evidence。
- 每轮必须说明这些问题为什么阻塞 contract、scope 或 completion gate。
- 用户用中文输入时，澄清问题必须用中文。
- docs mode 只能写非敏感 placeholder 文档。
