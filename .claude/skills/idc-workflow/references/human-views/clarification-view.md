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

- Provider：<builtin-critical-questions / grill-me-method / grill-with-docs-method>
- Fallback：<yes / no>

### 2. 当前决策树

- Root Decision：<main uncertainty>
- 已确定：<settled decisions>
- 当前 Frontier：<questions whose prerequisites are already settled>

### 3. 关键问题

1. <question>
   - A. <option label>（推荐，若适用）
   - B. <option label>
   - C. <option label>
   - 其他 / 补充说明：<optional>
   - 阻塞：<api_contract / scope_boundary / completion_gate / verification_contract>
   - 原因：<why_needed>

2. <question>
   - A. <option label>
   - B. <option label>
   - 阻塞：<...>
   - 原因：<...>

### 4. 本轮承诺度判断

- Status：<READY_FOR_ALIGNMENT / NEXT_FRONTIER / ESCALATE>
- 原因：<reason>

### 5. 回答后会发生什么

我会根据你的回答更新任务理解和契约草案，然后重新生成 Alignment View 给你确认。
```

## 规则

- 不展示完整 YAML。
- 每轮最多展示 5 个关键问题。
- 每个关键问题默认必须是选择题问题卡，提供 2-4 个互斥选项。
- 只有选项覆盖不了时，才允许追加“其他 / 补充说明”。
- 不输出长篇文章式追问。
- 只问会阻塞 contract、scope 或 completion gate 的问题。
- 使用 Grill Me 方法时，必须按 decision tree / frontier round 组织问题。
- 如果 Grill Me 方法不可用，必须说明已 fallback 到 builtin-critical-questions。
- 用户回答后不能直接写代码，必须先回到 Alignment View。
