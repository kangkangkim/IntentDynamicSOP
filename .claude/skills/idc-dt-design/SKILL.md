---
name: idc-dt-design
description: Use through idc-gc-sop-adapter when a D3A or registered domain task needs DT design planning before DT writing; this external harness only defines the non-sensitive adapter boundary for the original enterprise repo skill.
---

# DT Design Skill Adapter

This adapter represents the original enterprise repository skill used to design
DT.

It does not contain real enterprise DT design rules.

## When To Use

Use only after:

- IDC Human Alignment is approved.
- `idc-gc-sop-adapter` has selected this atomic capability.
- A task contract and verification contract exist.
- For D3A, selected DT domains come only from the DT Domain registry.
- Required repository context is referenced by `evidence_ref`.

Do not use when:

- DT design is already fully specified and only writing is needed.
- the selected DT domain is unknown.
- the task is asking for implementation code.
- using this adapter would require guessing enterprise DT patterns.

## Input

```yaml
dt_design_input:
  selected_domain: d3a | general | <ENTERPRISE_PLACEHOLDER>
  selected_dt_domains: []
  behavior_contract_ref: string
  api_contract_ref: string
  verification_contract_ref: string
  repo_context_refs: []
  constraints_ref: string
```

## Output

```yaml
dt_design_output:
  status: READY_FOR_DT_WRITER | NEED_CLARIFICATION | BLOCKED
  dt_design_ref: string
  selected_dt_domains: []
  red_evidence_plan: []
  green_evidence_plan: []
  blocker_summary: string
  evidence_refs: []
```

## Hard Rules

- DT design is not RED evidence.
- DT design is not GREEN evidence.
- DT design must not replace `verification_contract`.
- D3A DT domains must stay within the registered DT Domain registry.
- Real enterprise DT design rules must remain behind `<ENTERPRISE_ORIGINAL_REPO_SKILL_REF>`.
