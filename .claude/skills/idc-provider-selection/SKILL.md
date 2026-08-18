---
name: idc-provider-selection
description: Use before repository context loading to choose bounded grep, CodeGraph, OKL, or repo search according to anchor and domain knowledge.
---

# Provider Selection Skill

Choose repository context providers.

## When To Use

Use inside Knowledge Gate before querying repo context.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/provider-selection-matrix.md
.claude/skills/idc-workflow/references/schemas/repo-context-provider.schema.yaml
```

## Output

```yaml
provider_selection:
  selected_providers: []
  queries: []
  max_results: 10
  max_snippet_chars: 800
  evidence_ref_required: true
```

## Hard Rules

- Use bounded grep first when code anchors are known.
- Use OKL only for summary / refs / keywords.
- Do not use OKL to override code facts.
- Do not treat provider output as test/build evidence.
