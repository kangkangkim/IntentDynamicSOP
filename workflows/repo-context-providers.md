# Repo Context Providers

Repo Context Providers 负责获取当前代码仓相关上下文。

V0 主要统一三类 provider：

```text
grep / CodeGraph / OKL
```

它们位于 Knowledge Gate 内：

```text
Knowledge Gate
  -> Static Domain Knowledge
  -> Repo-native Architecture & Rules
  -> Dynamic Repo Facts
       -> grep
       -> CodeGraph
       -> OKL
```

Provider 顺序由 `workflows/provider-selection-matrix.md` 决定。

## Provider 分工

| Provider | 职责 | 典型问题 |
|---|---|---|
| `grep` | 文本事实 | 这个 symbol / error / config 在哪里出现？ |
| `codegraph` | 结构事实 | 谁调用谁？影响范围是什么？ |
| `OKL` | LLM Wiki 工具；保密区通过 `okl-query` 命令调用 | 历史设计、TR3、领域约定怎么说？ |
| `repo_search` | 仓库搜索 | 类似实现和测试在哪里？ |

## 使用规则

- 有明确代码锚点时，先 bounded grep。
- 没有代码锚点但有领域语义时，先 OKL 拿 refs / keywords，再 bounded grep。
- Fast 默认只用 bounded grep / basic repo search；只有 no anchor + domain known 时最多 1 次 OKL 查询。
- Lite 使用 bounded grep，必要时使用 CodeGraph；如果规则或历史不清楚，最多 1 次 OKL 查询。
- Complex 可以使用 grep + CodeGraph + OKL，但必须按 execution unit / layer packet 摘要化。
- D3A 多 Layer 必须按 Layer Context Packet 分别查询。
- provider 只返回 facts / refs，不做最终决策。
- provider 结果必须进入 Context Packet，而不是直接进入 DONE 判断。
- `okl-query` 是调用 OKL 的命令，不是 provider 名；IDC 不实现 OKL 本体。

## 输出要求

每条 finding 必须包含：

```text
type
path
summary
evidence_ref
confidence
```

禁止：

```text
无 evidence_ref 的结论
长文档全文
全仓无边界搜索
把 OKL 当作测试 evidence
```
