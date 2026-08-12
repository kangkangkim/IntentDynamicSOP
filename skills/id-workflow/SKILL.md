---
name: id-workflow
description: Use when the user asks to run, try, trigger, or apply the Intent Dynamic Code / IDC workflow; process a one-line request or TR3 design document; generate an Alignment Pack; classify Domain Module and Lane; or continue an approved Alignment Pack through the automated closure loop with evidence gates.
---

# IDC Workflow

Use this skill to run the Intent Dynamic Code workflow.

This is the orchestration skill. It delegates reusable pre-alignment work to atomic skills:

```text
skills/intent-discovery/SKILL.md
skills/intent-grilling/SKILL.md
skills/intent-alignment/SKILL.md
```

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
  -> Intent Maturity Router
  -> intent-discovery if raw_idea
  -> Domain Resolver
  -> Lane Resolver
  -> Contract Gate
  -> Requirement Assessor
  -> intent-grilling if needed
  -> Alignment Pack
  -> intent-alignment
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

## Human View vs Machine Contract

Do not show users raw YAML as the primary interface.

Use Human View for interaction:

```text
human-views/alignment-view.md
human-views/completion-view.md
human-views/escalation-view.md
```

Keep Machine Contract internally:

```text
schemas/alignment-pack.schema.yaml
schemas/escalation-policy.schema.yaml
schemas/verification-contract.schema.yaml
```

Default user-facing output before approval is Alignment View, not raw `alignment-pack.yaml`.

## Load only what is needed

Read these files first:

```text
CLAUDE.md
workflows/input-adapter.md
workflows/lane-resolver.md
workflows/contract-gate.md
workflows/human-alignment.md
schemas/alignment-pack.schema.yaml
skills/intent-discovery/SKILL.md
skills/intent-grilling/SKILL.md
skills/intent-alignment/SKILL.md
workflows/discovery-provider.md
schemas/discovery-provider.schema.yaml
human-views/brainstorming-view.md
human-views/alignment-view.md
human-views/clarification-view.md
```

If Requirement Assessor returns `NEED_CLARIFICATION`, also read:

```text
workflows/clarification-provider.md
schemas/clarification-provider.schema.yaml
human-views/clarification-view.md
```

If `input_maturity = raw_idea`, run Discovery Provider before Clarification Provider:

```text
workflows/discovery-provider.md
schemas/discovery-provider.schema.yaml
human-views/brainstorming-view.md
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
- Keep `id-workflow` as orchestration; reusable pre-alignment behavior lives in atomic skills.
- Use `brainstorming-method` for `raw_idea`: explore context, ask one key question at a time, propose 2-3 approaches when useful, then draft spec.
- Skip Discovery Provider for TR3 unless the TR3 is too incomplete to identify behavior.
- Clarification Provider only asks for critical missing information needed for contracts, scope, or completion gates.
- Prefer `grill-me-method` for clarification: decision tree, frontier rounds, commitment check, no implementation.
- Use `grill-with-docs-method` only when clarification should create non-sensitive decision records.
- Fallback to `builtin-critical-questions` if Grill Me method is unavailable or too expensive.
- All Lanes must self-close with evidence.
- `fast` does not mean "no verification"; it means small closure.
- Single execution unit code change must be `<= 500 LOC`.
- D3A multi-layer work must split one Layer per Context Packet.
- D3A requires RED evidence, all required DT GREEN, and `tran_build PASS`.
- OKL / docs / CodeGraph / grep findings are context, not DONE evidence.
- Keep enterprise details as placeholders outside the confidential environment.

## Output modes

If the user has not approved yet, output an Alignment Pack summary and ask for approval.

If critical information is missing, output `human-views/clarification-view.md` first and do not ask for approval yet.

If the input is a raw idea, output `human-views/brainstorming-view.md` before clarification.

If the user approved, run the automated closure loop and report:

```text
plan
context loaded
execution units
evidence
completion status
escalation triggers if any
```

Render completion with `human-views/completion-view.md`.

If escalation is triggered, render `human-views/escalation-view.md`.
