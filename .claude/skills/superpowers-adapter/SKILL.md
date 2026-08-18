---
name: superpowers-adapter
description: Use after IDC Human Alignment approval when the task should execute with a Superpowers-inspired engineering loop for planning, TDD, subagent development, debugging, review, verification, and branch finishing while preserving IDC domain, contract, and evidence gates.
---

# Superpowers Adapter Skill

This skill adapts the public Superpowers engineering workflow into IDC.

It is an adapter layer, not the outer workflow owner.

```text
IDC Harness = control plane
Superpowers Adapter = execution discipline
Domain Module = enterprise domain constraints
```

## When To Use

Use only when all are true:

- Human Alignment is approved.
- Domain and Lane are already selected by IDC.
- Required IDC contracts exist.
- Execution units or Layer Context Packets are bounded.
- Completion gate is owned by IDC.

Do not use when:

- the request is still a raw idea.
- Clarification questions remain.
- Human Alignment is not approved.
- Domain / Lane / Contract Gate has not run.
- the task requires guessing enterprise API, path, command, log, or architecture facts.

## Adapted Superpowers Flow

The adapter may use these Superpowers-inspired stages:

```text
writing-plans
  -> executing-plans
  -> test-driven-development
  -> subagent-driven-development
  -> systematic-debugging if failure
  -> requesting-code-review
  -> receiving-code-review
  -> verification-before-completion
  -> finishing-a-development-branch
```

`brainstorming` remains pre-alignment and is routed through:

```text
.claude/skills/brainstorming/SKILL.md
.claude/skills/idc-intent-discovery/SKILL.md
```

## IDC Overrides

IDC rules override this adapter whenever they conflict.

- IDC Domain Module Router owns Domain selection.
- IDC Lane Resolver owns execution intensity.
- IDC Contract Gate owns required contracts.
- D3A Layer and DT Domain registries cannot be changed here.
- API Contract must be frozen before implementation.
- Every execution unit code change must be `<= 500 LOC`.
- D3A still requires DT RED evidence, all required DT GREEN evidence, and `tran_build PASS`.
- General Coding still requires its selected test/build evidence.
- Superpowers-style verification cannot replace IDC Completion Gate.
- OKL, docs, TR3 DT design, and repository search are knowledge inputs, not DONE evidence.

## Stage Mapping

### writing-plans

Use only after IDC Alignment approval.

Inputs:

```text
approved_alignment_ref
task_contract
verification_contract
api_contract if required
domain module constraints
lane constraints
```

Output:

```text
execution_plan_ref
execution_unit_refs
```

### executing-plans

Execute only bounded units from the approved plan.

For D3A:

```text
one Layer Context Packet per selected Coding Layer
max_layers_per_packet = 1
```

For General:

```text
selected_components must come from General component registry
selected_test_domains must come from General test registry
```

### test-driven-development

Use RED/GREEN when the Lane or Domain requires it.

For D3A, RED/GREEN is required by the D3A completion gate.

### subagent-driven-development

Use only through IDC Delegation Contract.

The main agent remains `planning_and_delegation_only`.

### systematic-debugging

Use when test/build evidence fails.

Debugging output must be:

```text
failure_summary
suspected_scope
targeted_fix_plan
evidence_ref
```

Do not paste full logs into main context.

### requesting-code-review / receiving-code-review

Use after GREEN evidence and before final completion when Lane or risk calls for review.

Review can find bugs or risks, but it does not mark DONE.

### verification-before-completion

Require tool evidence before completion.

For D3A:

```text
red_evidence_refs
green_evidence_refs for all required DT domains
tran_build_pass_ref
completion_summary_ref
```

For General:

```text
required test/build evidence refs
completion_summary_ref
```

### finishing-a-development-branch

Use only after IDC Completion Gate is satisfied.

It may prepare cleanup, summary, branch handoff, or PR material.

Do not mark completion by branch cleanliness alone.

## Source Boundary

This adapter is inspired by the public `obra/superpowers` skills list and does
not copy upstream prompts verbatim.

Source:

```text
https://github.com/obra/superpowers
https://github.com/obra/superpowers/tree/main/skills
```

License:

```text
MIT License
Copyright (c) 2025 Jesse Vincent
```
