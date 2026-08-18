---
name: idc-lane-completion
description: Use before completion to check fast, lite, or complex lane closure requirements independently from domain-specific completion gates.
---

# Lane Completion Skill

Check lane-level completion.

## When To Use

Use before Evidence Gate final PASS.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/lane-completion.md
.claude/skills/idc-workflow/references/lanes/registry.yaml
.claude/skills/idc-workflow/references/lanes/fast.yaml
.claude/skills/idc-workflow/references/lanes/lite.yaml
.claude/skills/idc-workflow/references/lanes/complex.yaml
```

## Output

```yaml
lane_completion:
  selected_lane: fast | lite | complex
  status: PASS | FAIL | BLOCKED
  missing_evidence: []
```

## Hard Rules

- All lanes must self-close with evidence.
- `fast` still requires verification evidence.
- Domain completion gates are additive, not replacements.
