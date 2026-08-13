---
name: intent-grilling
description: Use when a draft spec, structured requirement, or TR3 design doc needs Grill Me style clarification before alignment; ask bounded frontier-round questions that block contract, scope, or completion gates.
---

# Intent Grilling

Use this atomic skill to turn a draft spec, structured requirement, or TR3 design doc into clarification-ready answers.

It is reusable outside D3A and outside the full ID workflow.

## When To Use

Use for:

- TR3 design docs that still have contract, scope, or completion ambiguity.
- Draft specs produced by `intent-discovery`.
- Structured requirements before Alignment View.
- Any request where implementation would require guessing.

## Required Inputs

```text
../id-workflow/references/workflows/clarification-provider.md
../id-workflow/references/schemas/clarification-provider.schema.yaml
../id-workflow/references/human-views/clarification-view.md
../id-workflow/references/workflows/requirement-assessor.md
```

## Behavior

```text
Requirement Assessor
  -> NEED_CLARIFICATION
  -> Build decision tree
  -> Select current frontier
  -> Ask <= 5 bounded questions
  -> User answers
  -> Commitment check
  -> READY_FOR_ALIGNMENT / NEXT_FRONTIER / ESCALATE
```

## Output

Return a user-readable Clarification View and an internal `clarification_provider` contract.

Questions must say:

- what they ask
- which contract/scope/completion gate they block
- why the answer is needed before alignment

## Hard Rules

- Do not write implementation code.
- Do not decide Domain or Lane.
- Do not override scope, contract, or completion gate.
- Do not ask vague preference questions.
- Clarification answers are not DONE evidence.
- Use Chinese if the user used Chinese.
- Fallback to `builtin-critical-questions` if Grill Me method is unavailable or too expensive.
