# Grill With Docs Method

This reference defines the stateful IDC clarification method for cases where
questions and decisions should also update non-sensitive project docs.

It is inspired by the public `mattpocock/skills` Grill With Docs workflow and
adapted for IDC. It does not copy upstream prompts verbatim.

## Goal

Challenge a plan or design against existing project language, then record
settled decisions before Human Alignment.

## Method

```text
Read bounded docs
  -> Build decision tree
  -> Ask frontier-round question cards
  -> Capture settled decisions
  -> Update docs only for crystallized decisions
  -> Commitment check
```

## Bounded Docs

Read only docs needed for the current clarification frontier:

- existing `CONTEXT.md` or project overview.
- relevant ADRs.
- glossary or terminology notes.
- non-sensitive domain notes.

Do not read full logs, full repositories, or unrelated documentation just to ask
better questions.

## Writable Docs

Allowed outputs:

- `CONTEXT.md` updates for stable project context.
- ADRs for accepted architectural decisions.
- glossary entries for stable terms.
- clarification notes that will be referenced by Alignment Pack.

Do not write implementation code, tests, build scripts, generated artifacts, or
confidential enterprise facts into shared docs.

## Commitment Check

At the end of each round, choose exactly one:

```text
READY_FOR_ALIGNMENT
NEXT_FRONTIER
ESCALATE
```

`READY_FOR_ALIGNMENT` means docs contain enough settled decisions to render
Alignment View without hiding critical unknowns.

`NEXT_FRONTIER` means another bounded question round is needed.

`ESCALATE` means docs reveal a blocker that cannot be resolved by clarification.

## Hard Rules

- Keep docs updates small and attributable to settled answers.
- Do not turn speculative options into recorded decisions.
- Do not write code after finishing the interview.
- Do not mark docs as implementation evidence.
- Human Alignment remains required after docs are updated.
