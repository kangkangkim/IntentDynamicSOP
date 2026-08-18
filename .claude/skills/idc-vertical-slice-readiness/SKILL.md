---
name: idc-vertical-slice-readiness
description: Use before the first confidential-zone D3A execution to verify real bindings exist for one small vertical slice without treating readiness as DONE evidence.
---

# Vertical Slice Readiness Skill

Check readiness for the first real confidential-zone D3A vertical slice.

## When To Use

Use before first confidential-zone D3A execution.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/vertical-slice-readiness-gate.md
.claude/skills/idc-workflow/references/schemas/vertical-slice-readiness.schema.yaml
docs/confidential-migration-checklist.md
```

## Output

```yaml
vertical_slice_readiness:
  status: NOT_READY | READY_FOR_ALIGNMENT | READY_FOR_EXECUTION | BLOCKED
  readiness_checks: []
  missing_bindings: []
  evidence_refs: []
```

## Hard Rules

- Do not mark READY_FOR_EXECUTION while any required check fails.
- Do not replace placeholders with guessed enterprise facts.
- Readiness evidence cannot replace RED/GREEN or `tran_build PASS`.
