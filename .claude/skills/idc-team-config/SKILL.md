---
name: idc-team-config
description: Validate and resolve the private team-config.yaml into read-only effective IDC runtime configuration; use during team adoption, readiness checks, custom-domain registration, or adapter-binding diagnosis.
---

# IDC Team Config

Use this skill when adopting IDC into a team environment or diagnosing a
configuration-dependent route.

`team-config.yaml` is the only team-authored configuration source. Do not ask a
team to edit shared registries, Domain Module files, or generated `.idc/` files.

## When To Use

Use during team adoption, before the first configured run, after a binding or
Domain change, or when routing returns `NEEDS_TEAM_CONFIG`.

`idc-workflow` invokes this Skill's runtime preflight automatically on every
run. Teams do not manually maintain `.idc/effective-team-config.yaml`.

## Required flow

1. Read `../idc-workflow/references/schemas/team-config.schema.yaml`.
2. Read `../idc-workflow/references/workflows/team-config-resolver.md`.
3. Validate the filled configuration:

   ```sh
   ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb --config team-config.yaml --check
   ```

4. Materialize the read-only effective configuration when validation passes:

   ```sh
   ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
     --config team-config.yaml \
     --output .idc/effective-team-config.yaml
   ```

5. Route IDC from the effective configuration, never by combining defaults and
   team overrides ad hoc.

Normal workflow entry uses the no-argument bootstrap below; the explicit
Resolver commands above are for diagnosis and CI:

```sh
ruby .claude/skills/idc-team-config/scripts/prepare_runtime.rb
```

The preflight includes a three-reference `bootstrap_load_plan`. After Domain,
Lane, or phase changes, generate the next minimal plan instead of reading the
effective registry directly. The decision phase may omit `--lane` (the lane is
not resolved yet); from `planning` onward `--lane` is required:

```sh
ruby .claude/skills/idc-team-config/scripts/plan_context.rb \
  --effective .idc/effective-team-config.yaml \
  --phase decision \
  --domain general
```

The optional top-level `alignment` section configures the pre-alignment
intent-processing pipeline and mirrors the lane orchestration shape:

```yaml
alignment:
  bindings: # capability key -> {skill_ref: .claude/skills/idc-*/SKILL.md}
  orchestration:
    mode: ordered
    steps: # id / stage / skill_ids / trigger_signals
```

The Resolver validates it with bounded field-level errors and materializes the
resolved pipeline into the effective config. A missing section (or missing
`bindings` / `orchestration`) falls back to the framework default five-step
chain with no other output difference. Scenario Router, Contract Gate, Human
Alignment approval, and completion ownership cannot be configured through it.

For each planned execution unit, run Capability Selector with a demand contract:

```sh
ruby .claude/skills/idc-team-config/scripts/select_capabilities.rb \
  --effective .idc/effective-team-config.yaml \
  --demand <CAPABILITY_DEMAND_YAML> \
  --output .idc/runs/<task-id>/attempt-<n>/capability-selection-<execution-unit>.yaml
```

Build a Knowledge Load Plan for the same execution unit:

```sh
ruby .claude/skills/idc-team-config/scripts/plan_knowledge.rb \
  --effective .idc/effective-team-config.yaml \
  --demand <KNOWLEDGE_DEMAND_YAML> \
  --output .idc/runs/<task-id>/attempt-<n>/knowledge-load-plan-<execution-unit>.yaml
```

Execution context planning requires both READY plans. After execution, verify
the executor's knowledge receipt before Completion:

```sh
ruby .claude/skills/idc-team-config/scripts/verify_knowledge_consumption.rb \
  --plan .idc/runs/<task-id>/attempt-<n>/knowledge-load-plan-<execution-unit>.yaml \
  --receipt <KNOWLEDGE_CONSUMPTION_RECEIPT>
```

## Output

```yaml
team_config_result:
  status: READY | NEEDS_TEAM_CONFIG
  effective_config_ref: .idc/effective-team-config.yaml
  available_capability_count: integer
  errors: []
  warnings: []
```

## Hard Rules

- Reject `command`, `build_command`, `run_command`, and `pass_condition` keys.
- Resolve and validate local Skill and knowledge refs against `team.repo_path`
  with IDC Core fallback; preserve explicit URI refs.
- Commands and pass/fail parsing live inside bound enterprise skills.
- Non-empty team registries replace the corresponding defaults wholesale.
- A custom Domain is registered from `domain.custom`; do not edit the shared
  Domain registry during adoption.
- `adapter_extensions` may add team capabilities but cannot override Domain,
  Lane, Contract Gate, Human Alignment, or Completion Gate ownership.
- Every Lane profile may configure its own Skill allowlist, denylist, required
  set, and stage orchestration. Resolver must reject unresolved references;
  Selector must apply the profile and emit execution order.
- `ordered` Lane orchestration never falls back silently. A missing stage mapping
  returns `NEEDS_ORCHESTRATION_MAPPING`.
- Generated `.idc/effective-team-config.yaml` is state, not a configuration
  source and not completion evidence.
- Runtime bootstrap always regenerates effective config atomically and records
  the source YAML SHA-256; never reuse stale generated state.
- Preflight dry-runs every configured Lane step and required Skill through the
  real Capability Selector. Return `NEEDS_TEAM_CONFIG` if selection or order
  differs from the YAML policy.
- Context Load Plan is the runtime loading authority. Read only
  `required_refs`; do not preload all available capabilities or schemas.
- Knowledge Load Plan is bound to one execution unit. Authorization requires
  it READY; Completion requires a VERIFIED consumption receipt with no
  unplanned Layer, component, or test-domain refs.
- Per-execution-unit artifacts must use per-unit filenames such as
  `.idc/runs/<task-id>/attempt-<n>/capability-selection-<execution-unit>.yaml`;
  a shared single-slot name gets overwritten by the next execution unit and
  breaks Delegation Contract audits. All per-run products are collected under
  `.idc/runs/<task-id>/attempt-<n>/`; a re-run increments the attempt
  subdirectory to keep versions and never silently overwrites.
  `.idc/effective-team-config.yaml` is the only exception: it is global,
  atomically regenerated, and source-sha256 stamped.
- Self-optimization may observe or propose; it must never mutate IDC Core or
  promote an overlay without Human Alignment.
- Validate `alignment` with bounded field-level errors (`alignment.*` paths),
  never with a whole-file rejection. A step `skill_id` missing from
  `alignment.bindings` returns `NEEDS_TEAM_CONFIG`; it must not silently drop
  the step.
- `alignment.orchestration.mode` is always `ordered`. A missing stage mapping
  returns `NEEDS_ORCHESTRATION_MAPPING`, the same bounded rule as Lane
  orchestration; there is no silent fallback.
- The `alignment_check` step (Human Alignment gate) cannot be removed; teams
  may rebind its `skill_ref` only, and the rebound ref must keep the
  `.claude/skills/idc-*/SKILL.md` shape.
- `raw_idea` and `critical_gaps_remain` form the framework signal floor: each
  must stay covered by at least one step's `trigger_signals`.
- A missing `alignment` section (or missing `bindings` / `orchestration`)
  falls back to the framework default five-step chain and materializes it in
  the effective config; the section configures intent-processing steps only
  and never Domain, Lane, Contract Gate, or Completion ownership.

If validation fails, return `NEEDS_TEAM_CONFIG` with bounded field-level errors.
