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

When the host supports PreToolUse hooks (e.g. Claude Code), the hook `.claude/hooks/verify_plan_confirmation_ask.py` machine-enforces this step: it verifies a real AskUserQuestion interaction referencing the plan file exists in the session transcript before allowing the authorize_execution.py call. Self-attested `status: confirmed` without a real interaction is denied.

It confirms exactly three artifacts:

1. 计划件本体：`general-plan.yaml` 或 `d3a-plan.yaml`（execution units /
   coding layers / DT mapping / dependency DAG）。
2. API Contract：当 Contract Gate 标记 required 时必须一并确认；D3A 的 freeze
   语义是「确认后冻结」——先经 Technical Plan Confirmation，再 freeze。
3. DT 设计：`selected_dt_domains` 与 RED / GREEN plan。

Plan artifacts are mandatory on disk: `technical_plan_confirmation.confirmation_ref`
must point to a real file conforming to `references/schemas/general-plan.schema.yaml`
or `references/schemas/d3a-plan.schema.yaml`. `authorize_execution.py` rejects a
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
python3 .claude/skills/idc-workflow/scripts/authorize_execution.py \
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

### Capability Selection — mandatory pre-authorization artifact

The request must carry `capability_selection_ref` pointing to the READY
Capability Selection artifact produced by
`scripts/select_capabilities.py` for this execution unit. The script
verifies:

1. The file exists on disk at the declared path.
2. Its `status` field equals `READY`.
3. Its `execution_unit` matches the current authorization request's
   `execution_unit_id`.
4. Its `selected_skills` list is non-empty.
5. For `orchestration.mode: ordered` lanes, the `stage_order` in the artifact
   covers every configured stage without gaps or reordering.
6. For ordered execution, `ordered_execution` exactly projects the selected
   Skill identities and order. The gate derives `authorized_stage_skills` and
   `selected_atomic_skill_refs` from it. For autonomous execution, it derives
   the same authorization fields directly from `selected`.

A missing field, a dangling ref, a non-READY status, an execution-unit
mismatch, an empty `selected_skills`, or a broken stage order returns
`BLOCKED_CAPABILITY_SELECTION_REQUIRED` — the gate never proceeds to dispatch
until a valid artifact exists. This check is not configurable through
team-config and cannot be disabled.

`selected_atomic_skill_refs` in an authorization request is only an optional
consistency assertion. If supplied, it must exactly equal the derived list,
including duplicates and order. A caller-supplied subset, superset, or
reordered list is blocked. Fast, Lite, and Complex use this same rule when
configured as ordered.

The main agent must run Capability Selector via
`scripts/select_capabilities.py` and persist the output artifact **before**
calling `authorize_execution.py`. Constructing an authorization request that
references a non-existent or hand-authored `capability_selection_ref` is
treated as a fabricated artifact and rejected identically.

### Effective config freshness — mandatory SHA check

`authorize_execution.py` reads `.idc/effective-team-config.yaml` and compares
its `source_sha256` against the SHA256 of the current `team-config.yaml` on
disk. A mismatch means `prepare_runtime.py` was not run after the config
changed, so the Capability Selector ran against stale policy.

- Mismatch → `BLOCKED_STALE_EFFECTIVE_CONFIG`; re-run `prepare_runtime.py`
  and verify `status: READY` before retrying authorization.
- Missing effective config → same error; `prepare_runtime.py` must produce it
  first.

This check is machine-enforced inside the script, not model-discretionary. No
team-config switch can disable it.

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

Agent Result must include an Execution Receipt containing:

- `authorization_id`
- `dispatch_tool_call_ref`
- `executor_session_ref`
- `loaded_domain_execution_skill` (e.g. `idc-general-coding`)
- `capability_selection_ref` — the same artifact verified at authorization
- `executed_stage_skills` — ordered list of `{step_id, stage, capability_id,
  skill_ref, execution_order, status, evidence_refs}` entries recording exactly
  which Skills ran; must be non-empty, each status must be `completed` or
  `succeeded`, and each item must carry evidence
- `executed_atomic_skills`
- `changed_paths`
- `evidence_refs`

Completion Gate cross-checks `executed_stage_skills` against the
authorization's derived `authorized_stage_skills` and re-reads the same
`capability_selection_ref`. Missing, extra, failed, or reordered Skills return
`NEEDS_EXECUTION_EVIDENCE` — missing execution is not silently forgiven even
if tests pass. Enforcement is identical for ordered Fast, Lite, and Complex.

The receipt also carries the authorized `knowledge_plan_id` and a
`knowledge_consumption_result_ref`. Completion requires that result to be
`VERIFIED`.

Main agent may plan, dispatch, summarize evidence, and decide DONE. It may not
write implementation, test, build, verification, or targeted-fix changes.
