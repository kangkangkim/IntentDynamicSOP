# Transfer To Test

Transfer To Test is a TDD workflow extension shared by all teams.

It reads skill refs from:

```text
team-config.yaml.bindings.system_test.skill_ref
```

## When To Use

Use after `ATOMIC_COMMIT_CREATED` or `BUILD_GREEN` when the lane or domain
requires a handoff to system testing.

## Flow

```text
ATOMIC_COMMIT_CREATED | BUILD_GREEN
  -> TRANSFER_TO_TEST
  -> TEST_HANDOFF_RECORDED
```

## Output

```yaml
transfer_to_test:
  system_test_skill_ref: team-config.yaml.bindings.system_test.skill_ref
  handoff_ref: <ENTERPRISE_SYSTEM_TEST_HANDOFF_REF>
  evidence_refs: []
  status: TEST_HANDOFF_RECORDED | SKIPPED | BLOCKED
```

## Hard Rules

- Do not hard-code system test paths or commands.
- System test handoff does not replace `tran_build PASS`.
- If `system_test.skill_ref` is null, skip unless team policy requires transfer.
