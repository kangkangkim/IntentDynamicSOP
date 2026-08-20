# Human Alignment

Human Alignment 是前置人工对齐点，也是 readiness / gap / approval 的统一检测 gate。

所有需要用户确认、批准、重新分类、补充澄清或处理异常回流的交互，都必须通过 `AskUserTool` 发出。具体出口契约见 `workflows/ask-user-tool-policy.md`。

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
  -> Module Lane applicability, then Lane Resolver only when applicable
  -> Contract Gate
  -> Human Alignment Check
  -> Clarification Provider / Discovery Provider if needed
  -> Alignment Pack
  -> Human Alignment
  -> Automated Closure Loop
```

## Human Alignment Check 管什么检测

Human Alignment Check 不写代码、不做最终实现规划。它只决定当前材料能不能给人确认，或者应该先回到哪个前置能力。

它统一检测：

- `readiness`: 是否已经能生成 Alignment View。
- `critical_gap`: contract / scope / completion gate / API semantics / test evidence / file placement 是否缺关键决策。
- `needs_alternatives`: raw idea 是否还需要 Brainstorming 发散。
- `docs_needed`: 澄清结果是否需要同步到非敏感 docs / ADR / glossary。
- `approval_validity`: 已有 approval ref / runtime checkpoint 是否仍可信。
- `scope_drift`: 当前事实是否超出已 approve 的 scope。

检测结果只允许进入这些状态：

```text
NEEDS_BRAINSTORMING
NEEDS_CLARIFICATION
NEEDS_CLARIFICATION_WITH_DOCS
READY_FOR_ALIGNMENT
APPROVED_TO_EXECUTE
NEEDS_RE_ALIGNMENT
```

Discovery 可以产出 `maturity_signal`，但不能替代 Human Alignment Check 做 readiness decision。

## Human Alignment 确认什么

只确认这些内容：

- 输入理解是否正确。
- Domain / Lane applicability 是否正确；D3A 应为 `not_applicable` 并采用固定 D3A workflow。
- change type / change shape 是否正确。
- contract set 是否正确。
- scope / boundary 是否正确。
- completion gate 是否正确。
- 是否还有 open questions。

它不确认具体实现细节。

## Provider 触发位置

Brainstorming、Grill Me、Grill With Docs 发生在 Human Alignment approval 之前，由 Human Alignment Check 触发。澄清 provider 规则仍由 `workflows/clarification-provider.md` 管理。

如果 Human Alignment Check 发现关键信息不足：

```text
NEEDS_CLARIFICATION
  -> Clarification Provider
  -> grill-me-method / grill-with-docs-method / builtin-critical-questions
  -> Clarification View
  -> 更新 normalized_request / contracts
  -> 回到 Human Alignment Check
```

`grill-me-method` 是默认推荐澄清方式。

如果 Grill Me 方法不可用或过重，必须 fallback 到 `builtin-critical-questions`。

## 不允许短路

如果存在 contract / scope / completion gate / API semantics / test evidence / file placement gap：

```text
NEEDS_CLARIFICATION
  -> Clarification View
  -> AskUserTool 用户回答
  -> Human Alignment Check
  -> Alignment View only after READY_FOR_ALIGNMENT
```

禁止把 Clarification 折叠进 Alignment View。

Alignment View 不能包含：

- 待定细节。
- open questions。
- 长篇开放式追问。
- 要用户一边 approve 一边补充关键 contract 的请求。

这些内容必须先通过 `intent-grilling` 的 Clarification View 处理，并且问题必须使用选择题问题卡。

Alignment approval 也必须通过 `AskUserTool`，不能在普通文本里请求用户回复 approve。

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

如果 `AskUserTool` 不可用，Human Alignment 必须返回 `BLOCKED_NEEDS_ASK_USER_TOOL`，不能把 approval 或 re-alignment 当作已完成。
