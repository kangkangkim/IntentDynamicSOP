---
name: idc-general-coding
description: Use when a coding task does not match a specialized domain module and should run through the General Coding workflow with task, verification, TDD, and evidence gates.
---

# General Coding Skill

## When To Use

Use this skill when Domain Module Router selects `general`.

If the General Coding request is rough, vague, sketchy, one-line, or says “大概想做 / 先试试 / 还没想清楚”, do not start General Coding yet.

Route back to:

```text
.claude/skills/idc-intent-discovery/SKILL.md
```

General Coding starts only after the rough idea becomes a draft spec and passes Human Alignment.

## Flow

```text
idc-intent-discovery if raw_idea
  -> idc-intent-grilling if needed
  -> idc-intent-alignment
  -> General Plan
  -> Provider Selection Matrix
  -> Execution Unit <= 500 LOC
  -> RED evidence if tests are required
  -> implementation
  -> GREEN evidence
  -> build/static check evidence if required
  -> Completion View
```

## Required Contracts

```text
task_contract
verification_contract
```

API Contract is optional and only required when the task changes API or externally visible behavior.

## Output

```yaml
general_coding_result:
  status: done | blocked | needs_fix | escalated
  selected_components: []
  required_test_domains: []
  changed_files: []
  test_or_build_evidence_refs: []
  completion_summary_ref: <COMPLETION_SUMMARY_REF>
```

## Hard Rules

- Do not write code before Human Alignment approval.
- Do not use D3A Layer or DT Domain registries.
- Choose general components only from the effective registry: repo default `../idc-workflow/references/registries/general-components.yaml`, or replaced wholesale by `team-config.yaml.general.components` when non-empty (never merge).
- Choose test domains only from the effective registry: repo default `../idc-workflow/references/registries/general-test-domains.yaml`, or replaced wholesale by `team-config.yaml.general.test_domains` when non-empty (never merge).
- Every execution unit code change must be `<= 500 LOC`.
- Completion requires tool evidence, not model confidence.
- Keep enterprise details as placeholders outside the confidential environment.
