# Team Config Resolver

Team Config Resolver turns the single team-authored `team-config.yaml` into a
validated, read-only `.idc/effective-team-config.yaml`.

`idc-workflow` must call `idc-team-config/scripts/prepare_runtime.rb` before
request routing. The preflight regenerates effective config atomically on every
invocation and records `source_sha256`; stale generated state is never trusted.

```text
team-config.yaml
  -> schema validation
  -> prohibited command-key check
  -> skill/ref resolution
  -> Domain materialization
  -> registry replacement
  -> adapter-extension composition
  -> Lane skill-policy and orchestration validation
  -> capability-selection profile materialization
  -> Knowledge binding
  -> self-optimization policy check
  -> readiness result
  -> .idc/effective-team-config.yaml
```

## Domain materialization

- `mode: d3a` selects the built-in D3A module. Non-empty DT domains replace the
  default DT registry wholesale.
- `mode: general` selects the built-in General module. Non-empty component and
  test-domain lists replace their defaults wholesale.
- `mode: custom` creates an effective Domain Module from `domain.custom`; the
  team does not edit `domains/registry.yaml` or create another config file.
- `mode: d3a` and `mode: general` must be registered `status: active` in the
  shared domain module registry (`domains/registry.yaml`; overridable with the
  resolver's `--registry PATH`). An unregistered mode fails with
  `domain.mode <mode> is not registered in the domain module registry; register
  it or switch domain.mode`. `mode: custom` is exempt: it registers inline via
  `domain.custom`.

## Adapter materialization

The shared adapter registry remains the Core eligibility baseline. Resolver:

1. Binds its known capability rows from `bindings.*.skill_ref`.
2. Appends validated `adapter_extensions` for team-specific GC atoms and
   original-repository skills.
3. Rejects extensions that attempt to own Domain, Lane, Contract Gate, Human
   Alignment, or Completion Gate.
4. Runs registration conflict audit. Two Skills that overlap on capability key,
   stage, Lane/profile, and trigger are rejected unless the extension declares
   `composes_with` or `supersedes`.

The runtime router reads only the effective adapter set; no second team-authored
binding source exists.

Bindings only declare availability. `workflows/capability-selector.md` decides
which bound capabilities run for each stage and execution unit.

`composes_with` means both abilities may be selected. `supersedes` means the
eligible extension removes the listed capability before selection. Domain
execution and orchestration Skills cannot be registered as atomic extensions.

## Lane materialization

Each `lane.profiles.fast|lite|complex` block is validated against the effective
capability pool. Resolver rejects unknown or unbound Skill IDs, Lane-ineligible
references, ordered orchestration without steps, and steps that place a Skill in
an unsupported stage. The validated profile is copied into effective config and
is consumed directly by Capability Selector; it is never treated as a comment.

## Knowledge materialization

Every configured knowledge field has one consumer:

| Field | Consumer |
|---|---|
| `architecture_doc_ref` | Planner and Knowledge Gate |
| `feature_docs_root_ref` | Discovery and Knowledge Gate |
| `layer_docs` | Layer/Component Context Packet builder |
| `verification_mapping_ref` | Planner and Verification Mapping Gate |
| `repo_context.provider_skill_ref` | Repo Context Provider |
| `repo_context.policy_ref` | Provider Selection Matrix overlay |

## Failure behavior

Return `NEEDS_TEAM_CONFIG` with field-level errors. Do not fall back to a second
team binding file, edit shared registries, or guess a missing enterprise fact.

## Portable references

- Absolute Skill paths remain absolute.
- `team://path` resolves from `team.repo_path`.
- `harness://path` resolves from the IDC Core root.
- Plain relative paths try `team.repo_path` first, then IDC Core for built-in
  skills.
- Effective config stores resolved absolute file paths so later routers do not
  depend on the process working directory.

## Ownership

`team-config.yaml` is authored. `.idc/effective-team-config.yaml` is generated.
Team overlays proposed by self-optimization remain proposals until Human
Alignment approves promotion; they never mutate the source config automatically.
