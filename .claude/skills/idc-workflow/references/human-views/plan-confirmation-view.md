# Plan Confirmation View

这是给开发人员看的技术方案确认卡片，在 Execution Authorization / dispatch 之前展示。

确认本身必须通过 `AskUserTool` 发出；本文件只定义展示模板，不是直接 confirmation 通道。

背后的机器契约是：

```text
schemas/execution-authorization.schema.yaml（technical_plan_confirmation）
workflows/execution-authorization-gate.md
```

## 模板

```text
## 请确认技术方案

这是一个只针对技术方案的窄确认：不重新讨论任务方向、目标和 scope。

### 1. 计划件本体

方案落在计划件：<general-plan.yaml / d3a-plan.yaml 文件名>

- Execution Unit：<EU 列表，每条一句摘要 + <=500 LOC 标注>
- Coding Layers / Components：<d3a: coding_layers；general: selected_components>
- DT / Test Domain mapping：<layer/component -> required DT domains>
- 依赖 DAG：<from -> to 摘要>

### 2. API Contract

- Contract Gate 判定：<required / not_required>
- 若 required：待确认的 API Contract 摘要（接口语义、行为变化点）
- D3A 语义：确认后冻结（freeze），此后变更需重新确认

### 3. DT 设计

- selected_dt_domains：<选中的 DT domains>
- RED / GREEN plan：<每个 required DT domain 的 RED 先行、GREEN 判定方式>

### 4. Scope 边界对照

已批准的 Alignment Pack scope：

- 本次会做：<in_scope>
- 本次不会做：<out_of_scope>
- 禁止越界：<forbidden_changes>

本计划覆盖范围：

- <计划 EU 覆盖点>

对照结果：<未超出 / 超出>

### 5. 需要你确认

请确认：

1. 计划件本体（EU / layers / DT mapping / 依赖 DAG）是否正确？
2. required API Contract 是否正确？
3. DT 设计与 RED/GREEN plan 是否正确？

通过 AskUserTool 确认后，我才生成 execution authorization 并 dispatch。
```

## 规则

- 只展示人需要确认的三件（计划件本体、API Contract、DT 设计）加 scope 边界对照；不展示 YAML 原文、knowledge refs、capability selection 细节。
- 这是框架 floor：fast / lite / complex 全部 lane 与 d3a 固定 workflow 都必须展示本视图并确认，没有「小改动跳过」例外。
- 确认只针对技术方案；不得在这里重新对齐任务方向、目标或 scope。
- 如果 scope 边界对照发现计划超出已批准 scope，不在本视图内要求用户就地确认越界计划：返回 NEEDS_RE_ALIGNMENT，回流 Human Alignment。
- confirmation 必须指向落盘计划件（general-plan / d3a-plan schema）；没有落盘文件就没有可确认对象。
- confirm / request change 必须通过 `AskUserTool` 收集；如果不可用，返回 `BLOCKED_NEEDS_ASK_USER_TOOL`。
