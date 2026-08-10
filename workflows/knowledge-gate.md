# Knowledge Gate

Knowledge Gate 的职责是：只加载当前 execution unit 需要的知识。

## 知识分类

静态 domain knowledge：

- Layer knowledge。
- DT domain knowledge。
- Architecture rules。

动态 repository context：

- Grep。
- CodeGraph。
- Wiki。
- Repository search。

V0 不实现真实 CodeGraph 或 Wiki，只定义接口和 placeholder。

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
  provider: grep | codegraph | wiki | repo_search
  query: string
  status: SUCCESS | EMPTY | ERROR | PLACEHOLDER
  evidence: []
  notes: []
```
