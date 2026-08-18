---
name: idc-lane-resolver
description: Use inside /id-workflow after scenario/domain routing to choose fast, lite, or complex execution intensity from explicit lane signals.
---

# Lane Resolver Skill

Select execution intensity.

IDC V0 lane ids are exactly `fast`, `lite`, and `complex`.

## When To Use

Use after top-level route is known and before Contract Gate.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/lane-resolver.md
.claude/skills/idc-workflow/references/lanes/registry.yaml
```

## Output

```yaml
lane_decision:
  selected_lane: fast | lite | complex
  decision_rule: hard_trigger | fast_all_conditions_met | default_lite
  hard_triggers: []
  fast_disqualified_by: []
```

## Hard Rules

- Lane is intensity, not domain.
- Do not invent fourth lane ids such as `known-domain`, `d3a`, `gc`, `dynamic`, or `unknown`.
- Hard triggers force `complex`.
- `fast` requires all fast conditions.
- `fast` still requires verification evidence.
