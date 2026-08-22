# Domain Module Router

Domain Module Router 是 Scenario Router 的插件化扩展。

它不直接知道每个 domain 的内部 layer。运行时先读取：

```text
.idc/effective-team-config.yaml
```

内置 `d3a` / `general` 再读取共享 module；`domain.mode: custom` 直接使用
Resolver 从 `team-config.yaml.domain.custom` 生成的有效 module：

```text
domains/<domain>/module.yaml
or effective domain source = team-config-inline
```

## 路由流程

```text
用户任务
  -> Scenario Router
  -> 读取 Effective Domain Registry
  -> 匹配 module.route.trigger_rules
  -> 选中某个 Domain Module
  -> 应用 module.lane_policy
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
- D3A 的 `domain.d3a.dt_domains`、General 的 `general.components` / `general.test_domains` 非空时整体替换默认 registry；不合并两个来源。
- Custom Domain 由 `domain.custom` 内联注册，不要求团队编辑共享 `domains/registry.yaml`。
- 内置 `domain.mode`（`d3a` / `general`）必须在 `domains/registry.yaml` 中保持 `status: active`；Resolver 会拒绝未注册的内置 mode。拔掉内置 domain 意味着同时删除 registry 条目并切换 `domain.mode`。
- `plan_context` 拒绝与 effective domain 不一致的 `--domain` 取值：`general` / `d3a` 只在 effective domain id 一致时可用，`custom` 只在 effective domain 来源为 `team-config-inline` 时可用。
- Module 内部规划由该 module 的 planner 负责。
- D3A 是自定义 domain module，不是 Core 特例。
- Domain Module 可以声明 `lane_policy.mode: dynamic | fixed | not_applicable`。
- `dynamic` module 交给 Lane Resolver；`fixed` 为确实需要固定 Lane 的团队扩展保留；`not_applicable` 由 module execution profile 接管并跳过 Lane Resolver。
- D3A module 使用 `not_applicable` 和 `d3a_fixed_workflow`，不输出 Lane。
- GC SOP atomic abilities 通过 Skill Adapter Router 复用，不写进 Domain Module Router。

## 输出形状

```yaml
scenario_route:
  route: D3A_CODING
  selected_module: d3a
  module_file: domains/d3a/module.yaml
  lane_policy:
    mode: not_applicable
    selected_lane: null
    bypass_lane_resolver: true
    execution_profile: d3a_fixed_workflow
  confidence_reason: 用户明确选择 D3A。
  next: workflows/d3a-workflow.md
```
