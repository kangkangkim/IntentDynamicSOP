# QUICKSTART

This guide is the shortest path from the shared IDC harness to a confidential
team setup. The goal is "fill parameters, then run one vertical slice."

## Step 1: Copy The Harness

Copy this repository into your confidential environment.

Do not add real enterprise paths, commands, logs, APIs, or internal skill names
to the shared public harness.

## Step 2: Create Team Config

Copy:

```sh
cp team-config.yaml.template team-config.yaml
```

`team-config.yaml` is ignored by git and is the only place a team should put
real local parameters.

## Step 3: Fill Team Basics

Fill:

```yaml
team:
  id: <TEAM_ID>
  repo_path: <REPO_PATH>
  skill_base_path: <SKILL_BASE_PATH>
```

## Step 4: Select Domain

For D3A:

```yaml
domain:
  use_d3a: true
  custom_domain_id: null
```

For another team domain, set `use_d3a: false` and fill `custom_domain_id`.

Real DT domains replace the repo placeholder registry wholesale:

```yaml
domain:
  d3a_dt_domains:
    - id: <DT_ID>
      knowledge_ref: <ENTERPRISE_DT_KNOWLEDGE_REF>
```

Non-empty replaces `registries/dt-domains.yaml` (no merge); empty falls back to
the repo defaults. General Coding teams do the same via `general.components`
and `general.test_domains` (they replace `general-components.yaml` /
`general-test-domains.yaml` wholesale).

D3A keeps the fixed user-designed workflow. The config only binds knowledge,
skills, commands, and evidence sources into that workflow.

## Step 5: Fill Skill Bindings

Fill only skills your team already has. Leave missing skills as `null`.

```yaml
bindings:
  brainstorming:
    skill_ref: <ENTERPRISE_BRAINSTORMING_SKILL_REF>
  dt_build:
    skill_ref: <ENTERPRISE_DT_BUILD_SKILL_REF>
    build_command: <ENTERPRISE_DT_BUILD_COMMAND>
    run_command: <ENTERPRISE_DT_RUN_COMMAND>
  tran_build:
    skill_ref: <ENTERPRISE_TRAN_BUILD_SKILL_REF>
    command: <ENTERPRISE_TRAN_BUILD_COMMAND>
```

Unfilled GC SOP atoms are skipped unless the Skill Adapter Router sees a
matching capability, stage, contract, and binding.

## Step 6: Fill Knowledge Indexes

Bind existing enterprise knowledge by path or reference. Do not copy the full
knowledge body into the shared harness.

```yaml
knowledge:
  architecture_doc: <ENTERPRISE_ARCHITECTURE_DOC_REF>
  feature_docs_root: <ENTERPRISE_FEATURE_DOCS_ROOT>
  layer_docs:
    DO: <ENTERPRISE_D3A_DO_KNOWLEDGE_REF>
  verification_mapping_ref: <ENTERPRISE_LAYER_TO_DT_MAPPING_REF>
```

DT knowledge refs ride on the `domain.d3a_dt_domains` entries shown in Step 4;
`knowledge.dt_docs` no longer exists.

## Step 7: Fill Build Commands

Fill the commands and pass condition used by your team:

```yaml
build:
  dt_build_command: <ENTERPRISE_DT_BUILD_COMMAND>
  dt_run_command: <ENTERPRISE_DT_RUN_COMMAND>
  tran_build_command: <ENTERPRISE_TRAN_BUILD_COMMAND>
  tran_build_pass_condition: <ENTERPRISE_TRAN_BUILD_PASS_CONDITION_REF>
```

## Step 8: Validate Harness

Run:

```sh
python3 tests/test_harness.py
```

All tests should pass before the first confidential run. In the confidential
copy the same command also validates the filled `team-config.yaml`: unfilled
placeholders, non-existent `skill_ref` targets, inconsistent `domain` settings,
and leftover placeholder commands are reported before the first run.

## Step 9: Run One Vertical Slice

Start with the smallest D3A slice:

```text
1 Layer
1 DT Domain
1 verification mapping
1 repo context provider
RED evidence
GREEN evidence
tran_build PASS
Completion Summary
```

Do not model every GC SOP atom or every D3A knowledge source on day one.
