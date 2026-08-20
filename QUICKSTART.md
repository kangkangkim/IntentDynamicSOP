# QUICKSTART

This is the shortest path from the shared IDC harness to a confidential team
setup. A team authors one file: `team-config.yaml`.

For a General Coding team, the smallest valid file is:

```yaml
config_version: 1
team: {id: my-team, repo_path: /repos/my-team}
domain: {mode: general}
bindings: {}
```

Lane defaults, autonomous profiles, capability budgets, and disabled
self-optimization are materialized safely. Add only the Skill and knowledge
bindings the team can really execute.

## Step 1: Copy The Harness

Copy this repository into the confidential environment. Do not add enterprise
paths, commands, logs, APIs, or internal skill names to the public harness.

## Step 2: Create Team Config

```sh
cp team-config.yaml.template team-config.yaml
```

`team-config.yaml` is ignored by git. Files generated under `.idc/` are
read-only runtime state and are not a second configuration entry.

## Step 3: Fill Team Basics

```yaml
config_version: 1
team:
  id: <TEAM_ID>
  repo_path: <REPO_PATH>
```

## Step 4: Select Or Define Domain

Use a built-in Domain:

```yaml
domain:
  mode: d3a # or general
```

D3A DT domains may replace the public defaults wholesale:

```yaml
domain:
  mode: d3a
  d3a:
    dt_domains:
      - id: <DT_ID>
        knowledge_ref: <ENTERPRISE_DT_KNOWLEDGE_REF>
```

For a Custom Domain, fill `domain.custom` in the same file. Include trigger
rules, Lane policy, coding/test registries, required contracts, and workflow,
planner, and completion skill refs. Do not edit the shared Domain registry.

## Step 5: Fill Skill Bindings

Bindings declare which enterprise capabilities are available. They do not cause
every skill to execute.

```yaml
bindings:
  tech_design:
    skill_ref: <ENTERPRISE_TECH_DESIGN_SKILL_REF>
  dt_design:
    skill_ref: <ENTERPRISE_DT_DESIGN_SKILL_REF>
  dt_writer:
    skill_ref: <ENTERPRISE_DT_WRITER_SKILL_REF>
  dt_build:
    skill_ref: <ENTERPRISE_DT_BUILD_SKILL_REF>
  tran_build:
    skill_ref: <ENTERPRISE_TRAN_BUILD_SKILL_REF>
```

Add capabilities outside the fixed slots through `adapter_extensions`. Each
extension declares capability keys, stages, Lane/profile eligibility, signals,
and a skill ref. Shared registries remain unchanged.

## Step 6: Fill Knowledge Indexes

```yaml
knowledge:
  architecture_doc_ref: <ENTERPRISE_ARCHITECTURE_DOC_REF>
  feature_docs_root_ref: <ENTERPRISE_FEATURE_DOCS_ROOT>
  layer_docs:
    DO: <ENTERPRISE_D3A_DO_KNOWLEDGE_REF>
  verification_mapping_ref: <ENTERPRISE_LAYER_TO_DT_MAPPING_REF>
  repo_context:
    provider_skill_ref: <ENTERPRISE_REPO_CONTEXT_SKILL_REF>
    policy_ref: <ENTERPRISE_PROVIDER_POLICY_REF>
    fallback: bounded_grep
```

Only refs belong here. Knowledge bodies remain in enterprise storage.

## Step 7: Configure Capability Selection

```yaml
capability_selection:
  mode: autonomous_minimal_sufficient
  lane_profiles:
    fast: {max_optional_skills: 1}
    lite: {max_optional_skills: 3}
    complex: {max_optional_skills: null}
  d3a_profile: {max_optional_skills: null}
  require_selected_and_skipped_reasons: true
```

Then configure each Lane's executable Skill policy under `lane.profiles`:

```yaml
lane:
  default: lite
  profiles:
    lite:
      skills:
        allow: [tech_design, phase_plan, ut_design]
        deny: []
        required: [tech_design]
      orchestration:
        mode: autonomous
        steps:
          - id: lite-plan
            stage: planning
            skill_ids: [tech_design, phase_plan]
            trigger_signals: []
```

`autonomous` runs configured step Skills first and may add the smallest useful
set. `ordered` runs only the matching step in configured order; a missing stage
mapping blocks with `NEEDS_ORCHESTRATION_MAPPING`. Resolver rejects a Skill ID
that is unbound, unknown, Lane-ineligible, or assigned to an unsupported stage.
The three `max_optional_skills` values are defaults, not constants; set any of
them to a non-negative integer or `null` to match the team's SOP.

Fast, Lite, and Complex independently choose the smallest sufficient set from
the bound skills. D3A uses its workflow stage and Layer Context Packet instead
of a Lane.

## Step 8: Validate And Resolve

Normal `idc-workflow` usage runs preflight automatically and atomically rebuilds
effective config. The team still edits only `team-config.yaml`. The commands
below are optional diagnostics and CI checks:

```sh
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config team-config.yaml \
  --check

ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config team-config.yaml \
  --output .idc/effective-team-config.yaml

python3 tests/test_harness.py
```

Resolver rejects command keys, missing skill refs, invalid Domain definitions,
unsafe self-optimization settings, and malformed adapter extensions.

Portable Skill references:

- `'team://skills/example/SKILL.md'`: relative to `team.repo_path`.
- `'harness://.claude/skills/idc-example/SKILL.md'`: relative to IDC Core.
- plain relative path: team repo first, IDC Core second.
- absolute path or URI: retained as supplied.

## Step 9: Run One Vertical Slice

Start with:

```text
1 execution unit or D3A Layer
1 test/DT domain
1 verification mapping
1 repo context provider
Capability Selection result
RED evidence when TDD is required
GREEN evidence
required build PASS
Completion Summary
```

Inspect both selected and skipped capability reasons. A configured GC skill that
never becomes eligible should be fixed in its capability mapping, not forced to
run globally.
