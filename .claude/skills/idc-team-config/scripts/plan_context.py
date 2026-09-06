#!/usr/bin/env python3
"""Migrated from plan_context.py; behavior is intended to be identical."""

import argparse
import os
import sys
from pathlib import Path

import yaml

PHASES = ["bootstrap", "decision", "planning", "execution", "completion", "resume"]
DOMAINS = ["general", "d3a", "custom"]
LANES = ["fast", "lite", "complex"]

ROOT = Path(__file__).resolve().parents[4]

COMMON_REFS = {
    "bootstrap": [
        ".claude/skills/idc-workflow/references/workflows/input-adapter.md",
        ".claude/skills/idc-workflow/references/workflows/scenario-router.md",
        ".claude/skills/idc-workflow/references/workflows/domain-module-router.md",
    ],
    "decision": [
        ".claude/skills/idc-workflow/references/constraints/decision/core-decision-constraints.yaml",
        ".claude/skills/idc-workflow/references/constraints/decision/contract-selection.yaml",
        ".claude/skills/idc-workflow/references/workflows/contract-gate.md",
        ".claude/skills/idc-workflow/references/workflows/requirement-assessor.md",
        ".claude/skills/idc-workflow/references/workflows/human-alignment.md",
        ".claude/skills/idc-workflow/references/schemas/alignment-pack.schema.yaml",
        ".claude/skills/idc-workflow/references/human-views/alignment-view.md",
    ],
    "planning": [
        ".claude/skills/idc-workflow/references/constraints/planning/core-planning-constraints.yaml",
        ".claude/skills/idc-workflow/references/workflows/execution-unit-policy.md",
        ".claude/skills/idc-workflow/references/workflows/knowledge-gate.md",
    ],
    "execution": [
        ".claude/skills/idc-workflow/references/constraints/execution/core-execution-constraints.yaml",
        ".claude/skills/idc-workflow/references/constraints/execution/context-loading.yaml",
        ".claude/skills/idc-workflow/references/workflows/automated-closure-loop.md",
        ".claude/skills/idc-workflow/references/workflows/progressive-constraint-loading.md",
        ".claude/skills/idc-workflow/references/workflows/capability-selector.md",
        ".claude/skills/idc-workflow/references/workflows/delegation-router.md",
        ".claude/skills/idc-workflow/references/workflows/execution-authorization-gate.md",
        ".claude/skills/idc-workflow/references/schemas/delegation-contract.schema.yaml",
        ".claude/skills/idc-workflow/references/schemas/execution-authorization.schema.yaml",
        ".claude/skills/idc-skill-adapter-router/SKILL.md",
    ],
    "completion": [
        ".claude/skills/idc-workflow/references/workflows/lane-completion.md",
        ".claude/skills/idc-workflow/references/schemas/verification-contract.schema.yaml",
        ".claude/skills/idc-workflow/references/schemas/escalation-policy.schema.yaml",
        ".claude/skills/idc-workflow/references/human-views/completion-view.md",
        ".claude/skills/idc-workflow/references/human-views/escalation-view.md",
    ],
    "resume": [
        ".claude/skills/idc-workflow/references/workflows/resume-policy.md",
        ".claude/skills/idc-workflow/references/schemas/runtime-state.schema.yaml",
        ".claude/skills/idc-workflow/references/schemas/delegation-contract.schema.yaml",
    ],
}

DOMAIN_REFS = {
    "general": {
        "decision": [
            ".claude/skills/idc-workflow/references/domains/general/module.yaml",
            ".claude/skills/idc-workflow/references/workflows/lane-resolver.md",
        ],
        "planning": [
            ".claude/skills/idc-workflow/references/workflows/general-coding.md",
            ".claude/skills/idc-workflow/references/schemas/general-plan.schema.yaml",
        ],
        "execution": [".claude/skills/idc-general-coding/SKILL.md"],
    },
    "d3a": {},
    "custom": {},
}

OFFICIAL_DOMAIN_PACK_REFS = {
    "d3a": ".claude/skills/idc-workflow/references/domains/d3a/domain-pack.yaml",
}

