# Atomic Commit

Atomic Commit is a TDD workflow extension shared by all teams.

It does not hard-code git automation. It reads skill refs from:

```text
team-config.yaml.bindings.git_commit.skill_ref
```

## When To Use

Use after implementation, review, verification, and scan requirements are
satisfied for one bounded execution unit.

## Flow

```text
SCAN_GREEN | GREEN_CONFIRMED
  -> COMMIT_PREPARED
  -> ATOMIC_COMMIT_CREATED
  -> LAYER_COMPLETE
```

## Output

```yaml
atomic_commit:
  git_commit_skill_ref: team-config.yaml.bindings.git_commit.skill_ref
  changed_files: []
  evidence_refs: []
  commit_ref: <ENTERPRISE_COMMIT_REF>
  status: ATOMIC_COMMIT_CREATED | BLOCKED
```

## Hard Rules

- Do not create a commit before required evidence is present.
- Do not hard-code git commands in this workflow.
- If `git_commit.skill_ref` is null, use the runtime default only when the team policy allows it.
- One atomic commit must map to one bounded execution unit or one reviewed fix.
