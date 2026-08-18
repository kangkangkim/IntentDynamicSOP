---
name: idc-progressive-constraint-loader
description: Use inside /id-workflow to load only the current stage's decision, planning, or execution constraints.
---

# Progressive Constraint Loader Skill

Load stage-specific constraints.

## When To Use

Use whenever IDC moves between decision, planning, and execution stages.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/progressive-constraint-loading.md
.claude/skills/idc-workflow/references/constraints/decision/
.claude/skills/idc-workflow/references/constraints/planning/
.claude/skills/idc-workflow/references/constraints/execution/
```

## Output

```yaml
constraint_load:
  stage: decision | planning | execution
  loaded_constraint_refs: []
  forbidden_actions: []
```

## Hard Rules

- Load only current stage constraints.
- Do not turn context loading into a token budget policy.
- Do not drop safety constraints required by the current stage.
