---
name: idc-intent-grilling-with-docs
description: Use when a draft spec, structured requirement, or TR3 design doc needs Grill Me style clarification against project documentation, and the session should also create or update non-sensitive decision docs such as CONTEXT.md, ADRs, or glossary entries before alignment; never write implementation code.
---

# Intent Grilling With Docs

Use this skill when clarification needs to be stateful: the user wants the
questions, settled decisions, project vocabulary, or architectural trade-offs to
be captured as documentation while the idea is sharpened.

It is reusable outside D3A and outside the full ID workflow.

This is the IDC-carried version of Grill With Docs. It is inspired by the public
`mattpocock/skills` Grill With Docs family and adapted for IDC contracts. It
does not copy upstream prompts verbatim.

## When To Use

Use for:

- TR3 or structured requirements that need clarification against existing docs.
- Draft specs that should produce a durable decision record before Alignment.
- Domain vocabulary, API semantics, or scope decisions that must be remembered.
- Company confidential environments that do not already have Grill With Docs.

Do not use for:

- rough / raw idea requests that still need Brainstorming first.
- ordinary Grill Me sessions that should leave no workspace files.
- approved Alignment Pack.
- implementation, test, build, or failure-fix work.

If no docs should be written, use:

```text
.claude/skills/idc-intent-grilling/SKILL.md
```

## Required Inputs

```text
references/grill-with-docs-method.md
../idc-intent-grilling/references/grill-me-method.md
../idc-intent-grilling/assets/question-card-template.md
../idc-workflow/references/workflows/clarification-provider.md
../idc-workflow/references/schemas/clarification-provider.schema.yaml
../idc-workflow/references/human-views/clarification-view.md
../idc-workflow/references/workflows/requirement-assessor.md
```

## Behavior

```text
Requirement Assessor
  -> NEED_CLARIFICATION
  -> Read bounded project docs / existing decision records
  -> Build decision tree
  -> Select current frontier
  -> Ask <= 5 multiple-choice question cards
  -> User answers
  -> Update non-sensitive docs only when decisions crystallize
  -> Commitment check
  -> READY_FOR_ALIGNMENT / NEXT_FRONTIER / ESCALATE
```

## Output

Return a user-readable Clarification View and an internal
`clarification_provider` contract.

When docs are updated, return refs only:

```yaml
grill_with_docs_output:
  status: READY_FOR_ALIGNMENT | NEXT_FRONTIER | ESCALATE
  updated_doc_refs: []
  adr_refs: []
  glossary_refs: []
  open_questions: []
  blocked_gates: []
```

## Hard Rules

- Do not write implementation code.
- Do not edit source files, tests, build files, or production configs.
- Only create or update non-sensitive docs requested by the workflow.
- Do not write enterprise secrets, real internal APIs, private paths, logs, or
  confidential build commands into shared docs.
- Do not decide Domain or Lane.
- Do not override scope, contract, or completion gate.
- Do not ask more than 5 questions per frontier round.
- Use concise multiple-choice question cards by default.
- Documentation created here is not RED evidence, GREEN evidence, or DONE
  evidence.
- Human Alignment must happen after clarification.
