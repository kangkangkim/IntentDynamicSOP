---
name: idc-intent-alignment
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

Do not use when:

- rough / raw idea still needs `idc-intent-discovery`.
- critical contract / scope / completion gate questions remain.
- unresolved questions would need to be shown as "pending details" in the Alignment View.
- implementation has already started without approval.

If critical questions remain, route to:

```text
.claude/skills/idc-intent-grilling/SKILL.md
```

## Required Inputs

```text
../idc-workflow/references/workflows/human-alignment.md
../idc-workflow/references/schemas/alignment-pack.schema.yaml
../idc-workflow/references/human-views/alignment-view.md
../idc-workflow/references/human-views/completion-view.md
../idc-workflow/references/human-views/escalation-view.md
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

The view must not include unresolved clarification questions.

If any contract, scope, completion gate, API semantics, test evidence, or file-placement gap remains, do not render Alignment View yet. Return to `idc-intent-grilling` and show a Clarification View with multiple-choice question cards.

## Hard Rules

- Do not show raw YAML as the primary user interface.
- Do not write implementation code before approval.
- Do not ask for approval if there are open critical questions.
- Do not merge Clarification View into Alignment View.
- Do not put "pending details", "open questions", or long-form clarification prompts inside Alignment View.
- If the user requests clarification, return to `idc-intent-grilling`.
- If the user approves, hand off to the automated closure loop.
