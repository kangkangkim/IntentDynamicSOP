---
name: intent-alignment
description: Use when a normalized request, domain/lane decision, contract set, scope boundary, and completion gate need to be shown to a human for approval before implementation.
---

# Intent Alignment

Use this atomic skill to render the human approval checkpoint before implementation.

It is reusable outside D3A and outside the full ID workflow.

## When To Use

Use after:

- Discovery is complete or skipped.
- Clarification is complete or not needed.
- Domain and Lane are selected.
- Contract Gate has produced the required contract set.
- Scope boundary and completion gate are known.

## Required Inputs

```text
../id-workflow/references/workflows/human-alignment.md
../id-workflow/references/schemas/alignment-pack.schema.yaml
../id-workflow/references/human-views/alignment-view.md
../id-workflow/references/human-views/completion-view.md
../id-workflow/references/human-views/escalation-view.md
```

## Behavior

```text
Machine Contract
  -> Alignment View
  -> User approve / request clarification / request reclassify / reject
  -> approved Alignment Pack or return to earlier stage
```

## Output

Return a user-readable Alignment View and keep the internal Alignment Pack machine-readable.

The view must include:

- task understanding
- Domain and Lane
- change type and change shape
- required contracts
- scope boundary
- completion gate
- approval request

## Hard Rules

- Do not show raw YAML as the primary user interface.
- Do not write implementation code before approval.
- Do not ask for approval if there are open critical questions.
- If the user requests clarification, return to `intent-grilling`.
- If the user approves, hand off to the automated closure loop.
