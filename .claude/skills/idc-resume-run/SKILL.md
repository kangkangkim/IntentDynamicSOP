---
name: idc-resume-run
description: Use inside /id-workflow when the user provides a checkpoint or asks to resume an interrupted IDC run.
---

# Resume Run Skill

Resume from checkpoint refs.

## When To Use

Use when the input is a resume checkpoint or the user asks to continue an interrupted IDC run.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/resume-policy.md
.claude/skills/idc-workflow/references/schemas/runtime-state.schema.yaml
.claude/skills/idc-workflow/references/schemas/delegation-contract.schema.yaml
```

## Output

```yaml
resume_decision:
  status: RESUMABLE | NEEDS_VERIFICATION | ESCALATE
  resume_from_state: string
  required_refs: []
  verification_to_rerun: []
```

## Hard Rules

- Do not use main agent memory as source of truth.
- Runtime state is not DONE evidence.
- Re-run verification when execution may have partially completed.
- If checkpoint refs conflict, escalate instead of guessing.
