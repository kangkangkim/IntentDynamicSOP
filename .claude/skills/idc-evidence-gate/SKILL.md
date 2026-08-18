---
name: idc-evidence-gate
description: Use before Completion View to decide whether RED, GREEN, test/build, and tran_build evidence satisfy the selected Domain and Lane completion gates.
---

# Evidence Gate Skill

Check completion evidence.

## When To Use

Use after execution, DT writing, test/build runs, or targeted fixes.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/lane-completion.md
.claude/skills/idc-workflow/references/workflows/tdd-state-machine.md
.claude/skills/idc-workflow/references/schemas/verification-contract.schema.yaml
.claude/skills/idc-workflow/references/schemas/runtime-state.schema.yaml
```

## Output

```yaml
evidence_gate:
  status: PASS | FAIL | BLOCKED
  red_evidence_refs: []
  green_evidence_refs: []
  build_evidence_refs: []
  missing_evidence: []
  next: Completion View | Escalation View | Targeted Fix
```

## Hard Rules

- No RED means no GREEN for TDD-required work.
- D3A DONE requires all required DT GREEN and `tran_build PASS`.
- Readiness evidence cannot replace DONE evidence.
- Knowledge refs cannot replace tool evidence.
