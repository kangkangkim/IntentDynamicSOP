# /id-workflow

Unified entrypoint for the Intent Dynamic Code framework.

Use this command for every IDC-run task instead of calling lower-level skills
directly.

## Arguments

```text
$ARGUMENTS
```

`$ARGUMENTS` may be:

- a raw idea.
- a structured coding request.
- a TR3 design document.
- an approved Alignment Pack reference.
- a resume checkpoint reference routed by `references/workflows/resume-policy.md`.
- a request to route a task into Dynamic Scenario / Domain Module / General fallback.

## Required Routing

Invoke the orchestration skill:

```text
.claude/skills/idc-workflow/SKILL.md
```

Then route through:

```text
references/workflows/input-adapter.md                    # Input Adapter policy
  -> Intent Maturity Router
  -> references/workflows/resume-policy.md if resuming from checkpoint # Resume policy
  -> references/workflows/scenario-router.md             # Scenario Router policy
  -> references/workflows/domain-module-router.md if matched # Domain Module Router if matched
  -> references/workflows/lane-resolver.md               # Lane Resolver policy
  -> references/workflows/contract-gate.md               # Contract Gate policy
  -> references/workflows/requirement-assessor.md        # Requirement Assessor policy
  -> references/human-views/                             # Human View templates
```

After Human Alignment approval, continue through:

```text
references/workflows/automated-closure-loop.md           # Automated Closure Loop policy
  -> references/workflows/execution-unit-policy.md       # Execution Unit Planner policy
  -> references/workflows/progressive-constraint-loading.md # Progressive Constraint Loading
  -> .claude/skills/idc-skill-adapter-router/SKILL.md if GC / original-repo abilities are needed # Skill Adapter Router if GC / original-repo abilities are needed
  -> references/workflows/delegation-router.md           # Delegation Router policy
  -> references/workflows/knowledge-gate.md              # Knowledge Gate policy
  -> references/workflows/provider-selection-matrix.md   # Provider Selection policy
  -> references/workflows/repo-context-providers.md      # Repo Context Provider policy
  -> Execution
  -> references/workflows/tdd-state-machine.md if TDD is required # TDD State Machine
  -> references/workflows/lane-completion.md             # Lane Completion policy
  -> references/schemas/verification-contract.schema.yaml # Evidence Gate contract
  -> references/workflows/vertical-slice-readiness-gate.md # Vertical Slice Readiness policy
  -> references/human-views/                             # Completion View / Escalation View
```

## Output Surface

Show only one default Human View:

```text
raw idea -> Brainstorming View
missing critical fields -> Clarification View
ready for approval -> Alignment View
blocked -> Escalation View
done -> Completion View
```

Do not show raw YAML as the primary user interface.

## Hard Rules

- `/id-workflow` is the only user-facing entry command.
- Do not call `idc-d3a-coding`, `idc-gc-sop-adapter`, `idc-dt-design`, or `idc-dt-writer` directly from user intent before IDC routing.
- D3A is a custom Domain Module, not a Core special case.
- Dynamic Scenario is available for non-domain tasks that still need dynamic orchestration.
- General Coding is fallback for simple ordinary coding tasks.
- GC SOP and original-repo skills must go through Skill Adapter Router.
- The third GC original-repo skill remains `<ENTERPRISE_GC_THIRD_SKILL_NAME>` until named in the confidential zone.
- Completion must be based on tool evidence, not model confidence.
- Keep enterprise paths, APIs, commands, logs, tests, and SOP internals as placeholders outside the confidential environment.
