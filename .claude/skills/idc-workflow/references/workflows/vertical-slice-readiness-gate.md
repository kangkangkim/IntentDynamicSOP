# Vertical Slice Readiness Gate

This gate is used only when the harness moves into team-config onboarding
and the team is preparing the first real D3A vertical slice.

It does not prove the task is DONE. It only proves the harness has enough real
bindings to start an approved execution loop.

## Entry Condition

Use this gate after:

```text
Domain = d3a
Human Alignment approved
first team-config onboarding vertical slice selected
```

Do not use it in the external non-sensitive repository except with placeholders
or mock examples.

## Required Readiness Checks

All required checks must PASS before `READY_FOR_EXECUTION`:

- `layer_knowledge_bound`
- `dt_knowledge_bound`
- `verification_mapping_bound`
- `repo_context_provider_bound`
- `dt_red_green_build_skill_bound`
- `tran_build_skill_bound`
- `placeholder_hygiene_preserved`

Each check must include an `evidence_ref`.

## Scope Limits

The first real slice should stay small:

```text
max_layers <= 2
max_dt_domains <= 1
max_change_loc_per_execution_unit = 500
```

If the slice needs more scope, return to Human Alignment instead of silently
expanding the plan.

## Evidence Boundaries

Readiness evidence can prove that bindings exist.

Readiness evidence cannot replace:

- RED evidence.
- GREEN evidence.
- `tran_build` PASS evidence.
- Completion Summary evidence.

TR3 DT design, OKL summaries, architecture docs, and repository search results
are knowledge or planning inputs. They are not DONE evidence.

## Blockers

Return `BLOCKED` when any required binding is missing:

- no real layer knowledge for the selected layer.
- no real DT knowledge for the selected DT domain.
- no real Coding Layer -> DT Domain verification mapping.
- no bounded repo context provider with `evidence_ref`.
- no bound DT RED/GREEN build skill (`bindings.dt_build.skill_ref`).
- no bound `tran_build` skill (`bindings.tran_build.skill_ref`).
- placeholder hygiene cannot be proven.

When blocked, use Escalation View and ask only for the missing binding or scope
decision.
