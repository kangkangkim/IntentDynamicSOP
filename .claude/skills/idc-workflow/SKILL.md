---
name: idc-workflow
description: Use when the user asks to run, try, trigger, or apply the Intent Dynamic Code / IDC workflow; process a one-line request or TR3 design document; generate an Alignment Pack; classify Domain Module and Lane; or continue an approved Alignment Pack through the automated closure loop with evidence gates.
---

# IDC Workflow

Use this skill to run the Intent Dynamic Code workflow.

The user-facing slash command entrypoint is:

```text
.claude/commands/id-workflow.md
```

Users should enter through `/id-workflow`; this skill remains the orchestration
implementation behind that command.

This is the orchestration skill. It delegates reusable work to a small set of
skills, and reads router/gate/policy behavior from references.

```text
.claude/skills/idc-intent-discovery/SKILL.md
.claude/skills/idc-brainstorming/SKILL.md
.claude/skills/idc-intent-grilling/SKILL.md
.claude/skills/idc-intent-grilling/references/grill-me-method.md
.claude/skills/idc-intent-grilling/assets/question-card-template.md
.claude/skills/idc-intent-grilling-with-docs/SKILL.md
.claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md
.claude/skills/idc-intent-alignment/SKILL.md
.claude/skills/idc-skill-adapter-router/SKILL.md
.claude/skills/idc-general-coding/SKILL.md
.claude/skills/idc-d3a-coding/SKILL.md
.claude/skills/idc-dt-build/SKILL.md
.claude/skills/idc-tran-build/SKILL.md
.claude/skills/idc-superpowers-adapter/SKILL.md
.claude/skills/idc-gc-sop-adapter/SKILL.md
.claude/skills/idc-dt-design/SKILL.md
.claude/skills/idc-dt-writer/SKILL.md
.claude/skills/idc-gc-third-skill-placeholder/SKILL.md
```

Router, gate, lane, provider, completion, resume, and evidence behavior remains
under `references/` as passive policy/configuration, not standalone skills.

## When To Use

Use this skill when `/id-workflow` needs to classify an input, produce an
Alignment Pack, route to IDC pre-alignment skills, or continue an approved pack
through General Coding or D3A Coding evidence gates.

Do not use it as a lower-level adapter. For external SOP reuse or domain build
steps, route through `idc-skill-adapter-router` and the specific `idc-*` adapter
or execution skill.

## Trigger examples

- "/id-workflow <task>"
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

Default mode:

```text
references/workflows/input-adapter.md
  -> Intent Maturity Router
  -> references/workflows/scenario-router.md
  -> idc-intent-discovery if raw_idea
  -> references/workflows/domain-module-router.md if DOMAIN_MODULE
  -> references/workflows/lane-resolver.md
  -> references/workflows/contract-gate.md
  -> references/workflows/requirement-assessor.md
  -> idc-intent-grilling if needed
  -> idc-intent-grilling-with-docs if clarification must update docs
  -> Alignment Pack
  -> idc-intent-alignment
  -> references/human-views/
```

After the user approves:

