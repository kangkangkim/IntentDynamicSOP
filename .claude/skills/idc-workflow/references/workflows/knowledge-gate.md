# Knowledge Gate

Knowledge Gate 的职责是：只加载当前 execution unit 需要的知识。

该约束由可执行链强制：

```text
Knowledge Demand
  -> plan_knowledge.rb
  -> Knowledge Load Plan READY
  -> Execution Authorization 绑定 knowledge_plan_id
  -> executor 产出 Knowledge Consumption Receipt
  -> verify_knowledge_consumption.rb
  -> VERIFIED 才能进入 Completion Gate
```

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

Knowledge Load Plan 必须绑定一个 `execution_unit_ref`。D3A 选择一个 Layer 和
本单元 required DT Domains；General 选择本单元 component/test domains；Custom
Domain 选择一个 coding layer 和 test domains。未知 ID 或缺少 required ref 返回
`NEEDS_KNOWLEDGE_MAPPING`。

静态知识、搜索范围和动态 repo context 分开记录：目录 root 只能作为 search
scope，不能当作已加载正文；Provider/grep 必须返回 result ref。消费回执若遗漏
required ref，或包含计划外 Layer/component/test-domain ref，返回
`BLOCKED_KNOWLEDGE_CONSUMPTION`。

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

接入团队配置后，入口基本是：

```text
okl-query
```

Knowledge Gate 不设计 OKL 本体，只约束：

- 什么时候调用 OKL。
- 调用 OKL 时如何使用 `okl-query` 命令。
- query 问多窄。
- 返回内容如何摘要。
- refs 如何进入 Context Packet。
