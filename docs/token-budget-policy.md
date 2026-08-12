# Token Budget Policy

保密区算力有限，IDC 必须默认节省 token。

## 总原则

```text
默认小上下文
按阶段加载
只加载 impacted scope
长文档先摘要再引用
证据保留 ref，不塞全文
失败时局部扩展
```

## Lane Budget

| Lane | 目标上下文策略 | Provider 策略 |
|---|---|---|
| `fast` | 最小上下文 | anchor known 时 bounded grep；no anchor + domain known 时最多 1 次 okl-query |
| `lite` | 聚焦上下文 | bounded grep + 必要时 CodeGraph；规则或历史不清楚时最多 1 次 okl-query |
| `complex` | 分阶段上下文 | grep + CodeGraph + okl-query，但必须按 packet 摘要化 |

## 建议预算

```text
fast: 2k - 6k context
lite: 6k - 20k context
complex: 分阶段，每阶段 10k - 30k
D3A subagent: 每个 Layer Context Packet 单独预算
```

## Provider 限制

```yaml
max_results: 10
max_snippet_chars: 800
max_okl_queries: 1
max_grep_queries: 5
max_snippet_lines: 3
summary_required: true
evidence_ref_required: true
```

## Provider 顺序

```text
anchor_known = true:
  bounded grep -> targeted CodeGraph? -> okl-query?

anchor_known = false and domain_known = true:
  okl-query -> bounded grep -> targeted CodeGraph?

anchor_known = false and domain_known = false:
  intent-discovery / intent-grilling -> okl-query? -> bounded grep
```

OKL 本质是 LLM Wiki。

IDC 只约束 `okl-query` 的使用方式：

```text
只问当前 execution unit / Layer
只要 summary / refs / keywords
不拉全文
不当 DONE evidence
```

## Evidence 限制

Evidence 只放摘要和引用：

```yaml
evidence:
  status: PASS
  summary: "相关测试通过。"
  evidence_ref: path/to/log.txt
```

不要把完整日志塞进上下文。

## D3A 多 Layer

```text
一个 Layer Context Packet 一个预算
一个 execution unit <= 500 LOC
失败时只扩展责任 Layer 上下文
```