SIGNAL_REFS = {
    "raw_idea": [
        ".claude/skills/idc-workflow/references/workflows/discovery-provider.md",
        ".claude/skills/idc-workflow/references/schemas/discovery-provider.schema.yaml",
        ".claude/skills/idc-workflow/references/human-views/brainstorming-view.md",
    ],
    "clarification_required": [
        ".claude/skills/idc-workflow/references/workflows/clarification-provider.md",
        ".claude/skills/idc-workflow/references/schemas/clarification-provider.schema.yaml",
        ".claude/skills/idc-workflow/references/human-views/clarification-view.md",
    ],
    "critical_gaps_remain": [
        ".claude/skills/idc-workflow/references/workflows/clarification-provider.md",
        ".claude/skills/idc-workflow/references/schemas/clarification-provider.schema.yaml",
        ".claude/skills/idc-workflow/references/human-views/clarification-view.md",
    ],
    "docs_clarification_required": [],
    "user_question_required": [
        ".claude/skills/idc-workflow/references/workflows/ask-user-tool-policy.md"
    ],
    "tr3_input": [
        ".claude/skills/idc-workflow/references/schemas/normalized-request.schema.yaml",
        ".claude/skills/idc-workflow/references/docs/deep-dive/tr3-input.md",
    ],
    "tdd_required": [
        ".claude/skills/idc-workflow/references/workflows/tdd-state-machine.md"
    ],
    "repo_context_required": [
        ".claude/skills/idc-workflow/CONTEXT_ENGINEERING.md",
        ".claude/skills/idc-workflow/references/workflows/provider-selection-matrix.md",
        ".claude/skills/idc-workflow/references/workflows/repo-context-providers.md",
        ".claude/skills/idc-workflow/references/schemas/repo-context-provider.schema.yaml",
    ],
    "vertical_slice_readiness_required": [
        ".claude/skills/idc-workflow/references/workflows/vertical-slice-readiness-gate.md",
        ".claude/skills/idc-workflow/references/schemas/vertical-slice-readiness.schema.yaml",
        "docs/confidential-migration-checklist.md",
    ],
}

# Method assets remain owned by their configured Skills and are deliberately not
# appended by signal policy. Built-in defaults load these from their own SKILL.md:
# .claude/skills/idc-intent-grilling/references/grill-me-method.md
# .claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md

# Framework-default alignment baseline: the five intent skills the resolver
# materializes (resolve_team_config.py `alignment_default_bindings`) when
# team-config.yaml has no alignment section. Documented here so the source
# text carries the literal intent-alignment ref, and used as a fallback when a
# decision phase derives no skill refs from the effective pipeline.
FRAMEWORK_DEFAULT_ALIGNMENT_REFS = [
    ".claude/skills/idc-intent-discovery/SKILL.md",
    ".claude/skills/idc-brainstorming/SKILL.md",
    ".claude/skills/idc-intent-grilling/SKILL.md",
    ".claude/skills/idc-intent-grilling-with-docs/SKILL.md",
    ".claude/skills/idc-intent-alignment/SKILL.md",
]


