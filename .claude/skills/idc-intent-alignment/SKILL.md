---
name: idc-intent-alignment
description: Use when a normalized request needs Human Alignment readiness detection, critical gap routing, stale approval checking, or final human approval before implementation.
---

# Intent Alignment

Use this atomic skill to run the Human Alignment gate before implementation.

It is reusable outside D3A and outside the full ID workflow.

Human Alignment owns the detection of whether the current request is ready for
approval. Discovery may provide signals, but this skill decides whether to
route to Brainstorming, Grill Me, Grill With Docs, Alignment View, Re-alignment,
or execution after approval.

## When To Use

Use after:

- Discovery is complete or skipped.
- A normalized request or approved checkpoint exists.
- Domain, Lane, contract set, scope boundary, or completion gate need a readiness check.
- Existing approval / runtime state must be validated before resume.

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
  -> Human Alignment Check
  -> Brainstorming / Grill Me / Grill With Docs if needed
  -> Alignment View
  -> User approve / request clarification / request reclassify / reject
  -> approved Alignment Pack or return to earlier stage
```

## Readiness Detection

Before rendering Alignment View, detect:

- `needs_alternatives`: raw / vague / incomplete input still needs Brainstorming.
- `critical_gap`: contract, scope, completion gate, API semantics, test evidence, or file placement gap remains.
- `docs_needed`: clarification must update non-sensitive docs, ADR, glossary, or decision records.
- `approval_ready`: task understanding, Domain / Lane, contracts, scope, and evidence plan are clear enough for approval.
- `approval_valid`: existing approval ref and runtime checkpoint are still current.
- `scope_drift`: execution would exceed the approved scope and must return to Re-alignment.

Only render Alignment View when the status is `approval_ready`.

Only hand off to the automated closure loop when the user has approved and the
approval state is still valid.

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
- Do not let Discovery maturity signal bypass Human Alignment readiness detection.
- Do not resume execution from a stale approval ref.
- If the user requests clarification, return to `idc-intent-grilling`.
- If the user approves, hand off to the automated closure loop.
