# Skillization Boundary

IDC should skill-ize independently callable abilities: orchestration,
pre-alignment, domain execution, and external adapters.

It should not turn every workflow node into a skill. Router rules, gate policy,
lane definitions, evidence contracts, and completion checks are loaded by the
orchestration skill as references unless they need their own stable invocation
surface.

Passive data must be沉淀为 assets or references, not left as ambiguous loose
notes.

## Should Be Skills

These are active behaviors with stable input/output and independent reuse:

- workflow orchestration.
- intent discovery.
- brainstorming.
- intent grilling.
- intent alignment.
- skill adapter routing.
- General Coding execution.
- D3A Coding execution.
- build / DT / enterprise SOP adapters.

## Should Become Assets / References

These are passive assets and references:

- schemas.
- registries.
- lane definitions.
- input adapter rules.
- scenario router rules.
- domain module router rules.
- contract gate policy.
- requirement assessment policy.
- human-output surface routing policy.
- knowledge loading policy.
- provider selection policy.
- repository context policy.
- delegation policy.
- execution authorization policy and validator contract.
- execution unit planning policy.
- automated closure policy.
- TDD state machine policy.
- lane completion policy.
- evidence gate policy.
- vertical slice readiness policy.
- resume policy.
- human-view templates.
- knowledge templates.
- examples.
- evidence files.
- diagrams.
- migration checklists.
- source attribution.

## References vs Assets

Follow the Claude / Agent Skills directory shape:

```text
.claude/skills/<name>/SKILL.md
  instructions and routing metadata

.claude/skills/<name>/references/
  additional documentation loaded on demand

.claude/skills/<name>/assets/
  static resources such as templates, images, or data files

.claude/skills/<name>/scripts/
  executable helper code
```

This harness currently uses:

```text
.claude/skills/idc-workflow/references/
  workflow references, schemas, registries, human-view instructions, knowledge reference docs

.claude/skills/idc-workflow/assets/
  static resources and asset taxonomy

docs/
  human-readable design, adoption, attribution, and migration notes

examples/
  non-sensitive walkthrough and fixture assets

test/
  manual scenario cards

tests/
  executable harness checks
```

Do not create free-floating passive files without deciding whether they are
skill-loadable references, static assets, docs, examples, manual scenarios, or
harness tests.

## User Entry

The user-facing entry remains:

```text
$idc-workflow
```

The entry is the `idc-workflow` skill itself; there is no command alias layer.
Lower-level skills are internal building blocks. Users should not need to call
them directly.

## Confidential Boundary

Enterprise GC SOP and original-repository skills should be represented by
adapter skills in the external harness.

The adapter can declare:

- when it can run.
- what it needs as input.
- what it returns.
- what evidence refs are required.
- what it must not override.

The adapter must not contain real enterprise paths, commands, APIs, logs, test
names, or SOP internals outside the confidential zone. Those confidential
materials should become internal assets / references in the enterprise repo.
