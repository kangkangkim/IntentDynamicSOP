# Superpowers Brainstorming Method

This is the locally carried IDC port of the public Superpowers brainstorming
method. It preserves the upstream decision process instead of merely naming
Superpowers as an abstract baseline.

## Source

```text
Repository: https://github.com/obra/superpowers
Source: https://github.com/obra/superpowers/tree/main/skills/brainstorming
Inspected: 2026-08-20
```

The wording here is adapted for IDC. The method, path model, approval gate,
context-first exploration, approach comparison, design review, and one-way
complexity ratchet come from the upstream skill.

## Non-Negotiable Gate

Do not invoke implementation skills, write code, scaffold a project, or make an
implementation change while brainstorming. First make the intended design
visible and obtain the required human decision.

The amount of ceremony scales with the request. The approval gate does not.

In IDC, brainstorming approval confirms the draft direction only. It does not
grant implementation approval; that remains owned by Human Alignment.

## Classify The Path First

Classify before asking the first discovery question. Make the selected path and
reason visible so the user can correct it.

### Spike

Use for a feasibility question whose desired output is an answer or
recommendation, not retained production code.

Typical signals:

- "Can this work?"
- "Is this possible?"
- The user explicitly accepts a disposable probe.

Flow:

1. Explore only enough project context to frame the uncertainty.
2. Present the question and a short probe plan.
3. Obtain approval through `AskUserTool`.
4. Investigate as cheaply as correctness allows.
5. Report findings and a recommendation.

Anything created for the probe remains throwaway. Keeping it requires a new
request and a fresh IDC classification.

### Bounded

Use for a well-scoped change to a flow that already exists in the repository.
Familiarity with the type of application is not enough; there must be an actual
existing flow and a bounded change surface to inspect.

Flow:

1. Inspect relevant files, docs, and recent commits.
2. Ask only material clarification questions, one at a time.
3. Present a short design covering approach, affected files, and verification.
4. Obtain draft-direction approval through `AskUserTool`.
5. Hand the approved draft back to IDC Human Alignment.

Do not write a standalone spec merely to make a bounded task look formal.

### Architectural

Use for a new project, new subsystem, restructuring of component boundaries, or
a change to interfaces that other components depend on.

Flow:

1. Inspect project context before proposing architecture.
2. Ask discovery questions one at a time.
3. Propose two or three materially different approaches.
4. Lead with the recommendation and explain trade-offs.
5. Present the design in coherent sections and validate each section.
6. Produce a draft spec.
7. Self-review the draft spec.
8. Obtain draft-direction approval through `AskUserTool`.
9. Hand off to IDC clarification and Human Alignment.

Durable design-doc writing is handled by `idc-intent-grilling-with-docs` when
the IDC contract says docs are needed. Brainstorming itself does not commit.

## One-Way Complexity Ratchet

When uncertain between two paths, choose the heavier path. If hidden complexity
appears during exploration, stop and upgrade the path. Do not downgrade a path
mid-run merely because some questions became easier.

Examples:

- A presumed one-file change touches a shared interface: Bounded -> Architectural.
- A probe produces a possible implementation: finish the Spike recommendation,
  then classify the implementation as a new task.
- A large idea contains independent subsystems: decompose it before detailed
  questioning, then brainstorm the first sub-project.

## Relationship To IDC Lane

The Superpowers path and IDC Lane are independent classifications:

```text
Spike / Bounded / Architectural = discovery and design depth
fast / lite / complex          = approved execution intensity
```

Never map them directly. In particular:

- `Bounded` does not imply `fast`; a bounded API or production-code change can
  still be Lite or Complex.
- `Architectural` does not directly set `complex`; it usually reveals Complex
  hard triggers, but Lane Resolver must evaluate those signals explicitly.
- `Spike` ends with a recommendation and has no implementation Lane. If the
  user later requests retained code, classify that as a new IDC task.

Brainstorming may record newly discovered lane signals such as API semantic
change, cross-module impact, multiple test domains, unknown scope, or high
failure impact. It must pass those facts to the normalized request. After
Discovery, Domain Module Lane applicability takes precedence; Lane Resolver
handles only applicable dynamic-lane routes. D3A marks Lane `not_applicable`
and uses its fixed workflow regardless of the Superpowers path.

## Understand The Idea

Before detailed questions:

1. Inspect the current repository state, relevant documentation, and recent
   history when available.
2. Determine whether the request is small enough for one coherent design.
3. If it contains multiple independent systems, expose the decomposition,
   dependencies, and recommended sequence.
4. For a coherent scope, refine purpose, users or callers, constraints, success
   criteria, boundaries, and failure behavior.

All user questions use `AskUserTool`. Ask one decision at a time. Prefer
multiple-choice options when they clarify real alternatives, but allow concise
free text when the answer space is genuinely open.

Do not batch unrelated questions. Each answer should update the idea model and
determine the next frontier question.

## Explore Approaches

For a real design branch:

1. Produce two or three distinct approaches.
2. Put the recommended approach first.
3. Explain why it fits the goal and constraints.
4. State trade-offs, risks, and what each option deliberately leaves out.
5. Apply YAGNI and remove features that are not needed for the stated outcome.

Do not invent alternatives when there is only one credible path. In that case,
state the path and its constraints directly.

## Present The Design

Scale the design to the path:

- Spike: question, probe boundary, and expected learning.
- Bounded: a few sentences or short paragraphs.
- Architectural: sections sized to their actual complexity.

Where relevant, cover:

- architecture and boundaries
- components and responsibilities
- data or control flow
- interfaces and dependencies
- error and edge-case handling
- testing and completion evidence

For Architectural work, validate each meaningful section through
`AskUserTool`. If the answer reveals a contradiction or missing decision, return
to discovery rather than papering over it.

## Design For Isolation And Clarity

Prefer units with one clear responsibility and explicit interfaces. For each
unit, be able to answer:

- What does it do?
- How is it used?
- What does it depend on?
- Can its internals change without breaking callers?
- Can it be understood and tested without loading unrelated code?

Follow useful existing repository patterns. Include targeted improvements only
when they directly support the requested design; do not attach unrelated
refactors.

## Draft Spec Self-Review

Before handoff, check the draft with fresh eyes:

1. Placeholder check: unresolved `TBD`, `TODO`, or incomplete decisions.
2. Consistency check: requirements, architecture, and acceptance signals agree.
3. Scope check: one implementation plan can reasonably own the result.
4. Ambiguity check: material requirements do not have multiple interpretations.

Fix issues inside the draft before asking for approval. Do not claim the draft
is an approved contract.

## Optional Visual Questions

Offer a visual companion only when a specific question is materially easier to
answer by seeing mockups, diagrams, layouts, or spatial relationships. Make the
offer through `AskUserTool`; do not offer it at the start of every session.

Use an available visualization capability for visual questions. Textual scope,
requirements, trade-offs, and API decisions remain regular `AskUserTool`
questions. If no supported visual capability exists, continue without one.

## IDC Terminal Mapping

```text
Superpowers path classification
  -> context-first exploration
  -> one-at-a-time AskUserTool discovery
  -> approaches when a real branch exists
  -> path-sized design
  -> draft-spec self-review
  -> AskUserTool draft-direction approval
  -> idc-intent-discovery normalization
  -> Lane signals only; module applicability decides whether Lane Resolver runs
  -> idc-intent-grilling if critical gaps remain
  -> idc-intent-grilling-with-docs if durable docs are required
  -> idc-intent-alignment for implementation approval
```

This mapping replaces upstream's direct transition to implementation planning.
IDC continues to own Domain, Lane, contracts, implementation approval, and
completion gates.
