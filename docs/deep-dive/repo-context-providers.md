# Deep Dive: Repo Context Providers

Repo Context Providers 的目标是用较少 token 找到足够的仓库事实。

## 三类事实

```text
grep      -> 文本事实
CodeGraph -> 结构事实
OKL       -> LLM Wiki 知识文档事实，保密区用 okl-query 命令调用
```

这些事实会进入 Context Packet，帮助 Agent 执行，但不能直接作为 DONE evidence。

## 和 Runtime Tool Evidence 的区别

```text
Repo Context:
  帮助理解当前仓库怎么组织。

Runtime Tool Evidence:
  证明这次改动是否通过测试 / 构建 / 检查。
```

优先级：

```text
完成判断：Runtime Tool Evidence 最高
执行约束：User-approved Alignment + Repo-native Rules + Domain Rules
定位事实：Dynamic Repo Facts
知识参考：OKL / Static Knowledge
```

## Provider 顺序

详见：

```text
workflows/provider-selection-matrix.md
```

核心规则：

```text
有代码锚点：先 bounded grep
无代码锚点但有领域语义：先 OKL
既无锚点也无领域语义：先 Discovery / Grilling
```

## Token 控制

Provider 必须遵守：

```text
max_results <= 10
max_snippet_chars <= 800
summary_required = true
evidence_ref_required = true
```

如果 evidence 不够，优先扩大当前 execution unit 的相关查询，而不是全仓搜索。
