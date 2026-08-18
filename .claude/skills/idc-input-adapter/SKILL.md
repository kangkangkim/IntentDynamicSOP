---
name: idc-input-adapter
description: Use inside /id-workflow to normalize raw ideas, structured requests, TR3 documents, approved alignment refs, and resume checkpoints into a normalized_request before routing.
---

# Input Adapter Skill

Convert user input into `normalized_request`.

## When To Use

Use at the start of every `/id-workflow` run.

Do not use as a standalone user-facing command.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/input-adapter.md
.claude/skills/idc-workflow/references/schemas/normalized-request.schema.yaml
```

If input is TR3, also read:

```text
.claude/skills/idc-workflow/references/docs/deep-dive/tr3-input.md
```

## Output

```yaml
normalized_request:
  input_type: raw_idea | structured_requirement | tr3_design_doc | approved_alignment | resume_checkpoint
  input_maturity: raw_idea | structured_requirement | tr3_design_doc | approved_alignment
  extracted_goal: string
  domain_candidates: []
  lane_signals: {}
  next_pre_alignment_step: Discovery Provider | Requirement Assessor | Resume Policy
```

## Hard Rules

- Do not decide final Domain or Lane.
- Do not write implementation code.
- Do not treat TR3 DT design as RED/GREEN evidence.
- Do not invent enterprise facts.
