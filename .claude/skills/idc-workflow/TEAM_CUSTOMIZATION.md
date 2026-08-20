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
  owned by the adopting team in a confidential location
  owns team-config.yaml with Domain selection/definition, repository paths,
  internal skill refs, adapter extensions, and knowledge indexes

Generated Runtime
  owned by idc-team-config
  materializes read-only .idc/effective-team-config.yaml
```

Default adoption rule: reuse IDC Core unchanged and describe all team variation
through `team-config.yaml`.

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

Shared registries (`dt-domains.yaml`, `general-components.yaml`,
`general-test-domains.yaml`) are read-only defaults: a non-empty
`domain.d3a.dt_domains` / `general.components` / `general.test_domains` in
`team-config.yaml` replaces the corresponding registry wholesale (never merge).
Do not edit shared registry files in the confidential copy.

Custom domains are adoption configuration: use `domain.mode: custom` and fill
the inline `domain.custom` contract. Do not edit the shared Domain registry.

For multi-team reuse, do not put concrete team paths or commands into the shared
adapter registry. Keep `references/registries/skill-adapters.yaml` as the common
eligibility table, and let each adopting team provide confidential values in:

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

## What D3A Teams Fill In Confidentially

Only inside the confidential environment, fill real values in exactly one file:

```text
team-config.yaml
```

- Real DT domains and their knowledge refs go to `domain.d3a.dt_domains`
  (non-empty replaces `dt-domains.yaml` wholesale, no merge).
- Layer knowledge refs go to `knowledge.layer_docs`; the 7 layer names stay fixed.
- Skill refs go to `bindings.*`; commands and pass/fail logic remain inside those skills.

The repo registries (`d3a-layers.yaml`, `dt-domains.yaml`), `d3a/module.yaml`,
and `d3a-workflow.md` stay untouched placeholders in the confidential copy.

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
