# Execution Authorization Gate

This gate prevents a correct IDC route from being followed by direct main-agent
implementation.

```text
Human Alignment approved
  -> Planner creates execution unit
  -> Capability Selector returns READY
  -> Knowledge Load Plan returns READY for the same execution unit
  -> resolve Domain execution Skill
  -> Technical Plan Confirmation (AskUserTool, framework floor)
  -> create Delegation Contract
  -> Execution Authorization Gate
  -> dispatch subagent / agent team / official dynamic workflow
  -> executor loads Domain execution Skill
  -> executor may call selected atomic adapters
  -> execution receipt
  -> Evidence / Completion Gate
```

## Technical Plan Confirmation

Between Planner and Execution Authorization / dispatch, the main agent must run
a Technical Plan Confirmation through `AskUserTool`. This is a narrow technical
confirmation only; it must not re-open task direction or scope. If
`AskUserTool` is unavailable, return `BLOCKED_NEEDS_ASK_USER_TOOL`.

It confirms exactly three artifacts:

1. 计划件本体：`general-plan.yaml` 或 `d3a-plan.yaml`（execution units /
   coding layers / DT mapping / dependency DAG）。
2. API Contract：当 Contract Gate 标记 required 时必须一并确认；D3A 的 freeze
   语义是「确认后冻结」——先经 Technical Plan Confirmation，再 freeze。
3. DT 设计：`selected_dt_domains` 与 RED / GREEN plan。

Plan artifacts are mandatory on disk: `technical_plan_confirmation.confirmation_ref`
must point to a real file conforming to `references/schemas/general-plan.schema.yaml`
or `references/schemas/d3a-plan.schema.yaml`. `authorize_execution.rb` rejects a
missing file, so an on-disk plan is a hard precondition of every authorization.

This gate is a framework floor: `technical_plan_confirmation.required` is always
`true` for d3a (`trigger_reason: d3a_fixed_workflow`) and for every lane
(`trigger_reason: lane=fast | lane=lite | lane=complex`). It is not configurable
through team-config; no team config switch may lower it, and it is structurally
the same floor as the unremovable `alignment_check` step.

Scope drift red line: if plan check finds the plan exceeds the approved
Alignment Pack scope (in_scope / out_of_scope / forbidden_changes), the gate
must NOT confirm it in place. Return `NEEDS_RE_ALIGNMENT` and flow back to
Human Alignment (escalation trigger `scope_expansion_required`); the plan is
re-confirmed only after a re-approved Alignment Pack.

Show the developer `references/human-views/plan-confirmation-view.md` before
asking; the question itself goes through `AskUserTool` per
`references/workflows/ask-user-tool-policy.md`.

## Skill precedence

For `selected_domain: general`:

```text
outer protocol: idc-general-coding
inner optional atoms: idc-gc-sop-adapter and other selected adapters
executor: general-coder subagent or coding agent team
```

`idc-general-coding` owns execution-unit boundaries, TDD/evidence flow, and
General completion expectations. `idc-gc-sop-adapter` supplies only atomic
abilities selected for the current stage. They are layered, not competing
alternatives.

For `selected_domain: d3a`, the outer protocol is `idc-d3a-coding`; selected GC
or DT adapters remain inner abilities constrained by the fixed D3A workflow.

## Authorization

Before any repository mutation, run:

```sh
ruby .claude/skills/idc-workflow/scripts/authorize_execution.rb \
  --request <EXECUTION_AUTHORIZATION_REQUEST> \
  --output <EXECUTION_AUTHORIZATION_RESULT>
```

Continue only with `status: AUTHORIZED`. The authorization must name a
subagent, agent team, or official dynamic workflow. `main_agent` is invalid for
all code-changing execution units, including Fast and Lite.

The request must carry `technical_plan_confirmation` with `required: true`,
a `trigger_reason` of `d3a_fixed_workflow` or `lane=fast|lite|complex`, and
`status: confirmed` plus an existing `confirmation_ref` plan file. A missing
block, an unconfirmed status, or a dangling ref returns
`BLOCKED_PLAN_CONFIRMATION_REQUIRED` before any dispatch.

Authorization also reads `knowledge_load_plan_ref` and verifies READY status,
`knowledge_plan_id`, Domain, and execution-unit identity. A path string without
a readable matching plan is not authorization evidence.

The request's `allowed_paths` must cover every artifact destination declared by
the selected atomic skills (their `expected_outputs` entries). If a declared
destination falls outside `allowed_paths`, the gate returns `BLOCKED` with the
path conflict: the planner either widens the authorization explicitly or
re-plans the Context Packet. Executors must never silently re-home a declared
artifact to a different location.

After authorization, the main agent must perform a real dispatch. If dispatch
tools are unavailable, return `BLOCKED_DELEGATION_REQUIRED`; do not implement
directly.

## Completion provenance

Agent Result must include an Execution Receipt containing the authorization ID,
dispatch tool-call ref, executor session ref, loaded Domain execution Skill,
executed atomic skills, changed paths, and evidence refs. Completion Gate rejects
changes without this provenance even if tests pass.

The receipt also carries the authorized `knowledge_plan_id` and a
`knowledge_consumption_result_ref`. Completion requires that result to be
`VERIFIED`.

Main agent may plan, dispatch, summarize evidence, and decide DONE. It may not
write implementation, test, build, verification, or targeted-fix changes.
