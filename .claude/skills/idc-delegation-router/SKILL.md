---
name: idc-delegation-router
description: Use after planning to decide whether IDC should use dynamic workflow, agent team, subagent, or direct bounded execution handoff.
---

# Delegation Router Skill

Select execution delegation shape.

## When To Use

Use after Human Alignment approval and after an execution plan exists.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/delegation-router.md
.claude/skills/idc-workflow/references/schemas/delegation-contract.schema.yaml
```

## Output

```yaml
delegation_decision:
  selection_layer: dynamic_workflow | agent_team | subagent | direct_bounded
  delegation_contract_ref: string
  run_state_ref: string
  expected_return: []
```

## Hard Rules

- Main agent role remains `planning_and_delegation_only`.
- Do not merge full subagent sessions into main context.
- Do not consume full logs or full search results.
- Completion authority remains main agent only.
