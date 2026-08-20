# Self Optimization

Self Optimization is a bounded enterprise-adaptation loop:

```text
execution event
  -> adaptation observation
  -> gap classification
  -> recurring-pattern threshold
  -> team-overlay proposal
  -> historical replay / shadow evaluation
  -> Human Alignment promotion decision
  -> promote or reject
```

It reads only the locations and mode materialized from
`team-config.yaml.self_optimization`.

## Gap classes

```text
routing_gap
binding_gap
knowledge_gap
planning_gap
verification_gap
workflow_gap
core_candidate_gap
```

One event cannot rewrite policy. A proposal must cite multiple compatible
events or an explicit human correction, state its affected team scope, and
include rollback information.

## Promotion boundary

- Team-specific findings may propose a change to `team_overlay_ref`.
- Cross-team recurring findings may be labeled `core_candidate_gap`, but only
  Core maintainers can change IDC Core.
- `promotion_requires_human_alignment` must remain true.
- `auto_modify_core` must remain false.
- The active configuration is never mutated by this workflow.

Questions or promotion requests must use AskUserTool. If it is unavailable,
return `BLOCKED_NEEDS_ASK_USER_TOOL`.
