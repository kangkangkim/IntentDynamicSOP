# /id-workflow

Thin user-facing alias for the IDC skill orchestration layer.

This command intentionally contains no workflow logic. All executable behavior
lives in `idc-*` skills, with `idc-workflow` as the only orchestration skill.

## Arguments

```text
$ARGUMENTS
```

`$ARGUMENTS` may be a raw idea, structured request, TR3 design document,
approved Alignment Pack reference, or resume checkpoint reference.

## Invoke

Run the orchestration skill:

```text
.claude/skills/idc-workflow/SKILL.md
```

## Hard Rules

- `/id-workflow` is the only user-facing command alias.
- Command files must stay thin; do not move routing, gate, adapter, evidence, or execution behavior back into `.claude/commands/`.
- All IDC capabilities must live under `.claude/skills/idc-*/SKILL.md`.
- All IDC skill names must start with `idc-`.
- Do not call lower-level skills directly from user intent before `idc-workflow` routing.
- Keep enterprise paths, APIs, commands, logs, tests, and SOP internals as placeholders outside the confidential environment.
