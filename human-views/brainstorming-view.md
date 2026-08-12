# Brainstorming View

这是给一句话需求或模糊想法看的发散设计卡片。

背后的机器契约是：

```text
schemas/discovery-provider.schema.yaml
```

## 模板

```text
## 先把想法展开一下

你现在给的是 raw idea，我会先帮你把它变成可确认的设计草案，再进入 Grill Me 收敛。

### 1. 当前理解

<idea summary>

### 2. 我需要先问清楚

<focused discovery questions>

为什么这些问题重要：

<why this affects design direction>

### 3. 可选方案

方案 A：<summary>
- 取舍：<tradeoff>

方案 B：<summary>
- 取舍：<tradeoff>

推荐：

<recommended approach and reason>

### 4. 设计草案

- 目标：<goal>
- 使用方：<users_or_callers>
- 核心行为：<core_behavior>
- 不做什么：<out_of_scope>
- 验收信号：<acceptance_signals>

### 5. 下一步

你确认方向后，我会进入 Grill Me，把 contract、scope 和 completion gate 烤清楚。
```

## 规则

- 只在 raw idea 场景默认展示。
- TR3 文档默认不展示 Brainstorming View。
- 根据问题复杂度成组追问，不用 token 限制牺牲需求探索质量。
- 如果存在多个合理设计方向，展示 2-3 个方案和推荐。
- 用户确认设计方向前，不能写实现代码。
- Brainstorming 生成的是 draft spec，不是 approved contract。
