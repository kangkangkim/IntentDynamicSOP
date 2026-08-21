---
name: idc-dt-writer
description: Use through idc-gc-sop-adapter when an approved DT design should be turned into DT changes and RED/GREEN evidence; this external harness only defines the non-sensitive adapter boundary for the original enterprise repo skill.
---

# DT Writer Skill Adapter

This adapter represents the original enterprise repository skill used to write
DT.

It does not contain real enterprise DT implementation details.

## When To Use

Use only after:

- IDC Human Alignment is approved.
- `idc-dt-design` has produced `READY_FOR_DT_WRITER`, or an equivalent approved DT design ref exists.
- The selected DT domain is known.
- Allowed paths and forbidden paths are explicit.
- The DT build skill is bound (`bindings.dt_build.skill_ref`) after team-config onboarding.

Do not use when:

- there is no DT design ref.
- the task only needs DT design, not DT writing.
- required repository files are outside the approved scope.
- RED/GREEN evidence cannot be produced.

## Input

```yaml
dt_writer_input:
  dt_design_ref: string
  selected_dt_domains: []
  allowed_paths: []
  forbidden_paths: []
  dt_build_skill_ref: string
  max_change_loc: 500
```

## Output

```yaml
dt_writer_output:
  status: RED_READY | GREEN_READY | BLOCKED | FAILED
  changed_files: []
  red_evidence_refs: []
  green_evidence_refs: []
  blocker_summary: string
  followup_fix_ref: string
```

## Hard Rules

- Do not write outside `allowed_paths`.
- Do not exceed `max_change_loc: 500`.
- Do not mark GREEN without RED evidence when the domain requires TDD completion.
- Do not mark D3A DONE; IDC Completion Gate owns DONE.
- Real enterprise DT writing rules must remain behind `<ENTERPRISE_ORIGINAL_REPO_SKILL_REF>`.
