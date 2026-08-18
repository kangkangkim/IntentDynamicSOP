---
name: idc-contract-gate
description: Use inside /id-workflow after Domain and Lane are selected to choose the required machine contracts before planning or implementation.
---

# Contract Gate Skill

Select required contracts.

## When To Use

Use after `scenario-router`, `domain-module-router` when applicable, and `lane-resolver`.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/contract-gate.md
.claude/skills/idc-workflow/references/schemas/task-contract.schema.yaml
.claude/skills/idc-workflow/references/schemas/api-contract.schema.yaml
.claude/skills/idc-workflow/references/schemas/verification-contract.schema.yaml
```

## Output

```yaml
contract_gate:
  required_contracts: []
  optional_contracts: []
  missing_contracts: []
  next: Requirement Assessor | Human Alignment
```

## Hard Rules

- API Contract must precede implementation when API or behavior semantics change.
- D3A requires D3A Specification, API Contract, Task Contract, and Verification Contract.
- Do not reduce contract requirements to make a task look fast.
