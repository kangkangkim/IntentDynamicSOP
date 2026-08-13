# Deep Dive: Progressive Constraint Loading

约束分三段加载：

```text
Decision
Planning
Execution
```

对应目录：

```text
constraints/decision/
constraints/planning/
constraints/execution/
```

## 为什么要分段

如果一开始加载全部约束，会导致：

- token 浪费。
- 上下文污染。
- Agent 难以聚焦当前阶段。
- D3A 约束和 Core 约束混在一起。

分段后：

- Alignment 前只加载决策约束。
- Planner 前只加载规划约束。
- Execution 前只加载执行约束。

## 团队如何扩展

其他团队可以新增：

```text
constraints/planning/<team-domain>-planning-constraints.yaml
constraints/execution/<team-domain>-execution-constraints.yaml
```

但不要改 Core 约束，除非整个 SOP 的通用纪律变化。
