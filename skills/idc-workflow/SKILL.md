---
name: idc-workflow
description: Use when the user asks to run, try, trigger, or apply the Intent Dynamic Code / IDC workflow; process a one-line request or TR3 design document; generate an Alignment Pack; classify Domain Module and Lane; or continue an approved Alignment Pack through the automated closure loop with evidence gates.
---

# IDC Workflow

Use this skill to run the Intent Dynamic Code workflow.

## Trigger examples

- "用 IDC workflow 处理这个 TR3。"
- "按这套 SOP 跑一下。"
- "生成 Alignment Pack。"
- "我 approve 了，继续自动闭环。"
- "判断这个任务是 D3A 还是 General，应该走哪个 Lane。"

## Required behavior

Default mode:

```text
Input Adapter
  -> Domain Resolver
  -> Lane Resolver
  -> Contract Gate
  -> Requirement Assessor
  -> Grill Me if needed
  -> Alignment Pack
  -> Human Alignment
```

After the user approves:

```text
Automated Closure Loop
  -> Planner
  -> Progressive Constraint Loading
  -> Knowledge Gate
  -> Execution
  -> Verification
  -> DONE / Targeted Fix / Re-plan
```

## Load only what is needed

Read these files first:

```text
CLAUDE.md
workflows/input-adapter.md
workflows/lane-resolver.md
workflows/contract-gate.md
workflows/human-alignment.md
schemas/alignment-pack.schema.yaml
```

If the input is TR3, also read:

```text
schemas/normalized-request.schema.yaml
docs/deep-dive/tr3-input.md
```

If Domain = D3A, also read:

```text
domains/d3a/module.yaml
workflows/d3a-workflow.md
schemas/d3a-plan.schema.yaml
```

If the user has approved the Alignment Pack, also read:

```text
workflows/automated-closure-loop.md
workflows/progressive-constraint-loading.md
workflows/execution-unit-policy.md
workflows/lane-completion.md
schemas/escalation-policy.schema.yaml
```

For repo context work, read:

```text
workflows/repo-context-providers.md
schemas/repo-context-provider.schema.yaml
docs/token-budget-policy.md
```

## Hard rules

- Do not write implementation code before Human Alignment approval.
- Grill Me only asks for critical missing information needed for contracts, scope, or completion gates.
- All Lanes must self-close with evidence.
- `fast` does not mean "no verification"; it means small closure.
- Single execution unit code change must be `<= 500 LOC`.
- D3A multi-layer work must split one Layer per Context Packet.
- D3A requires RED evidence, all required DT GREEN, and `tran_build PASS`.
- OKL / docs / CodeGraph / grep findings are context, not DONE evidence.
- Keep enterprise details as placeholders outside the confidential environment.

## Output modes

If the user has not approved yet, output an Alignment Pack summary and ask for approval.

If the user approved, run the automated closure loop and report:

```text
plan
context loaded
execution units
evidence
completion status
escalation triggers if any
```
