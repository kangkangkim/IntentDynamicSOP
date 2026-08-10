# Progressive Constraint Loading

约束不是一次性全塞进上下文，而是分阶段加载。

```text
Decision Constraints
  -> Alignment 前

Planning Constraints
  -> Planner 前

Execution Constraints
  -> Execution 前
```

## Decision Constraints

加载点：

```text
Input Adapter
  -> Domain Resolver
  -> Lane Resolver
  -> Contract Gate
  -> Alignment Pack
```

来源：

```text
constraints/decision/
```

用途：

- 选择 Domain。
- 选择 Lane。
- 选择 Contract Set。
- 生成 Alignment Pack。

## Planning Constraints

加载点：

```text
Human Alignment approved
  -> Planner
```

来源：

```text
constraints/planning/
```

用途：

- 限制 scope。
- 限制 registry。
- 限制 DAG / mapping。
- 拆分 execution unit。

## Execution Constraints

加载点：

```text
Planner
  -> Knowledge Gate
  -> Execution Runtime
```

来源：

```text
constraints/execution/
```

用途：

- 限制 context loading。
- 限制 subagent 边界。
- 限制 500 LOC execution unit。
- 限制 evidence gate。
