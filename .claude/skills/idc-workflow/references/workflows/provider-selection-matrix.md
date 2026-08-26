# Provider Selection Matrix

Provider Selection Matrix 决定 Knowledge Gate 什么时候用 `grep`、`CodeGraph`、`OKL`。

团队 provider policy 从有效配置的 `knowledge.repo_context.policy_ref` 加载；
它只能收窄查询或绑定企业 provider，不能放宽 Context Packet 边界。

目标是让 Agent 按阶段拿到足够、可引用、可验证的上下文，而不是把全文知识库或长搜索结果塞进执行上下文。

## 输入信号

```yaml
provider_selection_input:
  lane_applicability: applicable | not_applicable
  selected_lane: fast | lite | complex | null
  execution_profile: lane_driven | d3a_fixed_workflow | string
  anchor_known: true | false
  domain_known: true | false
  query_intent: find_symbols | find_callers | find_callees | find_similar_impl | find_tests | find_docs | find_build_errors
  impact_unclear: true | false
  rule_or_history_unclear: true | false
```

## Provider 顺序

### anchor_known = true

已经有明确代码锚点，例如 symbol、error string、file path、config key。

```text
bounded grep
  -> targeted CodeGraph if impact_unclear
  -> OKL only if rule_or_history_unclear
```

### anchor_known = false and domain_known = true

没有明确代码锚点，但已有领域语义、Layer、DT domain、TR3 主题或内部概念。

```text
OKL
  -> bounded grep using keywords / refs from OKL
  -> targeted CodeGraph if impact_unclear
```

### anchor_known = false and domain_known = false

既没有代码锚点，也没有稳定领域语义。

```text
intent-discovery / intent-grilling
  -> OKL only if domain hints are needed
  -> bounded grep
```

## Lane Context Strategy

| Lane | OKL | grep | CodeGraph |
|---|---:|---:|---:|
| fast | 0 by default, max 1 query if no anchor and domain_known | max 2 queries, max 5 results/query, snippet 0 by default | off by default |
| lite | max 1 query if no anchor or rule/history unclear | max 5 queries, max 8 results/query, snippet <= 3 lines | only if impact_unclear |
| complex | per execution unit / layer packet | per execution unit / layer packet | per execution unit / layer packet |

D3A 不使用 Lane 行。它按 `d3a_fixed_workflow` 和当前 Layer Context Packet
选择 provider，查询边界不得跨 Layer。

## OKL Adapter Rules

OKL 是已有 LLM Wiki 能力，接入团队配置后，入口基本是：

```text
okl-query
```

IDC 不设计 OKL 本体，只约束什么时候调用 OKL，以及如何使用 `okl-query` 这条命令。

`okl-query` 请求必须：

- 只问当前 execution unit 或当前 Layer。
- 明确要求返回 summary / refs / keywords。
- 不要求长文全文。
- 不要求生成实现方案。
- 不要求判断 DONE。

建议 query 形状：

```text
For <task/layer>, return only:
1. relevant internal concept refs
2. likely code keywords or file families
3. constraints or historical rules
4. no full document text
```

## 输出要求

Provider 结果统一进入 Context Packet：

```yaml
provider_selection_result:
  selected_order:
    - OKL
    - grep
  commands:
    OKL: okl-query
  budget:
    max_okl_queries: 1
    max_grep_queries: 5
    max_results_per_query: 8
    max_snippet_lines: 3
  findings_summary:
    - provider: okl
      summary: "<summary>"
      evidence_ref: "<okl_ref>"
```

## 禁止

- 全仓无边界 grep。
- 把 grep 原始长输出塞进上下文。
- 把 OKL 全文塞进上下文。
- 把 OKL 当作 test/build evidence。
- 用 OKL 覆盖代码事实。
- 在 fast lane 默认调用 CodeGraph。
