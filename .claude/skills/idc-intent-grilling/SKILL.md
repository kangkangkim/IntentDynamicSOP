---
name: idc-intent-grilling
description: Use when a draft spec, structured requirement, or TR3 design doc needs Grill Me style clarification before alignment; ask bounded frontier-round questions that block contract, scope, or completion gates.
---

# Intent Grilling

Use this atomic skill to turn a draft spec, structured requirement, or TR3 design doc into clarification-ready answers.

It is reusable outside D3A and outside the full ID workflow.

This repository carries the GitHub-carried IDC implementation for Grill Me
because the target company environment does not yet have one. Bring this skill,
its `references/grill-me-method.md`, and `assets/question-card-template.md` into
the confidential environment as-is, then adjust only non-sensitive wording if a
team needs local terminology.

## When To Use

Use for:

- TR3 design docs that still have contract, scope, or completion ambiguity.
- Draft specs produced by `idc-intent-discovery`.
- Structured requirements before Alignment View.
- Any request where implementation would require guessing.

Do not use for:

- rough / raw idea requests that still need Brainstorming first.
- approved Alignment Pack.
- execution, test, build, or failure-fix work.

If the request is rough, route to:

```text
.claude/skills/idc-intent-discovery/SKILL.md
```

## Required Inputs

```text
references/grill-me-method.md
assets/question-card-template.md
../idc-workflow/references/workflows/clarification-provider.md
../idc-workflow/references/schemas/clarification-provider.schema.yaml
../idc-workflow/references/human-views/clarification-view.md
../idc-workflow/references/workflows/requirement-assessor.md
```

## Behavior

```text
Requirement Assessor
  -> NEED_CLARIFICATION
  -> Build decision tree
  -> Select current frontier
  -> AskUserTool <= 5 multiple-choice question cards
  -> User answers
  -> Commitment check
  -> READY_FOR_ALIGNMENT / NEXT_FRONTIER / ESCALATE
```

## Output

Return a user-readable Clarification View and an internal `clarification_provider` contract.

Questions must be multiple-choice question cards.

Each question card must say:

- what they ask
- 2-4 mutually exclusive options
- which option is recommended when there is a safe default
- which contract/scope/completion gate they block
- why the answer is needed before alignment

Use free-form questions only when the answer cannot be represented as choices. If free-form input is needed, keep it as an "Other / 补充说明" field after the choices.

## Hard Rules

- Do not write implementation code.
- Do not decide Domain or Lane.
- Do not override scope, contract, or completion gate.
- Do not ask vague preference questions.
- Do not write a long essay of questions. Use concise multiple-choice cards.
- Do not ask open-ended questions when 2-4 concrete choices can cover the decision.
- Clarification answers are not DONE evidence.
- Use Chinese if the user used Chinese.
- Fallback to `builtin-critical-questions` if Grill Me method is unavailable or too expensive.
- Do not require a team binding for Grill Me unless a team later creates a
  better internal implementation.
- All clarification questions must be emitted through `AskUserTool`; if it is
  unavailable, return `BLOCKED_NEEDS_ASK_USER_TOOL`.
