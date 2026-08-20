# Knowledge Gate

Knowledge Gate 的职责是：只加载当前 execution unit 需要的知识。

## 知识分类

静态 domain knowledge：

- Layer knowledge。
- DT domain knowledge。
- Architecture rules。

动态 repository context：

- grep。
- CodeGraph。
- OKL。
- Repository search。

V0 不实现真实 CodeGraph 或 Wiki，只定义接口和 placeholder。

Provider 选择顺序必须遵守：

```text
workflows/provider-selection-matrix.md
```

## 核心规则

每个 Layer Context Packet 只加载：

```text
当前选中 Layer knowledge
+ 当前选中 DT domain knowledge
+ 当前 repository facts
```

禁止一次性加载全部 D3A 知识。

知识条目从 `.idc/effective-team-config.yaml` 读取。Planner / Knowledge Gate 使用
`knowledge.architecture_doc_ref`、`knowledge.feature_docs_root_ref` 和
`knowledge.verification_mapping_ref`；Context Packet builder 使用
`knowledge.layer_docs`。DT、General 或 Custom registry 的 `knowledge_ref` 来自
Resolver 选定的单一有效来源，禁止把默认与团队覆盖混合。

Repo Context Provider 使用 `knowledge.repo_context.provider_skill_ref`；Provider
Selection Matrix 读取 `knowledge.repo_context.policy_ref`。缺少已配置消费者时返回
`NEEDS_TEAM_CONFIG`，不得静默忽略字段。

## Provider Interface

```yaml
context_provider_result:
  provider: grep | codegraph | okl | repo_search
  query: string
  status: SUCCESS | EMPTY | ERROR | PLACEHOLDER
  evidence: []
  notes: []
```

## OKL 约束

OKL 本质是 LLM Wiki。

保密区入口基本是：

```text
okl-query
```

Knowledge Gate 不设计 OKL 本体，只约束：

- 什么时候调用 OKL。
- 调用 OKL 时如何使用 `okl-query` 命令。
- query 问多窄。
- 返回内容如何摘要。
- refs 如何进入 Context Packet。
