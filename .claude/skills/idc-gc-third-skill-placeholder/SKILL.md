---
name: idc-gc-third-skill-placeholder
description: Placeholder adapter for the third original enterprise repository skill in the GC full-suite SOP; replace only after team-config onboarding, once the real skill name and contract are known.
---

# GC Third Skill Placeholder

The user described three original-repository skills but only identified:

```text
idc-dt-design
idc-dt-writer
```

This placeholder reserves the third adapter slot without inventing enterprise
details.

## When To Use

Do not execute this placeholder in the external harness.

After team-config onboarding, replace it only once the real third skill has:

- a real name.
- entry conditions.
- input contract.
- output contract.
- allowed paths / forbidden paths rules.
- evidence rules.
- escalation rules.

## Output

```yaml
third_skill_placeholder:
  status: NOT_EXECUTABLE
  required_confidential_inputs:
    - <ENTERPRISE_GC_THIRD_SKILL_NAME>
    - <ENTERPRISE_ORIGINAL_REPO_SKILL_REF>
    - <ENTERPRISE_THIRD_SKILL_CONTRACT_REF>
```

## Hard Rules

- Do not guess the third skill's purpose.
- Do not map it to an IDC workflow until a team-config contract exists.
- Do not treat this placeholder as an executable skill.

Placeholder refs:

```text
<ENTERPRISE_GC_THIRD_SKILL_NAME>
<ENTERPRISE_ORIGINAL_REPO_SKILL_REF>
<ENTERPRISE_PLACEHOLDER>
```
