---
name: idc-workflow
description: Use when the user asks to run, try, trigger, or apply the Intent Dynamic Code / IDC workflow; process a one-line request or TR3 design document; generate an Alignment Pack; classify Domain Module and Lane; or continue an approved Alignment Pack through the automated closure loop with evidence gates.
---

# IDC Workflow

Use this skill to run the Intent Dynamic Code workflow.

The user-facing entry is this skill itself:

```text
$idc-workflow
```

Users may invoke it explicitly with `$idc-workflow`, or describe an IDC task in
natural language and let skill matching select it. There is no `.claude/commands`
alias layer. This skill is the orchestration implementation, and all executable
IDC capabilities must live in `idc-*` skills.

This is the orchestration skill. It delegates reusable work to selected
`idc-*` skills.
Router, gate, lane, provider, completion, resume, and evidence behavior remains
under `references/` as passive policy/configuration. Supporting resources are
progressively disclosed through the machine-generated Context Load Plan; never
load every IDC skill or reference up front.

Repository-native rules in `CLAUDE.md` remain authoritative and are supplied by
the host environment; they are not duplicated into each Context Load Plan.

## When To Use

Use this skill when an IDC request needs to classify an input, produce an
Alignment Pack, route to IDC pre-alignment skills, or continue an approved pack
through General Coding or D3A Coding evidence gates.

Do not use it as a lower-level adapter. For external SOP reuse or domain build
steps, route through `idc-skill-adapter-router` and the specific `idc-*` adapter
or execution skill.

## Trigger examples

- "$idc-workflow <task>"
- "用 IDC workflow 处理这个 TR3。"
- "按这套 SOP 跑一下。"
- "生成 Alignment Pack。"
- "我 approve 了，继续自动闭环。"
- "中断了，继续上次任务。"
- "从 checkpoint 恢复。"
- "判断这个任务是 D3A 还是 General，应该走哪个 Lane。"

## Skill-level maturity routing

This skill must route rough requests before Domain execution.

Treat these as `raw_idea` only when the user intent is actually vague, even when the user mentions General Coding:

```text
rough
vague
sketchy
early idea
大概想做
先试试
不完整想法
还没想清楚
```

If a General Coding request is rough, run `idc-intent-discovery` first.

If a short request already has goal, behavior, and acceptance signals, do not use Brainstorming; continue to Clarification / Alignment.

Do not let `Domain = general` skip Brainstorming when the input is still rough.

## Required behavior

Mandatory runtime bootstrap, before reading or routing the user request:

```sh
ruby .claude/skills/idc-team-config/scripts/prepare_runtime.rb
```

- Run this on every `idc-workflow` invocation. It atomically regenerates
  `.idc/effective-team-config.yaml` from the current `team-config.yaml`, so a
  changed binding or Lane policy cannot leave stale runtime state.
- Continue only when `runtime_preflight.status: READY`.
- Read only `runtime_preflight.bootstrap_load_plan.required_refs` during
  bootstrap. Do not inspect the full registry or unrelated Skill bodies.
- If config is absent or invalid, return `NEEDS_TEAM_CONFIG` with the bounded
  Resolver errors. Do not route from the template, an old effective file, or
  shared defaults.
- For runtime, the template is never executed; it is only the source for creating the
  team-owned `team-config.yaml`.
- The team only authors `team-config.yaml`; bootstrap and generated files are
  framework-owned.

Default mode:

```text
references/workflows/input-adapter.md
  -> Intent Maturity Router
  -> references/workflows/scenario-router.md
  -> idc-intent-discovery if raw_idea
  -> references/workflows/domain-module-router.md if DOMAIN_MODULE
  -> apply module lane applicability policy (D3A => not_applicable)
  -> references/workflows/lane-resolver.md only for lane-applicable dynamic modules / scenarios
  -> references/workflows/contract-gate.md
  -> idc-intent-alignment as Human Alignment Check
  -> idc-brainstorming if alternatives are needed
  -> idc-intent-grilling if critical gaps remain
  -> idc-intent-grilling-with-docs if clarification must update docs
  -> Alignment Pack
  -> idc-intent-alignment for Human Alignment approval
  -> references/human-views/
```

After the user approves:

