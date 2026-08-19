# Implementation Review

Implementation Review is a TDD workflow extension shared by all teams.

It reads skill refs from:

```text
team-config.yaml.bindings.impl_review.skill_ref
team-config.yaml.bindings.coding_standard.skill_ref
```

## When To Use

Use after `IMPLEMENTING` and before `GREEN_CONFIRMED` when lane, domain, or team
policy requires implementation review.

## Flow

```text
IMPLEMENTING
  -> IMPL_REVIEW
  -> REVIEW_PASS
  -> GREEN_CONFIRMED
```

If review fails:

```text
REVIEW_FAIL
  -> DEFECT_FIX
  -> DT_REVERIFY
```

## Output

```yaml
implementation_review:
  impl_review_skill_ref: team-config.yaml.bindings.impl_review.skill_ref
  coding_standard_skill_ref: team-config.yaml.bindings.coding_standard.skill_ref
  review_evidence_ref: <ENTERPRISE_IMPL_REVIEW_EVIDENCE_REF>
  required_fixes: []
  status: REVIEW_PASS | REVIEW_FAIL | BLOCKED
```

## Hard Rules

- Do not hard-code review tool paths.
- Review evidence is quality evidence, not DONE evidence by itself.
- If review is required and `impl_review.skill_ref` is null, return `NEEDS_TEAM_CONFIG`.
