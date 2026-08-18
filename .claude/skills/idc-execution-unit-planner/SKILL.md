---
name: idc-execution-unit-planner
description: Use after planning to split approved work into bounded execution units or D3A Layer Context Packets with max 500 LOC per unit.
---

# Execution Unit Planner Skill

Split work into bounded execution units.

## When To Use

Use after Contract Gate and Human Alignment approval, before delegation.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/execution-unit-policy.md
.claude/skills/idc-workflow/references/schemas/execution-unit.schema.yaml
.claude/skills/idc-workflow/references/schemas/layer-context-packet.schema.yaml
```

## Output

```yaml
execution_units:
  - id: string
    selected_layer: string
    allowed_paths: []
    max_change_loc: 500
    expected_evidence: []
```

## Hard Rules

- Every execution unit must be independently verifiable.
- Every code-change execution unit must be `<= 500 LOC`.
- D3A splits first by Layer, then by execution unit.
- If splitting changes scope or contract, return to Human Alignment.
