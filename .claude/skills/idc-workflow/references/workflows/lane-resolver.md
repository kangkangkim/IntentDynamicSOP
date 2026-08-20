# Lane Resolver

Lane Resolver 只判断执行强度。

它不判断任务属于哪个领域。D3A / Team Domain / No Domain 由 Domain Resolver 决定。

Lane Resolver 可以使用 Input Adapter 输出的 `lane_signals`。例如 TR3 文档可以抽取出：

```text
api_semantic_change
cross_module_or_layer_impact
multiple_test_domains
needs_dependency_dag
```

Lane 信号必须带事实来源。用户没有提到风险、测试、跨模块或核心逻辑，
不等于对应的否定条件已经成立。缺失或无法确认的信号按 `unknown` 处理，
而 `unknown` 永远不能帮助任务进入 `fast`。

## Lane

V0 只有三种 Lane，且只能输出这三种值：

| Lane | 含义 |
|---|---|
| `fast` | 简单明确、低风险、小范围任务 |
| `lite` | 普通开发任务，范围可控，需要聚焦验证 |
| `complex` | 复杂、高风险、跨模块或关键不确定任务 |

禁止创建或推断第四种 Lane，例如 `known-domain`、`d3a`、`gc`、
`dynamic`、`unknown`。这些都属于 Domain Module、scenario、或
adapter routing，不属于 Lane。

## Lane Applicability

Lane Resolver 只处理 `lane_policy.mode: dynamic` 的 Domain Module，以及
Dynamic Scenario / General Coding。若 module 声明 `mode: not_applicable`，
由该 Domain 的 execution profile 接管执行，并跳过本 Resolver。

D3A module 明确声明 Lane 不适用，并使用 `d3a_fixed_workflow`。这不是第四种
Lane，也不表示 D3A 的每个任务都属于 `complex`。

## 决策顺序

### 1. 先看 Complex hard trigger

命中任意 hard trigger，直接选择 `complex`：

```text
critical_ambiguity
high_risk
cross_module_or_layer_impact
api_semantic_change
state_machine_or_concurrency_or_security_or_performance
data_migration
needs_dependency_dag
needs_multiple_subagents
multiple_test_domains
high_failure_impact
```

### 2. 再看 Lite floor

未命中 Complex hard trigger，但命中任意 Lite floor signal，至少选择
`lite`：

```text
new_capability
behavior_contract_change
new_or_changed_test_required
multi_file_or_multi_component_change
focused_design_required
broad_repo_exploration_required
affected_scope_unknown
```

Lite floor 承接比 Fast 稍大的普通开发：新增能力、行为契约变化、需要新增或
修改测试代码、涉及多个相关文件/组件、需要聚焦设计或需要较广 repo 探索的
任务，至少是 Lite。如果同时出现 Complex hard trigger，仍由 Complex 优先。

`production_code_change`、`bugfix_or_refactor` 本身不是 Lite floor。一个极小、
局部、低风险的 production code 修改，只要无需新增测试代码且已有验证足以
闭环，可以进入 Fast。

### 3. 最后判断是否允许 Fast

只有全部满足，才允许 `fast`：

```text
goal_clear
tiny_scope
low_risk
no_behavior_contract_change
no_core_logic_change
no_cross_module_impact
no_new_test_required
existing_verification_available
simple_verification
localized_change
fast_scope_evidence_present
```

其中：

- `no_new_test_required` 必须有理由，例如现有测试已经覆盖，或修改属于文档、注释、格式、明确配置/常量等无需新增测试的范围。
- `existing_verification_available` 表示仍然能运行现有测试、build、lint、静态检查或等价 basic verification；Fast 不等于不验证。
- `localized_change` 可以是非行为修改，也可以是极小的 production code bugfix，但不能改变 API / 数据契约、核心逻辑或跨模块行为。
- `fast_scope_evidence_present` 必须引用明确文件、diff anchor 或等价范围证据。
- 每个 Fast 条件都必须为显式 `true` 且可追溯；缺失、`false` 或 `unknown` 都会取消 Fast 资格。
- 不允许仅根据“需求很短”“预计改动很少”或“用户没要求测试”推断无需新增测试。

### 4. 其他默认 Lite

```text
不是 fast
也没有 complex hard trigger
=> lite
```

## 输出形状

```yaml
lane_decision:
  selected_lane: complex
  hard_triggers:
    - api_semantic_change
    - multiple_test_domains
  fast_disqualified_by:
    - behavior_contract_change
    - needs_test_evidence
  decision_rule: hard_trigger
  confidence: high
  reasons:
    - 任务涉及 API 语义变化。
    - 任务涉及多个测试域，因此不能走 fast。
```

## 设计原则

- 不靠模型感觉判断复杂度。
- hard trigger 优先。
- Lite floor 承接需要新增/修改测试或稍大范围的普通开发任务。
- Fast 必须严格准入，并有逐项事实证据。
- Lite 是默认中间态。
- 不确定时升级：Fast -> Lite，Lite -> Complex。
- 输出必须可解释，便于人 review。
- 所有 Lane 都必须自闭环，Lane 只改变 evidence 深度。
- 不允许在 Lane Resolver 内把领域熟悉度、业务域、GC、Superpowers 或 adapter 当成 Lane。
- D3A 的 Lane applicability 来自 module policy；Lane Resolver 不重新判断。
