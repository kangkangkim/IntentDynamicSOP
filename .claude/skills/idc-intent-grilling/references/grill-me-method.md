# Grill Me Method

This reference defines the reusable clarification method used by
`intent-grilling`.

It is inspired by the public `mattpocock/skills` Grill Me family and adapted for
IDC. It does not copy upstream prompts verbatim.

Use this GitHub-carried IDC version when a company team does not already have a
Grill Me implementation. It is intentionally portable and should not require
team-specific repository knowledge.

## Goal

Turn an unclear draft spec, structured requirement, or TR3 design document into
contract-ready answers before Human Alignment.

## Method

```text
Build decision tree
  -> identify settled decisions
  -> select current frontier
  -> ask bounded question cards
  -> update assumptions and blockers
  -> commitment check
```

## Frontier Round

A frontier round asks only questions whose prerequisites are already settled.

Do not ask downstream implementation details when upstream contract or scope
decisions are still open.

## Question Priority

Ask in this order:

1. Questions that change implementation path.
2. Questions that change API Contract.
3. Questions that change Verification Contract.
4. Questions that change completion gate.
5. Questions that change scope boundary.

## Commitment Check

At the end of each round, choose exactly one:

```text
READY_FOR_ALIGNMENT
NEXT_FRONTIER
ESCALATE
```

`READY_FOR_ALIGNMENT` means the task can produce Alignment View without hiding
critical unknowns.

`NEXT_FRONTIER` means another bounded question round is needed.

`ESCALATE` means the missing information cannot be resolved by normal
clarification.

## Hard Rules

- Do not write implementation code.
- Do not ask vague preference questions.
- Do not ask more than 5 questions per frontier round.
- Prefer 2-4 mutually exclusive options.
- Free-form is allowed only when choices cannot cover the decision.
- Clarification answers are not DONE evidence.
- Human Alignment must happen after clarification.