```text
references/workflows/automated-closure-loop.md
  -> Planner
  -> references/workflows/execution-unit-policy.md
  -> references/workflows/progressive-constraint-loading.md
  -> references/workflows/capability-selector.md
  -> references/workflows/delegation-router.md
  -> references/workflows/execution-authorization-gate.md
  -> dispatch agent team / subagent
  -> executor loads idc-general-coding or idc-d3a-coding as Domain execution protocol
  -> executor uses idc-superpowers-adapter / idc-gc-sop-adapter only when selected as inner abilities
  -> .claude/skills/idc-skill-adapter-router/SKILL.md for selected lower-level adapters
  -> Progressive Constraint Loading
  -> references/workflows/knowledge-gate.md
  -> references/workflows/provider-selection-matrix.md
  -> references/workflows/repo-context-providers.md
  -> Agent Team / Subagent Execution
  -> references/workflows/tdd-state-machine.md if TDD is required
  -> references/workflows/lane-completion.md
  -> Evidence Gate
  -> DONE / Targeted Fix / Re-plan
```

## Human View vs Machine Contract

Do not show users raw YAML as the primary interface.

Use Human View for interaction:

```text
references/human-views/alignment-view.md
references/human-views/completion-view.md
references/human-views/escalation-view.md
```

Keep Machine Contract internally:

```text
references/schemas/alignment-pack.schema.yaml
references/schemas/escalation-policy.schema.yaml
references/schemas/verification-contract.schema.yaml
```

Default user-facing output before approval is Alignment View, not raw `alignment-pack.yaml`.

## Progressive context loading

After bootstrap, generate a plan whenever the phase, Domain, Lane, or relevant
signals change. For lane-applicable routes, pass `--lane`; omit it for D3A.

```sh
ruby .claude/skills/idc-team-config/scripts/plan_context.rb \
  --effective .idc/effective-team-config.yaml \
  --phase decision \
  --domain general \
  --lane fast
```

Supported phases are `bootstrap`, `decision`, `planning`, `execution`,
`completion`, and `resume`. Add only observed signals with repeated `--signal`:

```text
raw_idea
clarification_required
docs_clarification_required
user_question_required
tr3_input
tdd_required
repo_context_required
vertical_slice_readiness_required
```

Continue only when `context_load_plan.status: READY`, then read exactly its
`required_refs`. Do not preload refs for later phases. Schema:
`references/schemas/context-load-plan.schema.yaml`.

For execution, first persist the READY Capability Selector result, then bind it
to the load plan:

```sh
ruby .claude/skills/idc-team-config/scripts/plan_context.rb \
  --effective .idc/effective-team-config.yaml \
  --phase execution \
  --domain general \
  --lane lite \
  --selection .idc/capability-selection.yaml
```

Execution planning rejects a missing or non-READY selection. Only the Domain
execution protocol, shared execution gates, and selected `skill_ref` values are
loaded. Unselected GC, DT, Superpowers, and team extension Skills remain out of
context. Custom Domains load their configured planner, workflow, or completion
Skill only in the matching phase.

## Hard Rules

