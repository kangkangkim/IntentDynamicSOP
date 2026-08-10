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

## Grill Me 的位置

Grill Me / Clarification 发生在 Human Alignment 之前。

如果 Requirement Assessor 发现关键信息不足：

```text
NEED_CLARIFICATION
  -> Grill Me
  -> 更新 normalized_request / contracts
  -> 回到 Requirement Assessor
```

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
