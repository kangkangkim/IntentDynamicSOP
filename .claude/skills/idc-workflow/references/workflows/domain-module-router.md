# Domain Module Router

Domain Module Router 是 Scenario Router 的插件化扩展。

它不直接知道每个 domain 的内部 layer，只读取：

```text
domains/registry.yaml
```

然后读取对应：

```text
domains/<domain>/module.yaml
```

## 路由流程

```text
用户任务
  -> Scenario Router
  -> 读取 Domain Module Registry
  -> 匹配 module.route.trigger_rules
  -> 选中某个 Domain Module
  -> 进入 module.workflow.entrypoint
```

如果没有任何 module 匹配：

```text
DYNAMIC_SCENARIO or GENERAL_CODING fallback
```

如果多个 module 都可能匹配：

```text
NEED_TRIAGE
```

## 关键约束

- Router 只选择 module。
- Router 不选择 module 内部 Layer。
- Router 不选择 module 内部 test domain。
- Router 不读取真实企业知识。
- Module 内部规划由该 module 的 planner 负责。
- D3A 是自定义 domain module，不是 Core 特例。
- GC SOP atomic abilities 通过 Skill Adapter Router 复用，不写进 Domain Module Router。

## 输出形状

```yaml
scenario_route:
  route: D3A_CODING
  selected_module: d3a
  module_file: domains/d3a/module.yaml
  confidence_reason: 用户明确选择 D3A。
  next: workflows/d3a-workflow.md
```
