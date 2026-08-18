# Human Alignment

Human Alignment 是前置人工对齐点。

设计哲学：

```text
前置对齐
后置自动闭环
异常再回人
```

## 位置

```text
Input Adapter
  -> Domain Resolver
  -> Lane Resolver
  -> Contract Gate
  -> Requirement Assessor
  -> Clarification Provider if needed
  -> Alignment Pack
  -> Human Alignment
  -> Automated Closure Loop
```

## Human Alignment 确认什么

只确认这些内容：

- 输入理解是否正确。
- Domain / Lane 判断是否正确。
- change type / change shape 是否正确。
- contract set 是否正确。
- scope / boundary 是否正确。
- completion gate 是否正确。
- 是否还有 open questions。

它不确认具体实现细节。

## Clarification Provider 的位置

Grill Me / Clarification 发生在 Human Alignment 之前，由 `workflows/clarification-provider.md` 统一管理。

如果 Requirement Assessor 发现关键信息不足：

```text
NEED_CLARIFICATION
  -> Clarification Provider
  -> grill-me-method / grill-with-docs-method / builtin-critical-questions
  -> Clarification View
  -> 更新 normalized_request / contracts
  -> 回到 Requirement Assessor
```

`grill-me-method` 是默认推荐澄清方式。

如果 Grill Me 方法不可用或过重，必须 fallback 到 `builtin-critical-questions`。

## 不允许短路

如果存在 contract / scope / completion gate / API semantics / test evidence / file placement gap：

```text
NEED_CLARIFICATION
  -> Clarification View
  -> 用户回答
  -> Requirement Assessor
  -> Alignment View only after READY_FOR_SPEC
```

禁止把 Clarification 折叠进 Alignment View。

Alignment View 不能包含：

- 待定细节。
- open questions。
- 长篇开放式追问。
- 要用户一边 approve 一边补充关键 contract 的请求。

这些内容必须先通过 `intent-grilling` 的 Clarification View 处理，并且问题必须使用选择题问题卡。

## 输出

```yaml
human_alignment:
  required: true
  status: approved
  reviewer_decision: approve
  notes: []
```

如果用户要求修改理解、分类或边界：

```yaml
human_alignment:
  status: needs_clarification
  reviewer_decision: request_clarification
  notes:
    - 需要重新定义 scope boundary。
```