- Do not write implementation code before Human Alignment approval.
- Follow `CONTEXT_ENGINEERING.md`: load stage-specific context, summarize long findings, and keep DONE evidence separate from knowledge findings.
- Main agent role is `planning_and_delegation_only`: select IDC workflow route, decide whether official dynamic workflow is needed, create Delegation Contract, dispatch agent team / subagent, then summarize returned evidence.
- Delegation selection order is mandatory: IDC workflow route -> official dynamic workflow if needed -> agent team -> subagent.
- IDC workflow route is event-triggered state routing; official dynamic workflow is only for scripted, repeatable, large-scale fan-out orchestration.
- Use agent team only when multiple subagents need communication, handoff, shared intermediate artifacts, review, or merge.
- Main agent must not mutate repository code, tests, build files, verification artifacts, or targeted fixes in any Lane. All such work requires Execution Authorization and a real subagent / agent-team / dynamic-workflow dispatch.
- For General Domain, `idc-general-coding` is the outer execution protocol loaded by the executor. `idc-gc-sop-adapter` and other adapters are inner atomic abilities selected by Capability Selector; they never replace the Domain execution Skill.
- If delegation tools are unavailable, return `BLOCKED_DELEGATION_REQUIRED`; never fall back to direct main-agent implementation.
- Interruption resume must use `runtime_state` checkpoint refs, not main agent memory.
- After resuming an interrupted execution, re-run verification unless tool evidence proves the interrupted step completed.
- Keep `idc-workflow` as orchestration; reusable pre-alignment, domain execution, and adapter behavior lives in skills.
- Do not add `.claude/commands` aliases; `idc-workflow` is the user-facing orchestration entry.
- Keep router, gate, lane, provider, completion, resume, and evidence behavior in `references/`; do not promote them to standalone skills unless they need independent invocation.
- Do not skillize passive assets such as schemas, registries, examples, human-view templates, lane definitions, evidence files, and knowledge templates;沉淀 them as references or assets according to the official skill directory shape.
- Superpowers Adapter may provide the inner engineering loop after approval, but IDC owns Domain, Lane, Contract Gate, and Completion Gate.
- GC SOP Adapter may reuse confidential enterprise atomic abilities after approval, but must go through Skill Adapter Router and cannot invent original repository skill details.
- Skill Adapter Router must select GC / DT / Superpowers adapters from `references/registries/skill-adapters.yaml`; adapter names are not triggers by themselves.
- For Lane-applicable routes, Capability Selector must execute `team-config.yaml.lane.profiles.<lane>` Skill policy and orchestration. Never silently ignore configured allow/deny/required lists or ordered steps.
- Team-specific paths, knowledge refs, and internal skill refs (including DT design / writing / build skills) must be supplied through `team-config.yaml`; real build commands live inside the bound skill, never in the config. Use `team-config.yaml.template` as the fill-parameters entrypoint.
- Registries (`dt-domains.yaml`, `general-components.yaml`, `general-test-domains.yaml`) are repo read-only defaults; a non-empty team-config list (`domain.d3a.dt_domains`, `general.components`, `general.test_domains`) replaces the registry wholesale — never merge sources.
- Original repository DT skills are represented as adapters: `idc-dt-design` for DT design, `idc-dt-writer` for DT writing, and `idc-gc-third-skill-placeholder` until the third skill is named in the confidential zone.
- Use `upstream-superpowers-brainstorming` as the `raw_idea` baseline, then apply `idc-brainstorming-overlay` before handoff to `idc-intent-grilling`.
- Skip Discovery Provider for TR3 unless the TR3 is too incomplete to identify behavior.
- Before first confidential-zone D3A execution, run Vertical Slice Readiness Gate and require all required readiness checks PASS.
- Clarification Provider only asks for critical missing information needed for contracts, scope, or completion gates.
- Prefer `grill-me-method` for clarification: decision tree, frontier rounds, commitment check, no implementation.
- Use `idc-intent-grilling-with-docs` and `grill-with-docs-method` only when clarification should create non-sensitive decision records.
- Fallback to `builtin-critical-questions` if Grill Me method is unavailable or too expensive.
- All Lanes must self-close with evidence.
- Treat Fast as an evidence-backed small-change path: absent or unknown signals never satisfy Fast conditions; a tiny localized production-code change may be Fast only when no new test code is needed and existing verification can close it. New capabilities, behavior-contract changes, new/changed tests, multi-file or multi-component work, focused design, broad repo exploration, or unknown scope must be at least Lite unless a Complex hard trigger applies.
- `fast` does not mean "no verification"; it means small closure.
- Single execution unit code change must be `<= 500 LOC`.
- D3A multi-layer work must split one Layer per Context Packet.
- D3A module marks Lane `not_applicable`, uses `d3a_fixed_workflow`, and bypasses Lane Resolver; do not classify D3A as `fast`, `lite`, or `complex`.
- D3A requires RED evidence, all required DT GREEN, and `tran_build PASS`.
- OKL / docs / CodeGraph / grep findings are context, not DONE evidence.
- Keep enterprise details as placeholders outside the confidential environment.
- All user-facing questions, approvals, re-alignment choices, and escalation decisions must be emitted through `AskUserTool` according to `references/workflows/ask-user-tool-policy.md`; do not ask the user by plain text.

## Output modes

If the user has not approved yet, output an Alignment Pack summary and request approval through `AskUserTool`.

If critical information is missing, output `references/human-views/clarification-view.md` first and do not ask for approval yet.

If the input is a raw idea, output `references/human-views/brainstorming-view.md` before clarification.

If the user approved, run the automated closure loop and report:

```text
plan
context loaded
execution units
evidence
completion status
escalation triggers if any
```

Render completion with `references/human-views/completion-view.md`.

If escalation is triggered, render `references/human-views/escalation-view.md`.

## Output

```yaml
idc_workflow_result:
  status: alignment_needed | approved_running | done | blocked | escalated
  selected_route: DOMAIN_MODULE | DYNAMIC_SCENARIO | GENERAL_CODING | NEED_TRIAGE
  selected_domain: d3a | general | <TEAM_DOMAIN_PLACEHOLDER>
  selected_lane: fast | lite | complex
  human_view_ref: string
  evidence_refs: []
  completion_summary_ref: string
```
