---
name: idc-repo-context-provider
description: Use after provider-selection to collect bounded repository facts with evidence refs from grep, CodeGraph, OKL, or repo search.
---

# Repo Context Provider Skill

Collect bounded repository context.

## When To Use

Use after `provider-selection`.

## Reads

```text
.claude/skills/idc-workflow/references/workflows/repo-context-providers.md
.claude/skills/idc-workflow/references/schemas/repo-context-provider.schema.yaml
```

## Output

```yaml
context_provider_result:
  provider: grep | codegraph | okl | repo_search
  status: SUCCESS | EMPTY | ERROR | PLACEHOLDER
  summary: string
  evidence_ref: string
  refs: []
```

## Hard Rules

- Return summaries and refs, not full logs or full search results.
- Respect `max_results: 10` and `max_snippet_chars: 800`.
- Every result requires `evidence_ref`.
- Repository context is not DONE evidence.
