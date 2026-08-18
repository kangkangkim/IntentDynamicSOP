# Team Customization

This skill package is the delivery unit for Claude Code.

Most teams should start here:

```text
.claude/skills/idc-workflow/
```

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

Change these files when adopting the workflow:

```text
references/domains/template-domain/
references/domains/registry.yaml
references/registries/general-components.yaml
references/registries/general-test-domains.yaml
CONTEXT_ENGINEERING.md
references/workflows/provider-selection-matrix.md
references/workflows/repo-context-providers.md
assets/README.md
```

## What D3A Teams Fill In Confidentially

Only inside the confidential environment, fill placeholders for:

```text
references/registries/d3a-layers.yaml
references/registries/dt-domains.yaml
references/domains/d3a/module.yaml
references/workflows/d3a-workflow.md
```

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
