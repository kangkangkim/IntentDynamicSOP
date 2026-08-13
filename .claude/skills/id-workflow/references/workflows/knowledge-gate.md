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
