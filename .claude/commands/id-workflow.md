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
- a resume checkpoint reference.
- a request to route a task into Dynamic Scenario / Domain Module / General fallback.

## Required Routing

Invoke the orchestration skill:

```text
.claude/skills/idc-workflow/SKILL.md
```

Then route through:

```text
.claude/skills/idc-input-adapter/SKILL.md                # Input Adapter
  -> Intent Maturity Router
  -> .claude/skills/idc-scenario-router/SKILL.md         # Scenario Router
  -> .claude/skills/idc-domain-module-router/SKILL.md if matched # Domain Module Router if matched
  -> .claude/skills/idc-lane-resolver/SKILL.md           # Lane Resolver
  -> .claude/skills/idc-contract-gate/SKILL.md           # Contract Gate
  -> .claude/skills/idc-requirement-assessor/SKILL.md    # Requirement Assessor
  -> .claude/skills/idc-output-surface-router/SKILL.md   # Human View
```

After Human Alignment approval, continue through:

```text
.claude/skills/idc-automated-closure/SKILL.md            # Automated Closure Loop
  -> .claude/skills/idc-execution-unit-planner/SKILL.md  # Execution Unit Planner
  -> .claude/skills/idc-progressive-constraint-loader/SKILL.md # Progressive Constraint Loading
  -> .claude/skills/idc-skill-adapter-router/SKILL.md if GC / original-repo abilities are needed # Skill Adapter Router if GC / original-repo abilities are needed
  -> .claude/skills/idc-delegation-router/SKILL.md       # Delegation Router
  -> .claude/skills/idc-knowledge-gate/SKILL.md          # Knowledge Gate
  -> .claude/skills/idc-provider-selection/SKILL.md      # Provider Selection
  -> .claude/skills/idc-repo-context-provider/SKILL.md   # Repo Context Provider
  -> Execution
  -> .claude/skills/idc-tdd-state-machine/SKILL.md if TDD is required # TDD State Machine
  -> .claude/skills/idc-lane-completion/SKILL.md         # Lane Completion
  -> .claude/skills/idc-evidence-gate/SKILL.md           # Evidence Gate
  -> .claude/skills/idc-output-surface-router/SKILL.md   # Completion View / Escalation View
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
- Do not call `d3a-coding`, `gc-sop-adapter`, `dt-design`, or `dt-writer` directly from user intent before IDC routing.
- D3A is a custom Domain Module, not a Core special case.
- Dynamic Scenario is available for non-domain tasks that still need dynamic orchestration.
- General Coding is fallback for simple ordinary coding tasks.
- GC SOP and original-repo skills must go through Skill Adapter Router.
- The third GC original-repo skill remains `<ENTERPRISE_GC_THIRD_SKILL_NAME>` until named in the confidential zone.
- Completion must be based on tool evidence, not model confidence.
- Keep enterprise paths, APIs, commands, logs, tests, and SOP internals as placeholders outside the confidential environment.
