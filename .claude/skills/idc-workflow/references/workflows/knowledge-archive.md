# Knowledge Archive

Knowledge Archive is a TDD workflow extension shared by all teams.

It reads skill refs from:

```text
team-config.yaml.bindings.knowledge_archive.skill_ref
```

It does not hard-code enterprise archive paths, commands, or internal skill
names.

## When To Use

Use after successful verification when a team requires durable knowledge capture
for decisions, pitfalls, evidence refs, or reusable implementation notes.

## Flow

```text
LAYER_COMPLETE
  -> KNOWLEDGE_ARCHIVE
  -> ARCHIVE_RECORDED
```

## Output

```yaml
knowledge_archive:
  knowledge_archive_skill_ref: team-config.yaml.bindings.knowledge_archive.skill_ref
  archived_refs: []
  summary_ref: <ENTERPRISE_KNOWLEDGE_ARCHIVE_REF>
  status: ARCHIVE_RECORDED | SKIPPED | BLOCKED
```

## Hard Rules

- Do not archive speculative decisions.
- Do not copy private knowledge into the shared harness.
- If `knowledge_archive.skill_ref` is null, skip unless team policy marks archive as required.
- Archive refs are knowledge, not RED / GREEN / build evidence.
