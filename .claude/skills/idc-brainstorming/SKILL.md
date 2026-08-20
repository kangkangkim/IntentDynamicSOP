---
name: idc-brainstorming
description: Use only when a coding request is a raw idea, vague thought, unclear feature concept, or early product direction that needs divergent exploration before clarification or implementation; produce 2-3 concrete approaches and a draft spec, without writing code.
---

# Brainstorming

Use this atomic skill only when the user has a vague early idea that does not yet have enough shape for Grill Me, Alignment, or coding.

It is reusable outside D3A and outside the full ID workflow.

This skill carries a local, executable port of upstream Superpowers
brainstorming. It does not merely refer to the upstream name. Read
`references/superpowers-brainstorming-method.md` before running the skill, then
apply the IDC-specific handoff and approval constraints in this file.

In a confidential company environment, prefer the team's existing
brainstorming implementation when effective team config provides
`idc-brainstorming`. This skill remains the shared IDC wrapper and fallback
contract so every team returns the same draft-spec shape.

## When To Use

Use for:

- 一句话但仍然模糊的需求。
- 模糊想法。
- rough / vague / sketchy general coding request。
- 用户说“大概想做”“先试试”“还没想清楚”“不完整想法”。
- 还没有核心行为、边界或验收标准的需求。
- 需要先发散出 2-3 个可选方案的需求。

Do not use by default for:

- 一句话但已经给出目标、行为和验收线索的需求。
- TR3 design docs.
- 已经有目标、核心行为和验收线索的 structured requirement。
- 已经 approved 的 Alignment Pack。
- build failure、test failure、执行修复类任务。

## Required Inputs

```text
references/superpowers-brainstorming-method.md
../idc-workflow/references/workflows/discovery-provider.md
../idc-workflow/references/schemas/discovery-provider.schema.yaml
../idc-workflow/references/human-views/brainstorming-view.md
../idc-workflow/references/schemas/normalized-request.schema.yaml
```

## Behavior

```text
raw_idea
  -> team brainstorming binding if available
  -> otherwise load local Superpowers brainstorming method
  -> classify Spike / Bounded / Architectural before the first question
  -> announce the selected path and reason
  -> explore project context before proposing a design
  -> AskUserTool one material discovery question at a time
  -> upgrade path if hidden complexity appears; never downgrade mid-run
  -> offer 2-3 approaches with trade-offs and a recommendation when a real branch exists
  -> present a path-sized design
  -> self-review placeholders, consistency, scope, and ambiguity
  -> AskUserTool confirm draft direction
  -> produce draft spec
  -> Render Brainstorming View
  -> Hand off to idc-intent-grilling / idc-intent-alignment when ready
```

The upstream paths are preserved:

- `Spike`: approved feasibility probe, then recommendation only.
- `Bounded`: existing repo flow, focused questions, short in-chat design.
- `Architectural`: context, questions, 2-3 approaches, sectioned design, draft spec, self-review.

The IDC overlay changes the terminal transition only: upstream draft approval
does not start implementation. It returns to IDC Clarification / Human
Alignment, where Domain, Lane, contracts, and implementation approval are
decided.

Superpowers path is not IDC Lane:

```text
Spike / Bounded / Architectural = Discovery depth
fast / lite / complex = execution intensity after approval
```

Do not create a direct mapping. This skill may discover and return lane signals.
After Domain routing, a fixed module lane policy takes precedence (D3A fixes
`complex`); Lane Resolver selects the Lane only for dynamic-lane routes.

## Output

Return a user-readable Brainstorming View and an internal `discovery_provider` contract.

The draft spec must include:

- superpowers_path
- path_reason
- goal
- users_or_callers
- core_behavior
- out_of_scope
- acceptance_signals
- alternatives_and_tradeoffs
- unresolved_decisions
- self_review_result
- observed_lane_signals
- lane_decision_deferred
- recommended_next_step

## Handoff

When this skill is used inside IDC, hand off to:

```text
.claude/skills/idc-intent-discovery/SKILL.md
```

`idc-intent-discovery` owns IDC-specific routing, normalized request updates, and the transition to Grill Me / Alignment.

## Hard Rules

- Do not write implementation code.
- Do not mark draft spec as approved contract.
- Do not treat upstream design approval as implementation approval.
- Do not skip `references/superpowers-brainstorming-method.md`; the local method is the actual fallback implementation.
- Classify `Spike | Bounded | Architectural` before the first user question.
- Hidden complexity may only upgrade the path; never downgrade it mid-run.
- Never map Spike / Bounded / Architectural directly to fast / lite / complex.
- Emit observed lane signals as facts and defer lane selection to fixed module policy or Lane Resolver.
- Ask one material discovery question at a time.
- Explore relevant files, docs, and recent commits before proposing a design when repo context exists.
- Architectural work must compare 2-3 approaches and self-review the draft spec before handoff.
- Do not commit a design document from this skill. Route durable documentation through `idc-intent-grilling-with-docs` when required.
- Do not use this skill merely because the request is short; short structured requests go to Grill Me / Alignment, not Brainstorming.
- Use Chinese if the user used Chinese.
- TR3 skips this skill unless the TR3 is too incomplete to identify behavior.
- Domain hint must not suppress idc-brainstorming: `general + rough` still uses this skill.
- Keep enterprise details as placeholders outside the confidential environment.
- Company-owned brainstorming should be reused through Team Binding, not copied
  into the shared harness.
- All questions or direction choices shown to the user must be emitted through
  `AskUserTool`; if it is unavailable, return `BLOCKED_NEEDS_ASK_USER_TOOL`.
