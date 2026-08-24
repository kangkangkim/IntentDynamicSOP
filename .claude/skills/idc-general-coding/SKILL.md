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

This is the outer Domain execution protocol for every `general_execution` unit.
The dispatched general-coder subagent or coding agent team must load it. GC SOP
adapters are optional inner atomic abilities selected by Capability Selector;
they do not compete with or replace this Skill.

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

## Executor startup — capability selection verification

Before writing any code, the dispatched executor must:

1. Read the `capability_selection_ref` from the Delegation Contract.
2. Verify the artifact exists on disk, `status: READY`, and
   `execution_unit` matches.
3. Extract `stage_order` and `selected_skills` — these define the exact
   ordered sequence the executor must follow.
4. If the artifact is missing, non-READY, or mismatched, return
   `BLOCKED_CAPABILITY_SELECTION_REQUIRED` and stop; do not proceed to
   implementation.

The executor runs each stage by invoking only the skills listed in
`selected_skills` for that stage, in the declared order. Skipping a
configured stage or substituting an unlisted skill is a protocol violation.
Each completed stage is recorded in `executed_stage_skills` for the
Execution Receipt.

## Hard Rules

- Do not write code before Human Alignment approval.
- Main agent must never execute this Skill as the repository mutation owner.
  Require Execution Authorization and a real general-coder subagent / coding
  agent-team dispatch, including Fast and Lite.
- Return an Execution Receipt with authorization ID, dispatch tool-call ref,
  executor session ref, `capability_selection_ref`, `executed_stage_skills`
  (ordered list of `{stage, skill_id, status}`), changed paths, and evidence
  refs. A receipt missing `capability_selection_ref` or `executed_stage_skills`
  is incomplete and will be rejected by Completion Gate.
- Do not use D3A Layer or DT Domain registries.
- Choose general components only from the effective registry: repo default `../idc-workflow/references/registries/general-components.yaml`, or replaced wholesale by `team-config.yaml.general.components` when non-empty (never merge).
- Choose test domains only from the effective registry: repo default `../idc-workflow/references/registries/general-test-domains.yaml`, or replaced wholesale by `team-config.yaml.general.test_domains` when non-empty (never merge).
- Every execution unit code change must be `<= 500 LOC`.
- Completion requires tool evidence, not model confidence.
- Keep enterprise details as placeholders outside team-config onboarding.
