---
name: idc-self-optimization
description: Observe IDC enterprise-adoption friction, classify recurring routing/binding/knowledge/planning/verification gaps, and produce replay-tested team-overlay proposals without automatically modifying IDC Core or active team configuration.
---

# IDC Self Optimization

Use only when `.idc/effective-team-config.yaml` enables `observe` or
`propose_only` mode.

Read:

```text
../idc-workflow/references/workflows/self-optimization.md
../idc-workflow/references/schemas/adaptation-event.schema.yaml
../idc-workflow/references/schemas/optimization-proposal.schema.yaml
```

## When To Use

Use after real IDC runs produce routing corrections, unused or missing Skill
bindings, knowledge gaps, planning corrections, or verification failures.

## Modes

- `observe`: append bounded adaptation events to the configured event store.
- `propose_only`: observe, classify recurring gaps, generate a team-overlay
  proposal, and evaluate it against configured replay cases.

## Hard Rules

- Never modify `team-config.yaml`, IDC Core, active registries, contracts, or
  completion gates automatically.
- Never infer enterprise facts from repeated model guesses.
- Redact private code, logs, paths, and APIs from portable event summaries.
- Promotion always requires Human Alignment.
- A proposal that fails replay, widens scope, weakens evidence requirements, or
  changes D3A fixed invariants must be rejected.

## Output

```yaml
self_optimization_result:
  status: OBSERVED | PROPOSED | REJECTED | BLOCKED
  adaptation_event_refs: []
  proposal_ref: string | null
  replay_status: PASS | FAIL | NOT_RUN
  promotion_status: pending | approved | rejected
```
