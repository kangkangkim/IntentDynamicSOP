---
name: idc-scenario-router
description: Use inside /id-workflow after input-adapter to choose DOMAIN_MODULE, DYNAMIC_SCENARIO, GENERAL_CODING fallback, or NEED_TRIAGE without reading domain internals.
---

# Scenario Router Skill

Choose the top-level route.

## When To Use

Use after `input-adapter` has produced `normalized_request`.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/scenario-router.md
.claude/skills/idc-workflow/references/domains/registry.yaml
```

## Output

```yaml
scenario_route:
  route: DOMAIN_MODULE | DYNAMIC_SCENARIO | GENERAL_CODING | NEED_TRIAGE
  selected_module: string
  confidence_reason: string
  next: string
```

## Hard Rules

- Do not inspect domain layer details.
- Do not choose D3A layers or DT domains.
- D3A is a custom Domain Module, not a Core special case.
- Use `DYNAMIC_SCENARIO` for non-domain work that still needs dynamic orchestration.
- Use `GENERAL_CODING` only as simple fallback.
