# Scenario Router

Scenario Router 只回答一个问题：

```text
这个任务应该进入哪条 workflow？
```

## V0 Route

| Route | 何时使用 | 状态 |
|---|---|---|
| `DOMAIN_MODULE` | 任务匹配某个已注册 Domain Module。 | 已实现插件化骨架 |
| `GENERAL_CODING` | D3A 之外的普通 coding 任务。 | 已实现 |
| `NEED_TRIAGE` | 信息不足，无法判断属于哪类任务。 | 已实现 |

## 规则

- 不要从模糊描述里猜企业 domain 细节。
- 只有当任务匹配 `domains/registry.yaml` 中的某个 module 时，才进入 Domain Module Router。
- D3A 只是一个 active Domain Module，不是 Core 特例。
- 所有没有匹配 Domain Module 的 coding 任务进入 General Coding。
- Router 不判断需求是否清楚。
- Router 不规划 Layer、测试或实现。
- Router 不读取 module 内部知识，只选择 module。

## 输出形状

```yaml
scenario_route:
  route: DOMAIN_MODULE
  selected_module: d3a
  module_file: domains/d3a/module.yaml
  confidence_reason: "用户明确选择 D3A workflow。"
  next: workflows/domain-module-router.md
```
