# Domain Module Router

Domain Module Router 是 Scenario Router 的插件化扩展。

它不直接知道每个 domain 的内部 layer。运行时先读取：

```text
.idc/effective-team-config.yaml
```

内置 `d3a` / `general` 再读取共享 module；启用了 `custom` 时直接使用
Resolver 从 `team-config.yaml.domain.custom` 生成的有效 module。团队可通过
`domain.enabled` 同时启用多个 Domain，`domain.mode` 只作为默认兜底：

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
- Router 只能从 `effective.domains.enabled` 中选择一个 module；多选表示团队能力范围，不表示一次任务并行执行多个 Domain。
- Router 不选择 module 内部 Layer。
- Router 不选择 module 内部 test domain。
- Router 不读取真实企业知识。
- D3A 的 `domain.d3a.dt_domains`、General 的 `general.components` / `general.test_domains` 非空时整体替换默认 registry；不合并两个来源。
- Custom Domain 由 `domain.custom` 内联注册，不要求团队编辑共享 `domains/registry.yaml`。
- 所有启用的内置 Domain（`d3a` / `general`）必须在 `domains/registry.yaml` 中保持 `status: active`；Resolver 会拒绝未注册的 enabled mode。
- `plan_context` 接受任意已启用的 `--domain`，拒绝未启用项；custom 域还接受声明的 `domain.custom.id`（与 `custom` 等价，且不得复用 `d3a` / `general` / `custom` 保留字）。旧配置未声明 `domain.enabled` 时仍保持单 Domain 匹配规则。
- Module 内部规划由该 module 的 planner 负责。
- D3A 是自定义 domain module，不是 Core 特例。
- Domain Module 可以声明 `lane_policy.mode: dynamic | fixed | not_applicable`。
- `dynamic` module 交给 Lane Resolver；lane-applicable 路由缺省 `--lane` 时回落 `lane.default`，两者皆无才 INVALID。
- `fixed` module 的 `selected_lane` 固定生效：缺省 `--lane` 自动填充，显式冲突的 `--lane` 会被拒绝，且 fixed Lane 不再经过 Lane Resolver。
- `not_applicable` 由 module execution profile 接管并跳过 Lane Resolver。
- D3A module 使用 `not_applicable` 和 `d3a_fixed_workflow`，不输出 Lane。
- D3A / Custom 可声明 `domain.<id>.orchestration.mode: ordered` 来调整
  Domain 中间原子 Skill 顺序；它不转移 Planner、Knowledge、Contract 或
  Completion Gate 所有权。
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
