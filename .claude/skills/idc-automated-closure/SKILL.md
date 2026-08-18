---
name: idc-automated-closure
description: Use after Human Alignment approval to run the post-approval IDC loop through planning, delegation, knowledge loading, execution, verification, targeted fix, replanning, or completion.
---

# Automated Closure Skill

Run the post-approval closure loop.

## When To Use

Use only after Human Alignment is approved.

Do not use before Alignment View approval.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/automated-closure-loop.md
.claude/skills/idc-workflow/references/schemas/escalation-policy.schema.yaml
.claude/skills/idc-workflow/references/schemas/runtime-state.schema.yaml
```

## Output

```yaml
automated_closure_result:
  status: done | fixed | replanned | escalated
  evidence_refs: []
  completion_summary_ref: string
  escalation_trigger: string
```

## Hard Rules

- Do not run without approved Human Alignment.
- Do not add default human checkpoints after approval.
- Escalate only when Escalation Policy requires it.
- Completion still requires Evidence Gate PASS.
