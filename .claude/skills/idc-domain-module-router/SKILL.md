---
name: idc-domain-module-router
description: Use inside /id-workflow when scenario-router selects DOMAIN_MODULE; load the selected module contract and route to its workflow without expanding internal enterprise knowledge.
---

# Domain Module Router Skill

Route to a registered Domain Module.

## When To Use

Use only when `scenario_route.route = DOMAIN_MODULE`.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/domain-module-router.md
.claude/skills/idc-workflow/references/schemas/domain-module.schema.yaml
.claude/skills/idc-workflow/references/domains/registry.yaml
```

Then read only the selected module file.

## Output

```yaml
domain_module_route:
  selected_module: d3a | general | <ENTERPRISE_PLACEHOLDER>
  module_file: string
  workflow_entrypoint: string
  required_contracts: []
  completion_gate: string
```

## Hard Rules

- Do not select module-internal layers.
- Do not select module-internal test domains.
- Do not read real enterprise knowledge in the external harness.
- Do not call GC SOP atoms directly; use `skill-adapter-router`.
