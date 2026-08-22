# Deep Dive: Progressive Constraint Loading

约束分三段加载，执行知识另由单元级计划约束：

```text
Decision
Planning
Execution
Knowledge Demand -> Knowledge Load Plan -> Consumption Receipt
```

对应目录：

```text
constraints/decision/
constraints/planning/
constraints/execution/
```

## 为什么要分段

如果一开始加载全部约束，会导致：

- 上下文污染。
- Agent 难以聚焦当前阶段。
- D3A 约束和 Core 约束混在一起。

分段后：

- Alignment 前只加载决策约束。
- Planner 前只加载规划约束。
- Execution 前只加载执行约束。
- 每个 execution unit 只加载 Knowledge Load Plan 选中的 Layer、component、
  test-domain 和静态知识 refs。
- 目录 root 只作为 search scope；搜索或 provider 的实际结果必须记录 result ref。

## 团队如何扩展

其他团队可以新增：

```text
constraints/planning/<team-domain>-planning-constraints.yaml
constraints/execution/<team-domain>-execution-constraints.yaml
```

但不要改 Core 约束，除非整个 SOP 的通用纪律变化。

## 可执行闭环

`plan_context.rb` 负责生成阶段指令加载清单；`plan_knowledge.rb` 根据有效团队配置
和当前 Knowledge Demand 生成不可跨单元复用的 Knowledge Load Plan。Execution
Authorization 同时绑定 Capability Selection 与 `knowledge_plan_id`。

执行者完成后提交 Knowledge Consumption Receipt。只有
`verify_knowledge_consumption.rb` 确认所有 required refs 已加载、没有计划外知识，
且所需 search/provider result refs 与摘要证据齐全，Completion Gate 才能通过。
