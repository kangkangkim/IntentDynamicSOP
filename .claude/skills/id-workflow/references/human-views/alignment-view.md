# Alignment View

这是给用户看的前置确认卡片。

背后的机器契约是：

```text
schemas/alignment-pack.schema.yaml
```

## 模板

```text
## 请确认任务对齐

### 1. 任务理解

我理解你要做的是：

<任务目标摘要>

输入来源：

<一句话需求 / TR3 / 其他>

### 2. 分类判断

- Domain：<d3a / general / team-domain>
- Lane：<fast / lite / complex>
- Change Type：<新增需求 / 行为变化 / bugfix / 重构 / 文档>
- Change Shape：<单点 / 跨层 / 霰弹式>

判断原因：

- <reason 1>
- <reason 2>

### 3. 本次需要的契约

- <contract 1>
- <contract 2>

### 4. 范围边界

本次会做：

- <in scope>

本次不会做：

- <out of scope>

禁止越界：

- <forbidden change>

### 5. 完成标准

- <lane completion requirement>
- <domain completion requirement>
- <evidence requirement>

### 6. 需要你确认

请确认：

1. 任务理解是否正确？
2. Domain / Lane 是否正确？
3. 范围边界是否正确？
4. 完成标准是否正确？

回复 `approve` 后，我再进入自动闭环。
```

## 规则

- 不直接向用户展示完整 YAML。
- 必须展示 Domain、Lane、Scope、Completion Gate。
- 如果有 open questions，必须先 Grill Me，不要要求用户 approve。
- Alignment View 不能承载待定细节、open questions 或长篇澄清问题。
- 不允许把 Clarification View 合并进 Alignment View。
- 如果还有 contract / scope / completion gate gap，必须先返回 Clarification View 选择题问题卡。
- 用户 approve 后，底层 Alignment Pack 才视为 approved。
