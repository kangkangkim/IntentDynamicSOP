---
name: idc-knowledge-gate
description: Use after Human Alignment approval and before execution to load only bounded domain knowledge and repository context needed for the selected execution unit.
---

# Knowledge Gate Skill

Load bounded knowledge.

## When To Use

Use before dispatching implementation, DT writing, debugging, or verification work.

## Reads

```text
.claude/skills/idc-workflow/CONTEXT_ENGINEERING.md
.claude/skills/idc-workflow/references/workflows/knowledge-gate.md
.claude/skills/idc-workflow/references/workflows/provider-selection-matrix.md
.claude/skills/idc-workflow/references/workflows/repo-context-providers.md
.claude/skills/idc-workflow/references/schemas/repo-context-provider.schema.yaml
```

## Output

```yaml
knowledge_packet:
  selected_unit_ref: string
  loaded_domain_refs: []
  repository_context_refs: []
  provider_results: []
  omitted_context: []
```

## Hard Rules

- Load only current execution unit context.
- Do not load all D3A knowledge at once.
- OKL, docs, CodeGraph, and grep are context, not DONE evidence.
- Every provider result needs `evidence_ref`.
