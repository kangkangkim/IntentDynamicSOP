# Escalation View

这是自动闭环无法继续时给用户看的异常回流卡片。

异常回流需要用户决策时必须通过 `AskUserTool` 发出；本文件只定义用户可读展示，不是直接决策通道。

背后的机器契约是：

```text
schemas/escalation-policy.schema.yaml
```

## 模板

```text
## 需要你重新确认

### 1. 当前状态

自动闭环在这里停住：

<workflow stage>

### 2. 触发原因

Escalation trigger：

<trigger>

说明：

<reason>

### 3. 已尝试

- <attempt 1>
- <attempt 2>

### 4. 需要你决定

请选择一种：

1. 修改 scope。
2. 修改 contract。
3. 允许重新规划。
4. 停止任务。

### 5. 当前 evidence

- <evidence summary> ref: <evidence_ref>
```

## 规则

- 只有命中 Escalation Policy 才展示。
- 不把技术日志全文塞给用户。
- 必须说明为什么不能继续自动闭环。
- 用户确认后，回到 Human Alignment 或 Planner。
- scope / contract / re-plan / stop 的选择必须通过 `AskUserTool` 收集；如果不可用，返回 `BLOCKED_NEEDS_ASK_USER_TOOL`。
