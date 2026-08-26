# IDC Harness Setup

Interactive local prototype for onboarding a team's way of working into the
IDC harness — it authors the repository's single team-owned configuration
source: `team-config.yaml`.

Open it directly:

```sh
open prototypes/team-config-studio/index.html
```

The page supports:

- A wizard flow that walks a team through setup step by step, with
  skip (keep framework defaults), resume-from-draft, and per-step status.
- Importing an existing `team-config.yaml` and jumping straight to the
  visual strategy overview.
- Choosing task types as a real multi-select over `domain.enabled`
  (general / d3a / custom in any combination) with one primary route
  (`domain.mode`); General is selectable, not forced.
- Choosing and independently inspecting General, D3A, or an inline Custom Domain,
  with inline explainers for coding layers / test domains registries.
- Alignment presets for the framework's three input maturities
  (探索型 raw idea / 结构化型 structured / TR3 型 tr3_design_doc) that rewire
  `trigger_signals`, with a signal preview showing which steps fire per input.
- Adding and removing team-owned capability bindings (custom keys beyond the
  framework set), with reference protection while a lane still uses them.
- Knowledge layer-doc mapping linked to the enabled domains: quick-add chips
  for the fixed D3A layers (TRAN_CFG … DRV), add/remove rows, and a hint that
  pure-general teams may skip it.
- Expressing the real execution ownership of each Domain:
  - General delegates execution orchestration to Fast, Lite, and Complex Lane profiles.
  - D3A exposes replaceable DT/build Skill bindings while keeping its Harness-owned fixed workflow and completion gate locked.
  - Custom Domain binds Planner, Workflow, and Completion Skills and selects a dynamic, fixed, or not-applicable Lane policy.
- Editing registries, core Skill bindings, and Adapter Extensions.
- Adding, removing, editing, and dragging steps in the framework-constrained pre-alignment pipeline.
- Dragging bound Skills between Fast, Lite, and Complex Lane profiles.
- Adding, removing, editing, and dragging each Lane's execution steps.
- Compiling Alignment, Domain routing, Domain execution, Lane strategy, and Completion into one visual strategy overview.
- Live YAML generation, browser-side checks, draft persistence, and download.

The browser checks are advisory. The authoritative validation remains:

```sh
python3 .claude/skills/idc-team-config/scripts/resolve_team_config.py \
  --config team-config.yaml --check
```

## Tests

Run the self-check suite (Node 18+, Chrome installed for the headless smoke test):

```sh
node prototypes/team-config-studio/studio.test.mjs
```

It loads the real `script.js` in Node with DOM stubs and verifies:

- Default, UI-constructed General / D3A / Custom scenarios produce YAML that
  passes the authoritative Ruby resolver (including the rule that lane
  `allow`/`required`/`deny`/`steps` may only reference bound skill IDs).
- Round-trip fidelity over the five repository configs: import → merge →
  regenerate keeps semantics and resolver-clean.
- Fault injection is caught by the browser-side checks before export.
- The rendered page (Chrome headless) shows all sections, a Ready badge, and
  generates a screenshot at `/tmp/idc-studio-visual-check.png`.

Two resolver rules worth remembering when authoring configs by hand:

- Only atomic capability skills may be bound (e.g. `idc-gc-sop-adapter`);
  orchestration/outer-protocol skills such as `idc-general-coding` are
  rejected.
- Lane allow/required/deny lists and ordered step `skill_ids` must all
  reference bound skills or adapter extension IDs.
