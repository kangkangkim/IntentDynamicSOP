---
name: intent-discovery
description: Use when a coding request is a raw idea, one-line intent, vague feature request, or early product thought that needs brainstorming before clarification; expand it into a draft spec without writing implementation code.
---

# Intent Discovery

Use this atomic skill to turn `raw_idea` input into a draft spec.

It is reusable outside D3A and outside the full ID workflow.

Use upstream Superpowers brainstorming as the baseline, then apply the IDC overlay for handoff and contract shape.

## When To Use

Use for:

- 一句话需求。
- 模糊想法。
- 还没有核心行为、边界或验收标准的需求。
- 需要先发散出 2-3 个可选方案的需求。

Do not use by default for:

- TR3 design docs.
- 已经有目标、核心行为和验收线索的 structured requirement。
- 已经 approved 的 Alignment Pack。

## Required Inputs

```text
../id-workflow/references/workflows/discovery-provider.md
../id-workflow/references/schemas/discovery-provider.schema.yaml
../id-workflow/references/human-views/brainstorming-view.md
../id-workflow/references/schemas/normalized-request.schema.yaml
```

## Behavior

```text
raw_idea
  -> upstream-superpowers-brainstorming baseline
  -> idc-brainstorming-overlay
  -> Explore lightweight project context
  -> Ask focused discovery questions
  -> Offer 2-3 approaches if there are real design branches
  -> Produce draft spec
  -> Render Brainstorming View
```

## Output

Return a user-readable Brainstorming View and an internal `discovery_provider` contract.

The draft spec must include:

- goal
- users_or_callers
- core_behavior
- out_of_scope
- acceptance_signals
- next: Clarification Provider

## Hard Rules

- Do not write implementation code.
- Do not mark draft spec as approved contract.
- Do not treat upstream design approval as implementation approval; hand off to `intent-grilling` and `intent-alignment`.
- Use Chinese if the user used Chinese.
- TR3 skips this skill unless the TR3 is too incomplete to identify behavior.
- Keep enterprise details as placeholders outside the confidential environment.
