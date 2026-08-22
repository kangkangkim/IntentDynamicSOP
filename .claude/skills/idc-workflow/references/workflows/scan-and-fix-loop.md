# Scan And Fix Loop

Scan And Fix Loop is a TDD workflow extension shared by all teams.

It does not hard-code enterprise tool paths. It reads skill refs from:

```text
team-config.yaml.bindings.static_scan.skill_ref
team-config.yaml.bindings.defect_fix.skill_ref
```

## When To Use

Use after `GREEN_CONFIRMED` and before `ATOMIC_COMMIT_CREATED` when the selected lane
or domain requires static scan / defect fix evidence.

## Flow

```text
GREEN_CONFIRMED
  -> SCAN_RUNNING
  -> SCAN_GREEN
  -> ATOMIC_COMMIT_CREATED
```

If scan fails:

```text
SCAN_FAIL
  -> DEFECT_FIX
  -> DT_REVERIFY
  -> GREEN_CONFIRMED
```

## Output

```yaml
scan_and_fix:
  static_scan_skill_ref: team-config.yaml.bindings.static_scan.skill_ref
  defect_fix_skill_ref: team-config.yaml.bindings.defect_fix.skill_ref
  scan_evidence_ref: <ENTERPRISE_STATIC_SCAN_EVIDENCE_REF>
  fix_evidence_ref: <ENTERPRISE_DEFECT_FIX_EVIDENCE_REF>
  status: SCAN_GREEN | SCAN_FAIL | BLOCKED
```

## Hard Rules

- Do not hard-code scan or fix commands in this workflow.
- If `static_scan.skill_ref` is null and scan is required, return `NEEDS_TEAM_CONFIG`.
- If `defect_fix.skill_ref` is null after scan failure, return `NEEDS_TEAM_CONFIG`.
- Scan evidence cannot replace RED / GREEN / `tran_build` evidence.
