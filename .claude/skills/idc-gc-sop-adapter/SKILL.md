---
name: idc-gc-sop-adapter
description: Use inside the confidential enterprise environment after IDC routing and Human Alignment approval to reuse the internal GC full-suite SOP atomic capabilities without letting GC own IDC Domain, Lane, Contract Gate, or Completion Gate decisions.
---

# GC SOP Adapter Skill

This skill is the confidential-zone adapter for the enterprise GC full-suite SOP.

It does not contain real GC implementation details in this external harness.

```text
IDC Core = dynamic routing framework
Domain Module = scenario-specific constraints such as d3a
GC SOP Adapter = reusable enterprise atomic execution abilities
Original repo skills = bounded adapters such as idc-dt-design and idc-dt-writer
```

## When To Use

Use only when all are true:

- IDC Scenario Router has selected a workflow.
- Domain Module Router has selected `d3a` or another registered module when a domain module is required.
- Human Alignment is approved.
- Required contracts are present.
- The target enterprise repository is available in the confidential zone.
- Capability Selector selected the requested GC atom from the effective registry.
- A dispatched executor already loaded the active Domain execution Skill
  (`idc-general-coding`, `idc-d3a-coding`, or Custom Domain equivalent).

Do not use when:

- the request is still a raw idea.
- clarification is still needed.
- the task has not passed Human Alignment.
- a GC atom would need to choose IDC Domain, Lane, or Completion Gate.
- the external harness would need real enterprise paths, commands, APIs, logs, test names, or SOP internals.

## Atomic Capability Boundary

GC atomic capabilities may provide:

```text
planning assistance
DT design assistance
DT writing assistance
implementation discipline
debugging assistance
review assistance
verification assistance
completion summary assistance
```

GC atomic capabilities may not override:

```text
Domain selection
Lane selection
Contract Gate
Human Alignment
Execution Unit <= 500 LOC
D3A Layer registry
DT Domain registry
Evidence-based Completion
tran_build PASS requirement
```

## Original Repo Skill Adapters

The first GC integration expects three original-repository skills.

Known external adapter names:

```text
.claude/skills/idc-dt-design/SKILL.md
.claude/skills/idc-dt-writer/SKILL.md
.claude/skills/idc-gc-third-skill-placeholder/SKILL.md
```

The third original-repository skill is intentionally a placeholder until the
confidential zone supplies its real name and contract.

## Handoff Shape

Every GC atom must receive a bounded handoff:

```yaml
gc_atomic_handoff:
  selected_domain: d3a | general | <ENTERPRISE_PLACEHOLDER>
  lane_applicability: applicable | not_applicable
  selected_lane: fast | lite | complex | null
  execution_profile: lane_driven | d3a_fixed_workflow | string
  capability_selection_ref: string
  selected_capability_id: string
  selection_reason: string
  approved_alignment_ref: string
  task_contract_ref: string
  verification_contract_ref: string
  api_contract_ref: string
  layer_context_packet_ref: string
  allowed_paths: []
  forbidden_paths: []
  # Each entry declares {kind, path}; every declared path must be covered by
  # allowed_paths. A conflict returns BLOCKED, never silent re-homing.
  expected_outputs:
    - kind: string
      path: string
  evidence_ref_required: true
```

Every GC atom must return:

## Output

```yaml
gc_atomic_result:
  status: SUCCESS | BLOCKED | FAILED
  summary: string
  changed_files: []
  produced_artifact_refs: []
  evidence_refs: []
  unresolved_questions: []
```

## Hard Rules

- Do not let GC choose IDC Domain, Lane, Contract Gate, or Completion Gate.
- Do not use GC SOP Adapter as the outer General Coding executor or as a
  substitute for `idc-general-coding`.
- Do not let main agent invoke GC atoms to perform repository mutations.
- Do not execute unmapped GC atoms.
- Do not silently relocate a declared artifact destination outside authorized
  `allowed_paths`; return `BLOCKED` with the path conflict instead.
- Do not execute every configured GC atom; only run the minimal sufficient set selected for the current stage.
- Do not expose real GC SOP content in this external harness.
- Keep all enterprise paths, commands, logs, test names, and APIs as placeholders outside the confidential zone.

## Source Boundary

Real GC SOP content must stay in the confidential enterprise repository.

Use placeholders in this external harness:

```text
<ENTERPRISE_GC_SOP_REF>
<ENTERPRISE_ORIGINAL_REPO_SKILL_REF>
<ENTERPRISE_REPO_PATH>
<ENTERPRISE_PLACEHOLDER>
```