```text
references/workflows/automated-closure-loop.md
  -> Planner
  -> references/workflows/execution-unit-policy.md
  -> references/workflows/progressive-constraint-loading.md
  -> idc-superpowers-adapter if execution discipline is needed
  -> idc-gc-sop-adapter if confidential GC atomic abilities are needed
  -> .claude/skills/idc-skill-adapter-router/SKILL.md if lower-level adapters are needed
  -> references/workflows/delegation-router.md
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

## Load only what is needed

Read these files first:

```text
CONTEXT_ENGINEERING.md
CLAUDE.md
references/workflows/input-adapter.md
references/workflows/scenario-router.md
references/workflows/domain-module-router.md
references/workflows/lane-resolver.md
references/workflows/contract-gate.md
references/workflows/requirement-assessor.md
references/workflows/human-alignment.md
references/workflows/delegation-router.md
references/workflows/skill-adapter-router.md
references/workflows/resume-policy.md
references/schemas/alignment-pack.schema.yaml
references/schemas/delegation-contract.schema.yaml
references/schemas/skill-adapter.schema.yaml
references/registries/skill-adapters.yaml
references/schemas/runtime-state.schema.yaml
assets/README.md
.claude/skills/idc-intent-discovery/SKILL.md
.claude/skills/idc-intent-grilling/SKILL.md
.claude/skills/idc-intent-grilling/references/grill-me-method.md
.claude/skills/idc-intent-grilling/assets/question-card-template.md
.claude/skills/idc-intent-grilling-with-docs/SKILL.md
.claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md
.claude/skills/idc-intent-alignment/SKILL.md
references/workflows/discovery-provider.md
references/schemas/discovery-provider.schema.yaml
references/human-views/brainstorming-view.md
references/human-views/alignment-view.md
references/human-views/clarification-view.md
```

If Requirement Assessor returns `NEED_CLARIFICATION`, also read:

```text
references/workflows/clarification-provider.md
references/schemas/clarification-provider.schema.yaml
references/human-views/clarification-view.md
.claude/skills/idc-intent-grilling-with-docs/SKILL.md if clarification must update docs
.claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md if clarification must update docs
```

If `input_maturity = raw_idea`, run Discovery Provider before Clarification Provider:

```text
.claude/skills/idc-brainstorming/SKILL.md
references/workflows/discovery-provider.md
references/schemas/discovery-provider.schema.yaml
references/human-views/brainstorming-view.md
```

If the input is TR3, also read:

```text
references/schemas/normalized-request.schema.yaml
references/docs/deep-dive/tr3-input.md
```

If Domain = D3A, also read:

```text
references/domains/d3a/module.yaml
references/workflows/d3a-workflow.md
references/schemas/d3a-plan.schema.yaml
.claude/skills/idc-d3a-coding/SKILL.md
.claude/skills/idc-dt-build/SKILL.md
.claude/skills/idc-tran-build/SKILL.md
```

If Domain = general, also read:

```text
references/domains/general/module.yaml
references/workflows/general-coding.md
references/schemas/general-plan.schema.yaml
.claude/skills/idc-general-coding/SKILL.md
```

If the user has approved the Alignment Pack, also read:

```text
.claude/skills/idc-skill-adapter-router/SKILL.md
references/workflows/automated-closure-loop.md
references/workflows/delegation-router.md
references/workflows/progressive-constraint-loading.md
references/workflows/execution-unit-policy.md
references/workflows/knowledge-gate.md
references/workflows/provider-selection-matrix.md
references/workflows/repo-context-providers.md
references/workflows/tdd-state-machine.md
references/workflows/lane-completion.md
references/schemas/delegation-contract.schema.yaml
references/schemas/escalation-policy.schema.yaml
.claude/skills/idc-superpowers-adapter/SKILL.md
.claude/skills/idc-gc-sop-adapter/SKILL.md
.claude/skills/idc-dt-design/SKILL.md
.claude/skills/idc-dt-writer/SKILL.md
.claude/skills/idc-gc-third-skill-placeholder/SKILL.md
```

If the user asks to resume after interruption, also read:

```text
references/workflows/resume-policy.md
references/schemas/runtime-state.schema.yaml
references/schemas/delegation-contract.schema.yaml
```

If the user is preparing the first confidential-zone D3A vertical slice, also read:

```text
references/workflows/vertical-slice-readiness-gate.md
references/schemas/vertical-slice-readiness.schema.yaml
docs/confidential-migration-checklist.md
```

For repo context work, read:

```text
CONTEXT_ENGINEERING.md
references/workflows/provider-selection-matrix.md
references/workflows/repo-context-providers.md
references/schemas/repo-context-provider.schema.yaml
```

## Hard Rules

- Do not write implementation code before Human Alignment approval.
- Follow `CONTEXT_ENGINEERING.md`: load stage-specific context, summarize long findings, and keep DONE evidence separate from knowledge findings.
- Main agent role is `planning_and_delegation_only`: select IDC workflow route, decide whether official dynamic workflow is needed, create Delegation Contract, dispatch agent team / subagent, then summarize returned evidence.
- Delegation selection order is mandatory: IDC workflow route -> official dynamic workflow if needed -> agent team -> subagent.
- IDC workflow route is event-triggered state routing; official dynamic workflow is only for scripted, repeatable, large-scale fan-out orchestration.
- Use agent team only when multiple subagents need communication, handoff, shared intermediate artifacts, review, or merge.
- Main agent must not directly execute complex implementation, consume full logs, consume full search results, or merge full subagent sessions back into main context.
- Interruption resume must use `runtime_state` checkpoint refs, not main agent memory.
- After resuming an interrupted execution, re-run verification unless tool evidence proves the interrupted step completed.
- Keep `idc-workflow` as orchestration; reusable pre-alignment, domain execution, and adapter behavior lives in skills.
- Keep router, gate, lane, provider, completion, resume, and evidence behavior in `references/`; do not promote them to standalone skills unless they need independent invocation.
- Do not skillize passive assets such as schemas, registries, examples, human-view templates, lane definitions, evidence files, and knowledge templates;沉淀 them as references or assets according to the official skill directory shape.
- Superpowers Adapter may provide the inner engineering loop after approval, but IDC owns Domain, Lane, Contract Gate, and Completion Gate.
- GC SOP Adapter may reuse confidential enterprise atomic abilities after approval, but must go through Skill Adapter Router and cannot invent original repository skill details.
- Skill Adapter Router must select GC / DT / Superpowers adapters from `references/registries/skill-adapters.yaml`; adapter names are not triggers by themselves.
- Original repository DT skills are represented as adapters: `idc-dt-design` for DT design, `idc-dt-writer` for DT writing, and `idc-gc-third-skill-placeholder` until the third skill is named in the confidential zone.
- Use `upstream-superpowers-brainstorming` as the `raw_idea` baseline, then apply `idc-brainstorming-overlay` before handoff to `idc-intent-grilling`.
- Skip Discovery Provider for TR3 unless the TR3 is too incomplete to identify behavior.
- Before first confidential-zone D3A execution, run Vertical Slice Readiness Gate and require all required readiness checks PASS.
- Clarification Provider only asks for critical missing information needed for contracts, scope, or completion gates.
- Prefer `grill-me-method` for clarification: decision tree, frontier rounds, commitment check, no implementation.
- Use `idc-intent-grilling-with-docs` and `grill-with-docs-method` only when clarification should create non-sensitive decision records.
- Fallback to `builtin-critical-questions` if Grill Me method is unavailable or too expensive.
- All Lanes must self-close with evidence.
- `fast` does not mean "no verification"; it means small closure.
- Single execution unit code change must be `<= 500 LOC`.
- D3A multi-layer work must split one Layer per Context Packet.
- D3A requires RED evidence, all required DT GREEN, and `tran_build PASS`.
- OKL / docs / CodeGraph / grep findings are context, not DONE evidence.
- Keep enterprise details as placeholders outside the confidential environment.

## Output modes

If the user has not approved yet, output an Alignment Pack summary and ask for approval.

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
