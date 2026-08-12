# Clarification View

这是给用户看的关键澄清卡片。

背后的机器契约是：

```text
schemas/clarification-provider.schema.yaml
```

## 模板

```text
## 需要先问清楚

我现在还不能直接进入对齐确认，因为下面信息会影响 contract、scope 或 completion gate。

### 1. 澄清来源

- Provider：<builtin-critical-questions / external-grill-me>
- Fallback：<yes / no>

### 2. 关键问题

1. <question>
   - 阻塞：<api_contract / scope_boundary / completion_gate / verification_contract>
   - 原因：<why_needed>

2. <question>
   - 阻塞：<...>
   - 原因：<...>

### 3. 回答后会发生什么

我会根据你的回答更新任务理解和契约草案，然后重新生成 Alignment View 给你确认。
```

## 规则

- 不展示完整 YAML。
- 最多展示 5 个关键问题。
- 只问会阻塞 contract、scope 或 completion gate 的问题。
- 如果 external-grill-me 不可用，必须说明已 fallback 到 builtin-critical-questions。
- 用户回答后不能直接写代码，必须先回到 Alignment View。
