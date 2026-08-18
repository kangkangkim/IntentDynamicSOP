---
name: idc-tdd-state-machine
description: Use when a lane or domain requires TDD state enforcement; prevent GREEN or DONE transitions without required RED/GREEN evidence.
---

# TDD State Machine Skill

Enforce TDD state transitions.

## When To Use

Use for D3A work and any lane/domain where RED/GREEN evidence is required.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/tdd-state-machine.md
.claude/skills/idc-workflow/references/schemas/verification-contract.schema.yaml
```

## Output

```yaml
tdd_transition:
  from_state: string
  to_state: string
  allowed: boolean
  required_evidence_refs: []
  blocker: string
```

## Hard Rules

- Do not allow `SPEC_READY -> IMPLEMENTING -> DONE`.
- Do not allow GREEN without RED evidence when TDD is required.
- Do not allow DONE without required GREEN and build evidence.
