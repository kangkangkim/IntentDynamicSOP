# QUICKSTART

This is the shortest path from the shared IDC harness to the first verified
team task. A team authors one file: `team-config.yaml`. IDC owns all generated
runtime state.

For a General Coding team, the smallest valid file is:

```yaml
config_version: 1
team: {id: my-team, repo_path: /repos/my-team}
domain: {mode: general}
bindings: {}
```

Lane defaults, autonomous profiles, capability budgets, and disabled
self-optimization are materialized safely. Bind only Skills and knowledge that
the team can really execute.

## Step 1: Copy The Harness

Copy this repository into the confidential environment. Do not add enterprise
paths, commands, logs, APIs, knowledge bodies, or internal Skill names to the
public harness.

## Step 2: Create Team Config

```sh
cp team-config.yaml.template team-config.yaml
```

`team-config.yaml` is ignored by git. Files under `.idc/` are framework-owned,
read-only runtime state, not another configuration entry.

## Step 3: Configure Team And Domain

Fill the team identity and repository root:

```yaml
config_version: 1
team:
  id: <TEAM_ID>
  repo_path: <REPO_PATH>
```

Choose a built-in Domain:

```yaml
domain:
  mode: general # or d3a
```

General dynamically selects `fast`, `lite`, or `complex`. D3A never selects a
Lane and always materializes:

```yaml
lane_applicability: not_applicable
selected_lane: null
execution_profile: d3a_fixed_workflow
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
rules, `dynamic | fixed | not_applicable` Lane policy, coding/test registries,
required contracts, and workflow/planner/completion Skill refs. Do not edit the
shared Domain registry.

## Step 4: Bind Skills And Resolve Ownership

Bindings declare which enterprise capabilities are available. They do not
cause every Skill to execute, and real commands remain inside the bound Skill.

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

Add capabilities outside the fixed slots through `adapter_extensions`:

```yaml
adapter_extensions:
  - id: idc-team-api-review
    execution_role: atomic_capability
    capability_keys: [api_review]
    allowed_stages: [review]
    eligible_lanes: [lite, complex]
    execution_profiles: []
    trigger_signals: [api_semantic_change]
    skill_ref: <ENTERPRISE_API_REVIEW_SKILL_REF>
    evidence_required: true
    composes_with: []
    supersedes: []
```

Registration overlap is never resolved by name guessing:

- Leave both arrays empty when the capability is unique.
- Use `composes_with: [<SKILL_ID>]` when both Skills must run.
- Use `supersedes: [<SKILL_ID>]` when the team Skill replaces another Skill.
- Do not bind `idc-workflow`, General/D3A execution protocols, Human Alignment,
  or another orchestration Skill as an atomic capability.

Unresolved capability/stage/Lane/profile/trigger overlap blocks preflight.

## Step 5: Fill Knowledge Indexes

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

Only refs belong here. Knowledge bodies remain in enterprise storage and are
loaded progressively for the current stage or execution unit.

## Step 6: Configure Execution Profiles

Capability budgets control how many optional Skills Selector may add:

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

General and lane-applicable Custom Domains configure each Lane independently:

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
mapping blocks with `NEEDS_ORCHESTRATION_MAPPING`. Resolver rejects unbound,
unknown, Lane-ineligible, or stage-ineligible Skill IDs.

D3A does not configure a Lane workflow. Its fixed stages and Layer Context
Packets drive selection, while `d3a_profile` only limits optional atomic Skills.

## Step 7: Run Preflight

Run the same preflight that `$idc-workflow` executes automatically:

```sh
ruby .claude/skills/idc-team-config/scripts/prepare_runtime.rb
```

Continue only when it reports:

```yaml
runtime_preflight:
  status: READY
  registration_audit_status: PASS
  bootstrap_load_plan:
    status: READY
    load_policy: read_required_refs_only
```

Preflight atomically rebuilds `.idc/effective-team-config.yaml`, checks the
source digest, validates Skill registration conflicts, and dry-runs every
configured Lane step and required Skill through the real Selector. Its
bootstrap plan contains only Input, Scenario, and Domain Router references.

For diagnosis or CI, the lower-level checks remain available:

```sh
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config team-config.yaml \
  --check

python3 tests/test_harness.py
```

Portable Skill references:

- `'team://skills/example/SKILL.md'`: relative to `team.repo_path`.
- `'harness://.claude/skills/idc-example/SKILL.md'`: relative to IDC Core.
- plain relative path: team repository first, IDC Core second.
- absolute path or URI: retained as supplied.
- URI refs inside flow mappings must remain quoted, for example
  `{skill_ref: 'team://skills/example/SKILL.md'}`.

## Step 8: Run IDC Workflow

Use the Skill entry in Claude Code, not a `.claude/commands` alias:

```text
$idc-workflow <TASK_OR_TR3>
```

Natural-language matching is also supported. User questions, approval, and
re-alignment choices are emitted through `AskUserTool`.

The framework runs this chain automatically:

```text
Preflight
  -> Input / Intent Maturity
  -> Discovery or Clarification when needed
  -> Domain and Lane applicability
  -> Contract Gate
  -> Human Alignment approval
  -> Planning and execution-unit split
  -> Capability Selector
  -> Knowledge Demand and Knowledge Load Plan
  -> stage-specific Context Load Plan
  -> Delegation Contract
  -> Execution Authorization
  -> Subagent / Agent Team execution
  -> Knowledge Consumption Receipt verification
  -> Execution Receipt
  -> Completion Gate
```

Do not manually invoke every internal script during normal use. In particular,
the Execution Context Load Plan requires READY Capability and Knowledge plans
for the same execution unit. It keeps instruction refs, exact static knowledge,
search scopes, and repo context requirements separate.

## Step 9: Verify One Vertical Slice

For General Fast/Lite/Complex, verify:

```text
selected Lane matches task evidence
selected and skipped capability reasons are present
team allow / deny / required / ordered policy took effect
Context Load Plan excludes unselected Skills
Knowledge Load Plan contains only selected component/test-domain knowledge
Knowledge Consumption Result = VERIFIED
Execution Authorization = AUTHORIZED
Execution Receipt contains dispatch and executor refs
Lane Completion requirements have real test/build evidence
```

For D3A, verify:

```text
lane_applicability = not_applicable
selected_lane = null
execution_profile = d3a_fixed_workflow
1 initial Layer Context Packet
1 initial DT Domain and verification mapping
Knowledge Load Plan contains only the current Layer and required DT knowledge
DT RED before implementation
all required DT GREEN
tran_build PASS
Knowledge Consumption Result = VERIFIED with provider/search result refs
Execution Receipt and Completion Summary
```

A configured GC or DT Skill that never becomes eligible should be fixed in its
capability mapping or Lane/profile policy, not forced to run globally.
