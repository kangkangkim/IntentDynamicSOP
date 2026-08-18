---
name: brainstorming
description: Use only when a coding request is a raw idea, vague thought, unclear feature concept, or early product direction that needs divergent exploration before clarification or implementation; produce 2-3 concrete approaches and a draft spec, without writing code.
---

# Brainstorming

Use this atomic skill only when the user has a vague early idea that does not yet have enough shape for Grill Me, Alignment, or coding.

It is reusable outside D3A and outside the full ID workflow.

This skill uses upstream Superpowers brainstorming as the baseline, then keeps IDC-specific handoff fields small and explicit.

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
../idc-workflow/references/workflows/discovery-provider.md
../idc-workflow/references/schemas/discovery-provider.schema.yaml
../idc-workflow/references/human-views/brainstorming-view.md
../idc-workflow/references/schemas/normalized-request.schema.yaml
```

## Behavior

```text
raw_idea
  -> upstream-superpowers-brainstorming baseline
  -> Explore lightweight project context if it helps the discussion
  -> Ask focused discovery questions when the idea is too ambiguous
  -> Offer 2-3 approaches if there are real design branches
  -> Produce draft spec
  -> Render Brainstorming View
  -> Hand off to idc-intent-grilling / idc-intent-alignment when ready
```

## Output

Return a user-readable Brainstorming View and an internal `discovery_provider` contract.

The draft spec must include:

- goal
- users_or_callers
- core_behavior
- out_of_scope
- acceptance_signals
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
- Do not use this skill merely because the request is short; short structured requests go to Grill Me / Alignment, not Brainstorming.
- Use Chinese if the user used Chinese.
- TR3 skips this skill unless the TR3 is too incomplete to identify behavior.
- Domain hint must not suppress brainstorming: `general + rough` still uses this skill.
- Keep enterprise details as placeholders outside the confidential environment.
