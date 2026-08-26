# Completion View

这是给用户看的完成摘要。

背后的机器契约可以是：

```text
evidence-summary.yaml
completion-summary.md
```

## 模板

```text
## 完成摘要

### 1. 状态

<DONE / PARTIAL / ESCALATED>

### 2. 做了什么

- <change summary 1>
- <change summary 2>

### 3. 执行单元

- <execution unit id>：<summary>，变更 <LOC> 行
- <execution unit id>：<summary>，变更 <LOC> 行

### 4. 验证证据

- <test/build/check>：<PASS/FAIL>，ref: <evidence_ref>
- <test/build/check>：<PASS/FAIL>，ref: <evidence_ref>

### 5. 完成标准

- Lane completion：<satisfied / not satisfied>
- Domain completion：<satisfied / not satisfied>
- Open escalation：<none / trigger>

### 6. 结论

<能否 DONE，以及原因>
```

## 规则

- Evidence 只展示摘要和 ref，不展示完整日志。
- 如果没有 evidence_ref，不能展示为 DONE。
- 如果任何 completion gate 未满足，状态不能是 DONE。
