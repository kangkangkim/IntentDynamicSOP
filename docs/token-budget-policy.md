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
| `fast` | 最小上下文 | grep / basic check，默认不查 OKL / CodeGraph |
| `lite` | 聚焦上下文 | grep + 必要时 CodeGraph |
| `complex` | 分阶段上下文 | grep + CodeGraph + OKL，但必须摘要化 |

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
summary_required: true
evidence_ref_required: true
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
