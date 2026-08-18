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

## Lane

V0 只有三种 Lane：

| Lane | 含义 |
|---|---|
| `fast` | 简单明确、低风险、小范围任务 |
| `lite` | 普通开发任务，范围可控，需要聚焦验证 |
| `complex` | 复杂、高风险、跨模块或关键不确定任务 |

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

### 2. 再判断是否允许 Fast

只有全部满足，才允许 `fast`：

```text
goal_clear
tiny_scope
low_risk
no_behavior_contract_change
no_core_logic_change
no_cross_module_impact
no_new_test_required
simple_verification
```

### 3. 其他默认 Lite

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
- Fast 必须严格准入。
- Lite 是默认中间态。
- 不确定时升级：Fast -> Lite，Lite -> Complex。
- 输出必须可解释，便于人 review。
- 所有 Lane 都必须自闭环，Lane 只改变 evidence 深度。
