---
name: idc-team-config
description: Validate or diagnose the team-owned team-config.yaml and materialize its effective IDC runtime; use for onboarding, Domain Pack selection, bindings, Lane policy, migration preview, or runtime lifecycle diagnosis.
---

# IDC Team Config

## When To Use

Use this skill when adopting IDC, changing a Domain or binding, previewing a v1
migration, or diagnosing `NEEDS_TEAM_CONFIG`, authorization drift, dispatch, or
completion failures.

## Hard Rules

- `team-config.yaml` is the only team-authored configuration source.
- Generated `.idc/` files are runtime state and evidence, never configuration.
- Official or installed Domain Packs are executable module assets, not a second
  team configuration. A self-developed Custom Domain still owns and maintains
  its Pack, workflow, policy, registries, knowledge, and completion assets.
- Do not edit shared registries or generated state to bypass validation.
- Do not treat hashes as signatures or executor-controlled records as host
  attestations.
- Completion requires the authorized graph, host-owned dispatch/predicate
  records, verified knowledge receipt, and the real completion verifier.
- The top-level pre-alignment section is:
  ```yaml
alignment:
  ```
  Router, approval, contract, and completion gates cannot be configured; an
  omitted section uses the framework default alignment.

## Focused references

- For v2 authoring, General/Custom Packs, ordered Lane policy, bindings,
  extensions, D3A enablement, or v1 preview migration, read
  [Team Config v2](references/team-config-v2.md).
- For compile/authorize/dispatch/replay/completion order, protected state, drift,
  idempotency, or crash recovery, read
  [Runtime lifecycle](references/runtime-lifecycle.md).

Normal IDC entry runs the bootstrap automatically:

```sh
python3 .claude/skills/idc-team-config/scripts/prepare_runtime.py
```

Continue only when `runtime_preflight.status: READY`. For diagnosis or CI, use
the exact scripts and contracts linked by the focused references. If any gate
fails, return its bounded status and diagnostics; never synthesize READY or
DONE from prose confidence.

## Output

Write per-run evidence under `.idc/runs/<task-id>/attempt-<n>/`, including one
`capability-selection-<execution-unit>.yaml` per execution unit. Effective config
is derived runtime state; it never replaces `team-config.yaml`.
