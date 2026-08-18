# Skill Adapter Router

Skill Adapter Router decides when IDC may call a reusable skill adapter under
`.claude/skills/`.

It is a framework-level router for dynamic scenarios and custom domain
scenarios. It does not know enterprise implementation details.

## Routing Order

```text
Input Adapter
  -> Scenario Router
  -> Domain Module Router if matched
  -> Lane Resolver
  -> Contract Gate
  -> Human Alignment
  -> Skill Adapter Router
  -> selected GC / original-repo skill adapter
  -> Evidence Gate
```

## Supported Adapter Classes

```text
public_methodology_adapter
enterprise_gc_sop_adapter
original_enterprise_repo_skill_adapter
domain_module_execution_skill
```

## GC SOP Integration

Enterprise GC full-suite SOP is integrated as:

```text
.claude/skills/gc-sop-adapter/SKILL.md
```

Known original-repository skill adapters:

```text
.claude/skills/dt-design/SKILL.md
.claude/skills/dt-writer/SKILL.md
.claude/skills/gc-third-skill-placeholder/SKILL.md
```

The third skill remains a placeholder until the confidential environment
provides the real skill name and contract.

## Rules

- Dynamic scenarios may use GC atoms only after Human Alignment approval.
- D3A may use GC atoms only inside D3A module constraints.
- `dt-design` can produce DT design artifacts, not RED/GREEN evidence.
- `dt-writer` can produce DT changes and RED/GREEN evidence refs, but cannot mark DONE.
- Placeholder adapters are not executable.
- Adapter output must be summarized and bounded.
- Full enterprise logs, paths, APIs, commands, and SOP internals must stay out of the external harness.

## Output Shape

```yaml
skill_adapter_route:
  selected_adapter: gc-sop-adapter | dt-design | dt-writer | gc-third-skill-placeholder
  selected_stage: planning | dt_design | dt_writing | implementation | debugging | review | verification
  route_reason: string
  input_contract_ref: string
  expected_output_contract_ref: string
  evidence_ref_required: true
  executable: true
```
