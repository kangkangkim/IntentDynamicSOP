# E2E Demo: TR3 -> D3A -> Automated Closure

这个 demo 展示一条公开 mock 流程：

```text
TR3 输入
  -> normalized_request
  -> domain/lane decision
  -> alignment_pack
  -> d3a_plan
  -> context_packet
  -> evidence
  -> completion_summary
```

所有内容都是 dummy 示例，不包含企业真实 D3A 知识。

运行真实系统时，TR3 / Repo Context / DT / tran_build 都必须在团队配置内绑定。
