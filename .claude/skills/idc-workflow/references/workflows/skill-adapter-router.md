# Skill Adapter Router

Skill Adapter Router decides when IDC may call a reusable skill adapter under
`.claude/skills/`.

It is a framework-level router for dynamic scenarios and custom domain
scenarios. It does not know enterprise implementation details.

Adapter selection is registry-driven, not name-driven. The router reads:

```text
references/registries/skill-adapters.yaml
team-config.yaml
```

and matches the current execution need against `capability_keys`,
`allowed_stages`, `requires`, `blocks_when`, and the team-filled binding values
in `team-config.yaml`.

## Routing Order

```text
Input Adapter
  -> Scenario Router
  -> Domain Module Router if matched
  -> module Lane applicability, then Lane Resolver when applicable
  -> Contract Gate
  -> Human Alignment
  -> Capability Selector
  -> Skill Adapter Router selects inner atomic adapters
  -> Delegation Contract + Execution Authorization
  -> dispatched Domain executor loads outer execution Skill
  -> executor invokes selected GC / original-repo atomic adapter
  -> Evidence Gate
```

## Supported Adapter Classes

```text
public_methodology_adapter
enterprise_gc_sop_adapter
original_enterprise_repo_skill_adapter
domain_module_execution_skill
```

## Selection Algorithm

```text
capability_selection_result + selected_stage + approved contracts
  -> load adapter registry
  -> load .idc/effective-team-config.yaml
  -> filter rows by capability_keys
  -> filter rows by allowed_stages
  -> verify required inputs / mapping refs / team-config bindings
  -> reject rows with active blocks_when conditions
  -> choose the most specific executable adapter
  -> return NEEDS_ADAPTER_MAPPING if no row matches
```

Do not infer adapter use from the skill name alone. A skill named with `gc`,
`dt`, or `superpowers` is still unusable unless a registry row matches the
current execution unit.

## GC SOP Integration

Enterprise GC full-suite SOP is integrated as:

```text
.claude/skills/idc-gc-sop-adapter/SKILL.md
```

Known original-repository skill adapters:

```text
.claude/skills/idc-dt-design/SKILL.md
.claude/skills/idc-dt-writer/SKILL.md
.claude/skills/idc-gc-third-skill-placeholder/SKILL.md
```

The third skill remains a placeholder until the confidential environment
provides the real skill name and contract.

## Rules

- Adapter selection must come from `references/registries/skill-adapters.yaml`.
- Concrete skill refs, repo paths, and knowledge refs must come from `team-config.yaml`; commands and pass/fail logic stay inside bound skills.
- A configured binding is only available. Execute it only when Capability Selector selected it for the current unit and stage.
- Adapter routing before delegation is selection only. Repository-mutating
  adapter invocation occurs inside the authorized executor, never in main agent.
- In General Domain, `idc-general-coding` remains the outer execution protocol;
  selected GC adapters are inner abilities and cannot replace it.
- Team-specific capability rows come from validated `adapter_extensions`; do not edit the shared registry during adoption.
- If no registry row matches, return `NEEDS_ADAPTER_MAPPING`.
- Do not use `gc` / `dt` / `superpowers` naming as a trigger by itself.
- Dynamic scenarios may use GC atoms only after Human Alignment approval.
- D3A may use GC atoms only inside D3A module constraints.
- `idc-dt-design` can produce DT design artifacts, not RED/GREEN evidence.
- `idc-dt-writer` can produce DT changes and RED/GREEN evidence refs, but cannot mark DONE.
- Placeholder adapters are not executable.
- Adapter output must be summarized and bounded.
- Full enterprise logs, paths, APIs, commands, and SOP internals must stay out of the external harness.

## Output Shape

```yaml
skill_adapter_route:
  selected_adapter: idc-gc-sop-adapter | idc-dt-design | idc-dt-writer | idc-gc-third-skill-placeholder
  selected_stage: planning | dt_design | dt_writing | implementation | debugging | review | verification
  requested_capability_keys: []
  capability_selection_ref: string
  registry_match_ref: references/registries/skill-adapters.yaml
  route_reason: string
  input_contract_ref: string
  expected_output_contract_ref: string
  evidence_ref_required: true
  executable: true
  no_match_result: NEEDS_ADAPTER_MAPPING
```
