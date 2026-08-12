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

## Provider

V0 支持两个 provider：

```text
builtin-critical-questions
external-grill-me
```

### builtin-critical-questions

默认 provider。

它不依赖外部服务，保密区内也必须可用。

它只能基于当前 request、repo context summary、contract gap 和 completion gate gap 提问。

### external-grill-me

可选增强 provider。

它代表外部知名 Grill Me 能力的适配点。

外部 provider 只能输出澄清问题和原因，不能直接：

- 决定 Domain / Lane。
- 修改 scope。
- 修改 contract。
- 写代码。
- 判断 DONE。

如果环境没有安装或不允许使用外部 provider，必须自动降级到 `builtin-critical-questions`。

## 问题预算

一次 clarification 最多问 5 个问题。

优先级：

1. 会导致不同实现路径的问题。
2. 会影响 API Contract 的问题。
3. 会影响 completion gate 的问题。
4. 会影响 test evidence 的问题。
5. 会影响 scope boundary 的问题。

## 输出形状

```yaml
clarification_provider:
  selected_provider: builtin-critical-questions | external-grill-me
  fallback_used: false
  reason: "<why this provider was selected>"
  questions:
    - id: Q1
      priority: critical
      question: "<question>"
      blocks:
        - api_contract
        - completion_gate
      why_needed: "<why this must be answered before alignment>"
```

## 规则

- 不问“好不好”“你怎么看”这类无约束问题。
- 不把完整 YAML 展示给用户。
- 不要求用户 approve；clarification 完成后才进入 Alignment View。
- 不把外部 provider 的回答当作 evidence。
- 外部 provider 失败时不能阻塞 workflow，必须 fallback。
