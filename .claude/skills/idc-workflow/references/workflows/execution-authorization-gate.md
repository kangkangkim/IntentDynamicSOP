# Execution Authorization Gate

This gate prevents a correct IDC route from being followed by direct main-agent
implementation.

```text
Human Alignment approved
  -> Planner creates execution unit
  -> Capability Selector returns READY
  -> Knowledge Load Plan returns READY for the same execution unit
  -> resolve Domain execution Skill
  -> create Delegation Contract
  -> Execution Authorization Gate
  -> dispatch subagent / agent team / official dynamic workflow
  -> executor loads Domain execution Skill
  -> executor may call selected atomic adapters
  -> execution receipt
  -> Evidence / Completion Gate
```

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
