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
.claude/skills/idc-workflow/references/registries/skill-adapters.yaml
.claude/skills/idc-gc-sop-adapter/SKILL.md
.claude/skills/idc-dt-design/SKILL.md
.claude/skills/idc-dt-writer/SKILL.md
.claude/skills/idc-gc-third-skill-placeholder/SKILL.md
```

## Output

```yaml
skill_adapter_route:
  selected_adapter: string
  selected_stage: planning | dt_design | dt_writing | implementation | debugging | review | verification
  requested_capability_keys: []
  registry_match_ref: .claude/skills/idc-workflow/references/registries/skill-adapters.yaml
  executable: true
  evidence_ref_required: true
```

## Hard Rules

- Select adapters from `skill-adapters.yaml`, not from skill names alone.
- If no registry row matches, return `NEEDS_ADAPTER_MAPPING`.
- Placeholder adapters are not executable.
- GC SOP atoms cannot choose Domain, Lane, Contract Gate, or Completion Gate.
- `idc-dt-design` is design, not RED/GREEN evidence.
- `idc-dt-writer` can return evidence refs, but cannot mark DONE.
