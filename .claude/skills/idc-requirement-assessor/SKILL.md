---
name: idc-requirement-assessor
description: Use inside /id-workflow after Contract Gate to decide READY_FOR_SPEC or NEED_CLARIFICATION based on critical missing fields.
---

# Requirement Assessor Skill

Check whether requirements are contract-ready.

## When To Use

Use before generating Alignment View.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/requirement-assessor.md
```

## Output

```yaml
requirement_assessment:
  status: READY_FOR_SPEC | NEED_CLARIFICATION
  missing_critical_fields: []
  clarification_frontier: []
  next: intent-grilling | intent-alignment
```

## Hard Rules

- Do not ask broad open-ended questions.
- Do not generate Alignment View when critical fields are missing.
- Do not write implementation code.
