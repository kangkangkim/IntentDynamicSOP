---
name: idc-output-surface-router
description: Use inside /id-workflow whenever user-facing output is needed to select exactly one Human View: Brainstorming, Clarification, Alignment, Escalation, or Completion.
---

# Output Surface Router Skill

Choose the user-visible surface.

## When To Use

Use whenever `/id-workflow` needs to respond to the user.

## Reads

```text
.claude/skills/idc-workflow/references/human-views/brainstorming-view.md
.claude/skills/idc-workflow/references/human-views/clarification-view.md
.claude/skills/idc-workflow/references/human-views/alignment-view.md
.claude/skills/idc-workflow/references/human-views/escalation-view.md
.claude/skills/idc-workflow/references/human-views/completion-view.md
```

## Output

```yaml
output_surface:
  selected_view: Brainstorming View | Clarification View | Alignment View | Escalation View | Completion View
  reason: string
  hidden_machine_contract_refs: []
```

## Hard Rules

- Show only one default Human View.
- Do not show raw YAML as the primary user interface.
- Do not merge Clarification View into Alignment View.
- Evidence appears as summary and refs, not full logs.
