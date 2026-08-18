---
name: idc-skill-adapter-router
description: Use after Human Alignment approval to route bounded work to GC SOP, original-repository skill adapters, or other registered skill adapters without exposing enterprise internals.
---

# Skill Adapter Router Skill

Route to lower-level skill adapters.

## When To Use

Use when an approved task needs GC SOP atoms, original repository DT skills, or another adapter under `.claude/skills/`.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/skill-adapter-router.md
.claude/skills/idc-workflow/references/schemas/skill-adapter.schema.yaml
.claude/skills/gc-sop-adapter/SKILL.md
.claude/skills/dt-design/SKILL.md
.claude/skills/dt-writer/SKILL.md
.claude/skills/gc-third-skill-placeholder/SKILL.md
```

## Output

```yaml
skill_adapter_route:
  selected_adapter: string
  selected_stage: planning | dt_design | dt_writing | implementation | debugging | review | verification
  executable: true
  evidence_ref_required: true
```

## Hard Rules

- Placeholder adapters are not executable.
- GC SOP atoms cannot choose Domain, Lane, Contract Gate, or Completion Gate.
- `dt-design` is design, not RED/GREEN evidence.
- `dt-writer` can return evidence refs, but cannot mark DONE.
