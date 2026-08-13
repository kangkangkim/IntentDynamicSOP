---
name: general-coding
description: Use when a coding task does not match a specialized domain module and should run through the General Coding workflow with task, verification, TDD, and evidence gates.
---

# General Coding Skill

Use this skill when Domain Module Router selects `general`.

## Flow

```text
intent-discovery if raw_idea
  -> intent-grilling if needed
  -> intent-alignment
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

## Hard Rules

- Do not write code before Human Alignment approval.
- Do not use D3A Layer or DT Domain registries.
- Choose general components only from `registries/general-components.yaml`.
- Choose test domains only from `registries/general-test-domains.yaml`.
- Every execution unit code change must be `<= 500 LOC`.
- Completion requires tool evidence, not model confidence.
- Keep enterprise details as placeholders outside the confidential environment.
