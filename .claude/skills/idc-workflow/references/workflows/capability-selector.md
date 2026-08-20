# Capability Selector

Capability Selector converts configured enterprise skills into executable choices.

```text
Planner capability demands
  + current stage
  + contracts and observed signals
  + selected Lane or D3A execution profile
  + effective team bindings
  + team-capabilities registry
  -> minimal sufficient selected skills
  -> explicit skipped reasons
  -> Skill Adapter Router
```

## Selection order

1. Planner emits required and optional capability keys for each execution unit.
2. Load `.idc/effective-team-config.yaml`; a null binding is unavailable.
3. Join bindings with `registries/team-capabilities.yaml` and validated
   `adapter_extensions`.
   Apply declared `supersedes` before required/optional selection; intentional
   `composes_with` overlaps remain eligible together.
4. Filter by current stage and observed trigger signals.
5. For General/dynamic routes, apply the selected Lane capability profile.
   Apply `lane.profiles.<lane>.skills` before demand matching:
   - non-empty `allow` is an executable allowlist;
   - `deny` always removes a capability;
   - stage-compatible `required` skills are selected even without a demand signal.
6. Match `lane.profiles.<lane>.orchestration.steps` by `stage` and optional
   `trigger_signals`.
   - `autonomous`: run configured step skills first, then add the minimal set
     needed to cover required and optional capability demand.
   - `ordered`: run only matching step skills, in listed order. A stage without
     a matching step returns `NEEDS_ORCHESTRATION_MAPPING`.
7. For D3A, apply `d3a_fixed_workflow` eligibility and the current Layer Context
   Packet; do not manufacture a Lane.
8. Select all required matches, then the smallest useful optional set within the
   profile budget.
9. Emit execution order plus selected and skipped reasons before Skill Adapter
   Router executes them.

## Lane behavior

- Fast: current execution unit; template default is at most one optional Skill.
- Lite: current stage; template default is at most three optional Skills.
- Complex: may select across the execution DAG; template default has no fixed
  optional limit.

Teams may adjust each `max_optional_skills` to a non-negative integer or `null`.
The value is read from effective config at runtime; it is not hard-coded by the
Selector.

Required capabilities are never discarded to satisfy an optional budget. If a
required capability is unbound, return `NEEDS_ADAPTER_MAPPING`.

Lane configuration is runtime policy, not descriptive metadata. Resolver rejects
unknown, unbound, Lane-ineligible, or stage-ineligible Skill IDs so a typo cannot
silently fall back to the shared registry.

## Important distinction

```text
binding present != skill selected
skill selected != skill succeeded
skill succeeded != completion gate passed
```

Only tool evidence and the active Completion Gate can close the task.