def to_array(value):
    """Ruby Array(): nil -> [], list -> itself, scalar -> wrap."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [[key, child] for key, child in value.items()]
    return [value]


def dig(node, *keys):
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def uniq(items):
    seen = set()
    output = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def fail_plan(message, exit_code=2):
    print(
        yaml.dump(
            {"context_load_plan": {"status": "INVALID", "reason": message}},
            allow_unicode=True,
        )
    )
    sys.exit(exit_code)


def load_yaml(path):
    try:
        with open(os.path.abspath(path), "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        fail_plan(str(error))
    try:
        return yaml.safe_load(text) or {}
    except yaml.YAMLError as error:
        fail_plan(str(error))


def repo_relative_ref(ref):
    text = str(ref)
    path = Path(text)
    if not path.is_absolute():
        return text
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError:
        return text
    return text if relative.startswith("..") else relative


def resolve_declared_ref(ref, base_dir):
    text = str(ref or "")
    if text.startswith("harness://"):
        return str((ROOT / text[len("harness://") :]).resolve())
    path = Path(text)
    if path.is_absolute():
        return str(path)
    local = (Path(base_dir) / path).resolve()
    return str(local if local.exists() else (ROOT / path).resolve())


def hydrate_official_domain_pack(domain_id, selected_domain):
    pack_ref = OFFICIAL_DOMAIN_PACK_REFS.get(domain_id)
    if not pack_ref or not isinstance(selected_domain, dict):
        return selected_domain
    if selected_domain.get("workflow_profile_ref"):
        return selected_domain
    pack_path = (ROOT / pack_ref).resolve()
    pack_document = load_yaml(pack_path)
    pack = pack_document.get("domain_pack") or {}
    if not isinstance(pack, dict) or pack.get("id") != domain_id:
        fail_plan("official Domain Pack does not match selected domain: {}".format(domain_id))
    hydrated = dict(selected_domain)
    hydrated["pack_ref"] = str(pack_path)
    hydrated["lane_policy"] = pack.get("lane_policy") or {}
    for key in [
        "workflow_profile_ref",
        "capability_policy_ref",
        "completion_predicate_ref",
        "knowledge_root_ref",
    ]:
        hydrated[key] = resolve_declared_ref(pack.get(key), pack_path.parent)
    registries = pack.get("registries") or {}
    hydrated["registries"] = {
        key: resolve_declared_ref(value, pack_path.parent)
        for key, value in registries.items()
    }
    return hydrated


def main():
    parser = argparse.ArgumentParser(
        prog="plan_context.py",
        description="Usage: plan_context.py --effective PATH --phase PHASE [--domain DOMAIN] [--lane LANE] [--selection PATH] [--knowledge-plan PATH] [--signal SIGNAL] [--signals-complete]",
    )
    parser.add_argument("--effective", dest="effective")
    parser.add_argument("--phase", dest="phase")
    parser.add_argument("--domain", dest="domain")
    parser.add_argument("--lane", dest="lane")
    parser.add_argument("--selection", dest="selection")
    parser.add_argument("--knowledge-plan", dest="knowledge_plan")
    parser.add_argument("--signal", dest="signals", action="append", default=[])
    parser.add_argument("--signals-complete", dest="signals_complete", action="store_true")
    options = parser.parse_args()

    signals = uniq(options.signals)

    if not options.effective or not options.phase:
        fail_plan("--effective and --phase are required")
    if options.phase not in PHASES:
        fail_plan("unknown phase: {}".format(options.phase))
    if options.lane and options.lane not in LANES:
        fail_plan("unknown lane: {}".format(options.lane))
    if options.phase != "bootstrap" and not options.domain:
        fail_plan("--domain is required after bootstrap")
    if options.phase == "execution" and not options.selection:
        fail_plan("--selection is required for execution")
    if options.phase == "execution" and not options.knowledge_plan:
        fail_plan("--knowledge-plan is required for execution")

    effective = load_yaml(options.effective)
    if effective.get("generated") is not True:
        fail_plan("effective config is not generated runtime state")

    # Gate 2: multi-domain configs accept any enabled module selected by Scenario
    # Router. Legacy configs remain single-domain and keep the original mismatch
    # error behavior. A custom domain accepts both `custom` and its declared id.
    domains_registry = effective.get("domains")
    selected_domain = None
    if isinstance(domains_registry, dict) and isinstance(
        domains_registry.get("modules"), dict
    ):
        enabled_domain_keys = list(to_array(domains_registry.get("enabled")))
        modules = domains_registry["modules"]
        custom_domain_id = str(dig(modules, "custom", "id") or "")
        accepted_domains = list(enabled_domain_keys)
        if "custom" in enabled_domain_keys and custom_domain_id:
            accepted_domains.append(custom_domain_id)
        accepted_domains = uniq(accepted_domains)
        selected_key = options.domain
        if custom_domain_id and selected_key == custom_domain_id:
            selected_key = "custom"
        if selected_key is not None and selected_key not in enabled_domain_keys:
            fail_plan(
                "unknown or disabled domain: {} (enabled: {})".format(
                    options.domain, ", ".join(str(item) for item in accepted_domains)
                )
            )
        if selected_key is None:
            selected_key = domains_registry.get("default")
        selected_domain = modules.get(selected_key) or effective.get("domain")
        if selected_key == "custom" and options.domain:
            options.domain = "custom"
    else:
        effective_domain_id = dig(effective, "domain", "id")
        effective_custom_domain = dig(effective, "domain", "source") == "team-config-inline"
        accepted_domains = (
            ["custom", str(effective_domain_id)]
            if effective_custom_domain
            else [str(effective_domain_id)]
        )
        accepted_domains = uniq([item for item in accepted_domains if item != ""])
        if options.domain and effective_custom_domain and options.domain not in accepted_domains:
            fail_plan(
                "unknown domain: {} (effective domain: custom/{}; accepted: {})".format(
                    options.domain,
                    effective_domain_id,
                    ", ".join(str(item) for item in accepted_domains),
                )
            )
        if options.domain and not effective_custom_domain:
            if options.domain not in DOMAINS:
                fail_plan(
                    "unknown domain: {} (accepted: {})".format(
                        options.domain, ", ".join(str(item) for item in accepted_domains)
                    )
                )
            if effective_domain_id != options.domain:
                fail_plan(
                    "--domain {} does not match effective domain {}; "
                    "use the effective domain, or add {} to domain.enabled "
                    "(legacy single-domain configs: switch domain.mode)".format(
                        options.domain, effective_domain_id or "unknown", options.domain
                    )
                )
        selected_domain = effective.get("domain")
        if effective_custom_domain and options.domain:
            options.domain = "custom"

    selected_domain = hydrate_official_domain_pack(options.domain, selected_domain)
    module_lane_mode = dig(selected_domain, "lane_policy", "mode")

    lane_applicable = options.domain == "general"
    if module_lane_mode in ("dynamic", "fixed", "not_applicable"):
        lane_applicable = module_lane_mode != "not_applicable"
        if module_lane_mode == "fixed":
            fixed_lane = dig(selected_domain, "lane_policy", "selected_lane")
            if options.lane and options.lane != fixed_lane:
                fail_plan(
                    "--lane {} conflicts with selected domain lane_policy.mode fixed "
                    "selected_lane {}; omit --lane or update the fixed policy in "
                    "team-config.yaml".format(options.lane, fixed_lane)
                )
            if not options.lane:
                options.lane = fixed_lane
    if (
        lane_applicable
        and options.phase in ("planning", "execution", "completion")
        and not options.lane
    ):
        lane_default = str(dig(effective, "lane", "default") or "")
        if not lane_default:
            fail_plan(
                "--lane is required for a lane-applicable domain and the effective "
                "config has no lane.default fallback"
            )
        options.lane = lane_default

    refs = list(COMMON_REFS.get(options.phase, []))
    if options.domain:
        refs += list(to_array(dig(DOMAIN_REFS, options.domain, options.phase)))

    # v2 Domain Packs materialize public contract refs directly on the selected
    # module. Consume phase-relevant files without registering the Domain ID in
    # Core. knowledge_root_ref is a directory boundary, so it is surfaced in the
    # plan metadata rather than treated as a loadable file.
    module_refs = {}
    if isinstance(selected_domain, dict):
        for key in [
            "workflow_profile_ref",
            "capability_policy_ref",
            "completion_predicate_ref",
            "knowledge_root_ref",
        ]:
            if present := selected_domain.get(key):
                module_refs[key] = present
        registries = selected_domain.get("registries") or {}
        if isinstance(registries, dict):
            module_refs["registries"] = {
                key: value
                for key, value in registries.items()
                if value is not None and str(value) != ""
            }
    module_phase_ref_keys = {
        "decision": ["workflow_profile_ref"],
        "planning": ["workflow_profile_ref", "capability_policy_ref"],
        "execution": ["workflow_profile_ref", "capability_policy_ref"],
        "completion": ["completion_predicate_ref"],
    }
    if dig(selected_domain, "source") == "domain-pack":
        refs += [
            module_refs.get(key)
            for key in module_phase_ref_keys.get(options.phase, [])
            if module_refs.get(key)
        ]
        if options.phase == "planning":
            refs += list((module_refs.get("registries") or {}).values())

    workflow_profile_ref = module_refs.get("workflow_profile_ref")
    if workflow_profile_ref:
        workflow_path = Path(str(workflow_profile_ref)).resolve()
        workflow_document = load_yaml(workflow_path)
        workflow_profile = workflow_document.get("workflow_profile") or {}
        phase_refs = (
            workflow_profile.get("phase_refs")
            if isinstance(workflow_profile, dict)
            else {}
        ) or {}
        refs += [
            resolve_declared_ref(ref, workflow_path.parent)
            for ref in to_array(phase_refs.get(options.phase))
        ]

    alignment_declared_signals = []
    alignment_resolution = None
    if options.phase == "decision":
        alignment = effective.get("alignment")
        if not isinstance(alignment, dict) or not alignment:
            fail_plan(
                "effective config is missing the materialized alignment pipeline; "
                "regenerate it with resolve_team_config.py"
            )
        alignment_bindings = alignment.get("bindings") or {}
        alignment_steps = list(to_array(dig(alignment, "orchestration", "steps")))
        alignment_declared_signals = uniq(
            [
                signal
                for step in alignment_steps
                if isinstance(step, dict)
                for signal in to_array(step.get("trigger_signals"))
            ]
        )
        if options.signals_complete:
            selected_alignment_steps = [
                step
                for step in alignment_steps
                if isinstance(step, dict)
                and (
                    step.get("stage") == "alignment_check"
                    or not to_array(step.get("trigger_signals"))
                    or any(
                        signal in signals
                        for signal in to_array(step.get("trigger_signals"))
                    )
                )
            ]
        else:
            selected_alignment_steps = list(alignment_steps)
        alignment_skill_ids = [
            skill_id
            for step in selected_alignment_steps
            if isinstance(step, dict)
            for skill_id in to_array(step.get("skill_ids"))
        ]
        alignment_skill_refs = []
        for skill_id in alignment_skill_ids:
            skill_ref = str(dig(alignment_bindings, skill_id, "skill_ref") or "")
            if skill_ref:
                alignment_skill_refs.append(repo_relative_ref(skill_ref))
        alignment_skill_refs = uniq(alignment_skill_refs)
        if not alignment_skill_refs:
            alignment_skill_refs = uniq(
                [repo_relative_ref(ref) for ref in FRAMEWORK_DEFAULT_ALIGNMENT_REFS]
            )
        if not alignment_skill_refs:
            fail_plan(
                "decision phase derived no alignment skill refs from the effective "
                "alignment pipeline"
            )
        refs += alignment_skill_refs
        selected_step_ids = [
            step.get("id")
            for step in selected_alignment_steps
            if isinstance(step, dict) and step.get("id") is not None
        ]
        all_step_ids = [
            step.get("id")
            for step in alignment_steps
            if isinstance(step, dict) and step.get("id") is not None
        ]
        # Structured per-step status so downstream consumers can distinguish
        # must-execute steps from signal-skipped ones (complete) or steps whose
        # trigger evaluation is still pending (uncertain) without re-deriving the
        # matching semantics. The alignment_check gate step always runs.
        alignment_step_statuses = []
        for step in alignment_steps:
            if not isinstance(step, dict):
                continue
            step_id = step.get("id")
            if step_id is None or str(step_id) == "":
                continue
            required_signals = to_array(step.get("trigger_signals"))
            if step.get("stage") == "alignment_check":
                status = "always_run"
            elif options.signals_complete:
                status = (
                    "must_execute"
                    if (not required_signals or any(signal in signals for signal in required_signals))
                    else "skipped_by_signal"
                )
            else:
                status = "pending_trigger_evaluation"
            step_skill_refs = []
            for skill_id in to_array(step.get("skill_ids")):
                skill_ref = str(dig(alignment_bindings, skill_id, "skill_ref") or "")
                if skill_ref:
                    step_skill_refs.append(repo_relative_ref(skill_ref))
            alignment_step_statuses.append(
                {
                    "step_id": step_id,
                    "trigger_signals": list(required_signals),
                    "skill_ref": (
                        step_skill_refs[0] if len(step_skill_refs) == 1 else step_skill_refs
                    ),
                    "status": status,
                }
            )
        # Under an uncertain signal set every signal-guarded step is still loaded
        # (fallback), so each one carries an open trigger evaluation instead of a
        # must-execute / skipped verdict.
        pending_trigger_evaluations = []
        if not options.signals_complete:
            for step in alignment_steps:
                if not isinstance(step, dict):
                    continue
                if step.get("stage") == "alignment_check":
                    continue
                required_signals = to_array(step.get("trigger_signals"))
                if not required_signals:
                    continue
                step_id = step.get("id")
                if step_id is None or str(step_id) == "":
                    continue
                pending_trigger_evaluations.append(
                    {"step_id": step_id, "trigger_signals": list(required_signals)}
                )
        alignment_resolution = {
            "signal_set": "complete" if options.signals_complete else "uncertain",
            "alignment_check_gate": (
                "pre_alignment_signals_resolved"
                if options.signals_complete
                else "pending_trigger_evaluations"
            ),
            "matched_step_ids": selected_step_ids,
            "skipped_step_ids": [
                step_id for step_id in all_step_ids if step_id not in set(selected_step_ids)
            ],
            "fallback_reason": (
                None
                if options.signals_complete
                else "signal set not declared complete; loaded full configured alignment pipeline"
            ),
            "steps": alignment_step_statuses,
        }
        if not options.signals_complete:
            alignment_resolution["pending_trigger_evaluations"] = pending_trigger_evaluations

    if options.domain == "custom":
        custom_ref_key = {
            "planning": "planner_skill_ref",
            "execution": "workflow_skill_ref",
            "completion": "completion_skill_ref",
        }.get(options.phase)
        if options.phase == "execution" and dig(selected_domain, "orchestration", "mode") == "ordered":
            custom_ref_key = None
        custom_ref = selected_domain.get(custom_ref_key) if custom_ref_key else None
        if custom_ref_key and not str(custom_ref or ""):
            fail_plan("custom domain is missing {}".format(custom_ref_key))
        if custom_ref:
            refs.append(custom_ref)

    domain_orchestration_resolution = None
    domain_declared_signals = []
    if options.phase == "execution" and options.domain in ("d3a", "custom"):
        orchestration = selected_domain.get("orchestration") or {}
        if isinstance(orchestration, dict) and orchestration.get("mode") == "ordered":
            steps = list(to_array(orchestration.get("steps")))
            domain_declared_signals = uniq(
                [
                    signal
                    for step in steps
                    if isinstance(step, dict)
                    for signal in to_array(step.get("trigger_signals"))
                ]
            )
            if options.signals_complete:
                selected_steps = [
                    step
                    for step in steps
                    if isinstance(step, dict)
                    and (
                        not to_array(step.get("trigger_signals"))
                        or not [
                            signal
                            for signal in to_array(step.get("trigger_signals"))
                            if signal not in signals
                        ]
                    )
                ]
            else:
                selected_steps = list(steps)
            capability_refs = {}
            for capability in to_array(effective.get("available_capabilities")):
                if isinstance(capability, dict):
                    capability_refs[capability.get("id")] = capability.get("skill_ref")
            selected_skill_ids = uniq(
                [
                    skill_id
                    for step in selected_steps
                    if isinstance(step, dict)
                    for skill_id in to_array(step.get("skill_ids"))
                ]
            )
            ordered_refs = [
                capability_refs.get(skill_id)
                for skill_id in selected_skill_ids
                if capability_refs.get(skill_id) is not None
            ]
            if selected_steps and not ordered_refs:
                fail_plan("ordered domain orchestration derived no executable skill refs")
            refs += ordered_refs
            selected_ids = [
                step.get("id") for step in selected_steps if isinstance(step, dict)
            ]
            all_ids = [step.get("id") for step in steps if isinstance(step, dict)]
            domain_orchestration_resolution = {
                "mode": "ordered",
                "signal_set": "complete" if options.signals_complete else "uncertain",
                "matched_step_ids": selected_ids,
                "skipped_step_ids": [
                    step_id for step_id in all_ids if step_id not in set(selected_ids)
                ],
                "ordered_skill_ids": selected_skill_ids,
            }

    # Surface the effective domain's declared required contracts in the planning
    # plan so downstream contract gating sees them; the gate workflow ref rides
    # along so the plan is self-contained for contract enforcement.
    required_contracts = [str(item) for item in to_array(selected_domain.get("required_contracts"))]
    if options.phase == "planning" and required_contracts:
        refs.append(".claude/skills/idc-workflow/references/workflows/contract-gate.md")

    # Lane Resolver owns dynamic lane selection only (lane-resolver.md): a fixed
    # lane policy pins selected_lane up front and not_applicable domains are
    # handled by their execution profile, so neither injects the resolver ref.
    if (
        module_lane_mode == "dynamic"
        and options.phase == "decision"
    ):
        refs.append(".claude/skills/idc-workflow/references/workflows/lane-resolver.md")
    if lane_applicable and options.lane and options.phase in (
        "decision",
        "planning",
        "execution",
        "completion",
    ):
        refs.append(
            ".claude/skills/idc-workflow/references/lanes/{}.yaml".format(options.lane)
        )

    known_signals = list(SIGNAL_REFS.keys())
    if options.phase == "decision":
        known_signals += alignment_declared_signals
    known_signals += domain_declared_signals
    unknown_signals = [signal for signal in signals if signal not in uniq(known_signals)]
    if unknown_signals:
        fail_plan("unknown signal(s): {}".format(", ".join(str(item) for item in unknown_signals)))
    for signal in signals:
        refs += list(to_array(SIGNAL_REFS.get(signal)))

    selected_capabilities = []
    selection = None
    if options.selection:
        selection = load_yaml(options.selection).get("capability_selection_result", {})
        if not isinstance(selection, dict) or selection.get("status") != "READY":
            fail_plan("capability selection is not READY")
        selected_capabilities = [
            {
                "capability_id": item.get("capability_id"),
                "skill_ref": item.get("skill_ref"),
                "execution_order": item.get("execution_order"),
            }
            for item in to_array(selection.get("selected"))
        ]
        refs += [item["skill_ref"] for item in selected_capabilities]

    knowledge_plan = None
    if options.knowledge_plan:
        knowledge_plan = load_yaml(options.knowledge_plan).get("knowledge_load_plan", {})
        if not isinstance(knowledge_plan, dict) or knowledge_plan.get("status") != "READY":
            fail_plan("knowledge load plan is not READY")
        if knowledge_plan.get("source_sha256") != effective.get("source_sha256"):
            fail_plan("knowledge load plan source does not match effective config")
        if knowledge_plan.get("selected_domain") != options.domain:
            fail_plan("knowledge load plan domain does not match context domain")
        if selection is not None and knowledge_plan.get("execution_unit_ref") != selection.get(
            "execution_unit_ref"
        ):
            fail_plan("knowledge load plan execution unit does not match capability selection")
        provider_skill_ref = dig(knowledge_plan, "repo_context", "provider_skill_ref")
        if (
            dig(knowledge_plan, "repo_context", "required") is True
            and dig(knowledge_plan, "repo_context", "mode") == "bound_skill"
        ):
            if not str(provider_skill_ref or ""):
                fail_plan("bound repo context mode is missing provider_skill_ref")
            refs.append(provider_skill_ref)

    refs = uniq(
        [
            str(ref)
            for ref in refs
            if ref is not None and str(ref) != ""
        ]
    )
    missing_refs = []
    for ref in refs:
        path = Path(ref)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            missing_refs.append(ref)
    if missing_refs:
        fail_plan(
            "planned reference(s) do not exist: {}".format(
                ", ".join(str(item) for item in missing_refs)
            )
        )

    context_plan = {
        "status": "READY",
        "source_sha256": effective.get("source_sha256"),
        "phase": options.phase,
        "domain": options.domain,
        "lane": options.lane,
        "signals": signals,
        "alignment_resolution": alignment_resolution,
        "domain_orchestration_resolution": domain_orchestration_resolution,
        "domain_module": {
            "id": selected_domain.get("id") if isinstance(selected_domain, dict) else None,
            "lane_policy": (
                selected_domain.get("lane_policy")
                if isinstance(selected_domain, dict)
                else None
            ),
            "refs": module_refs,
        },
        "required_refs": refs,
        "selected_capabilities": selected_capabilities,
        "knowledge_load_plan_ref": (
            os.path.abspath(options.knowledge_plan) if options.knowledge_plan else None
        ),
        "knowledge_plan_id": (
            knowledge_plan.get("knowledge_plan_id") if knowledge_plan is not None else None
        ),
        "required_static_knowledge": (
            list(to_array(knowledge_plan.get("required_static_knowledge")))
            if knowledge_plan is not None
            else []
        ),
        "knowledge_search_scopes": (
            list(to_array(knowledge_plan.get("search_scopes")))
            if knowledge_plan is not None
            else []
        ),
        "repo_context_plan": (
            knowledge_plan.get("repo_context") if knowledge_plan is not None else None
        ),
        "load_policy": "read_required_refs_only",
    }
    if options.phase == "planning" and required_contracts:
        context_plan["required_contracts"] = required_contracts

    print(yaml.dump({"context_load_plan": context_plan}, allow_unicode=True))


if __name__ == "__main__":
    main()
