# Team Customization

This skill package is the delivery unit for Claude Code.

Most teams should start here:

```text
.claude/skills/idc-workflow/
```

## Multi-Team Reuse Model

IDC is designed as a shared framework plus team-owned DIY layers:

```text
IDC Core
  shared by multiple teams
  owns idc-workflow skill, router policy, lane policy, gates, schemas, human views,
  adapter eligibility registry

Team Binding
  owned by the adopting team in a private team location
  owns team-config.yaml with Domain selection/definition, repository paths,
  internal skill refs, adapter extensions, and knowledge indexes

Generated Runtime
  owned by idc-team-config
  materializes read-only .idc/effective-team-config.yaml
```

Default adoption rule: reuse IDC Core unchanged and describe all team variation
through `team-config.yaml`.

The maintained v2 contract is [Team Config v2](../idc-team-config/references/team-config-v2.md).
The protected sequence is [Runtime lifecycle](../idc-team-config/references/runtime-lifecycle.md).

Execution order belongs to the selected v2 Pack policy, with explicit team Lane
profiles overriding only their matching Lane:

- General and lane-applicable Custom Domains use `lane.profiles.fast|lite|complex`.
- D3A remains Lane N/A and consumes its fixed Pack workflow.
- A self-developed Custom Domain maintains its own Pack assets.

Core still owns Alignment, Contract, Knowledge, authorization, and Completion
gates. Ordered steps are executable policy, not visualization.

Start by copying:

```text
team-config.yaml.template -> team-config.yaml
```

`team-config.yaml` is the fill-parameters entrypoint. Leave values null to use
framework defaults, built-in fallbacks, or skip optional abilities.

## Skills vs Assets

Active behavior should become skills.

Passive materials should become assets / references:

```text
assets/README.md
references/schemas/
references/registries/
references/human-views/
references/knowledge/
docs/
examples/
```

Do not turn schemas, registries, examples, evidence files, or knowledge templates
into skills.

## What Teams Usually Change

An adopting team changes exactly one file:

```text
team-config.yaml
```

Shared registries are read-only defaults. v2 definition registry overrides
replace the selected Pack registry wholesale; do not edit shared registry files.

List every supported route in `domains.enabled`, set `domains.default`, and map
each enabled ID to a Pack in `domains.definitions`. Do not edit the shared Domain
registry.

For multi-team reuse, do not put concrete team paths or commands into the shared
adapter registry. Keep `references/registries/skill-adapters.yaml` as the common
eligibility table, and let each adopting team provide private values in:

```text
team-config.yaml
```

The shared registry answers "which adapter may run here"; the team binding
answers "where and how this team runs it".

Team-specific capabilities use `adapter_extensions`; Resolver appends validated
rows to the effective registry without changing the shared registry.

If your company already has a Brainstorming capability, bind it as
`idc-brainstorming` in `team-config.yaml` and normalize its output to the IDC
draft-spec fields. Do not copy company brainstorming prompts into the shared
harness.

If your company does not have Grill Me, keep using the GitHub-carried IDC
implementation:

```text
.claude/skills/idc-intent-grilling/SKILL.md
.claude/skills/idc-intent-grilling/references/grill-me-method.md
.claude/skills/idc-intent-grilling/assets/question-card-template.md
.claude/skills/idc-intent-grilling-with-docs/SKILL.md
.claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md
```

## Design A Team Alignment Flow

`alignment` is an ordered pre-alignment pipeline, not merely a list of Skill
paths. Teams may rebind a framework step, change its trigger signals, reorder
the non-gate steps, or add a team-owned step by declaring both its binding and
its position in the flow:

```yaml
alignment:
  bindings:
    team_tr3_review:
      skill_ref: team://skills/idc-team-tr3-review/SKILL.md
  orchestration:
    mode: ordered
    steps:
      - id: alignment-team-tr3-review
        stage: clarification
        skill_ids: [team_tr3_review]
        trigger_signals: [tr3_design_doc]
```

The complete configured section must still include the framework stages
`discovery`, `divergence`, `clarification`, and `alignment_check`, cover the
`raw_idea` and `critical_gaps_remain` signal floor, and leave the Human
Alignment check as the final approval gate. A TR3 step may use
`tr3_design_doc` to run for every TR3 input, while `critical_gaps_remain` and
`docs_clarification_required` retain conditional Grilling behavior.

## What D3A Teams Fill In Confidentially

Only inside the team configuration, fill real values in exactly one file:

```text
team-config.yaml
```

- Real DT domains and their knowledge refs live in a team registry referenced by
  `domains.definitions.d3a.registries.test_domains_ref` (wholesale replacement).
- Layer knowledge refs go to `knowledge.layer_docs`; the 7 layer names stay fixed.
- General Lane knowledge refs go to `knowledge.lane_docs.fast/lite/complex`; only the selected Lane is loaded.
- Skill refs go to `bindings.*`; commands and pass/fail logic remain inside those skills.

The repo registries (`d3a-layers.yaml`, `dt-domains.yaml`), `d3a/module.yaml`,
and `d3a-workflow.md` stay untouched placeholders in the team copy.

Keep the fixed D3A Coding Layer names:

```text
TRAN_CFG
DO
VISP_ADP
TFC_TFI
TFE
ADP
DRV
```

## What Not To Change First

Do not start by changing:

```text
SKILL.md
CONTEXT_ENGINEERING.md
references/workflows/lane-resolver.md
references/workflows/lane-completion.md
references/workflows/tdd-state-machine.md
references/schemas/
```

Change these only after the first vertical slice works. If a team needs different context loading behavior, prefer adding domain-specific provider rules before changing the orchestration contract.

## First Vertical Slice

Start with one small task:

```text
input
-> alignment
-> domain/lane decision
-> execution plan
-> evidence
-> completion summary
```

Do not try to model the whole company domain on day one.
