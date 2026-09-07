#!/usr/bin/env python3
"""Migrated from resolve_team_config.rb; behavior is intended to be identical."""

import argparse
import hashlib
import itertools
import json
import os
import re
import sys
from pathlib import Path

import yaml
from domain_policy_runtime import digest, materialize_policy, validate_profiles

SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.IGNORECASE)
IDC_SKILL_DIR_RE = re.compile(r"^idc-[a-z0-9-]+$")
DOMAIN_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
D3A_LAYER_IDS = ["TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV"]
D3A_TEST_DOMAIN_IDS = ["TPRINT", "FW", "DPF"]
LEGACY_FIXED_DOMAIN_ID = "d3a"


def legacy_is_fixed_domain(domain_id):
    """V1-only adapter boundary for the historical built-in fixed Domain."""
    return domain_id == LEGACY_FIXED_DOMAIN_ID


def abort(message):
    print(message, file=sys.stderr)
    sys.exit(1)


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


def value_at(hash_value, *keys):
    return dig(hash_value, *keys)


def dotted_value(hash_value, path):
    return value_at(hash_value, *str(path).split("."))


def present(value):
    return value is not None and value != "" and value != [] and value != {}


def uniq(items):
    seen = set()
    output = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def walk_keys(value, path=None):
    path = path or []
    if isinstance(value, dict):
        for key, child in value.items():
            yield list(path) + [str(key)], str(key)
            yield from walk_keys(child, list(path) + [str(key)])
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_keys(child, list(path) + [str(index)])


def resolve_file_ref(ref, team_root, harness_root):
    value = str(ref)
    if value.startswith("harness://"):
        return os.path.normpath(os.path.join(str(harness_root), value[len("harness://") :]))
    if value.startswith("team://"):
        return os.path.normpath(os.path.join(str(team_root), value[len("team://") :]))
    if SCHEME_RE.match(value):
        return value
    if os.path.isabs(value):
        return os.path.normpath(value)
    team_candidate = os.path.normpath(os.path.join(str(team_root), value))
    harness_candidate = os.path.normpath(os.path.join(str(harness_root), value))
    if os.path.exists(team_candidate):
        return team_candidate
    if os.path.exists(harness_candidate):
        return harness_candidate
    return team_candidate


def validate_registry(entries, path, errors):
    if not isinstance(entries, list):
        errors.append("{} must be a list".format(path))
        return
    ids = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append("{}[{}] must be a mapping".format(path, index))
            continue
        entry_id = entry.get("id")
        ref = entry.get("knowledge_ref")
        if not present(entry_id):
            errors.append("{}[{}].id is required".format(path, index))
        if not present(ref):
            errors.append("{}[{}].knowledge_ref is required".format(path, index))
        if present(entry_id) and entry_id in ids:
            errors.append("{}[{}].id is duplicated".format(path, index))
        if present(entry_id):
            ids.append(entry_id)


def normalized_domain_orchestration(value, path, default_mode, allowed_modes, errors):
    if value is None:
        return {"mode": default_mode, "steps": []}
    if not isinstance(value, dict):
        errors.append("{} must be a mapping".format(path))
        return {"mode": default_mode, "steps": []}

    mode = value.get("mode") or default_mode
    if mode not in allowed_modes:
        errors.append("{}.mode must be {}".format(path, " or ".join(allowed_modes)))
    steps = value.get("steps")
    if not isinstance(steps, list):
        errors.append("{}.steps must be a list".format(path))
        steps = []
    if mode == "ordered" and not steps:
        errors.append("{}.steps must not be empty in ordered mode".format(path))
    step_ids = []
    for index, step in enumerate(steps):
        step_path = "{}.steps[{}]".format(path, index)
        if not isinstance(step, dict):
            errors.append("{} must be a mapping".format(step_path))
            continue
        if not present(step.get("id")):
            errors.append("{}.id is required".format(step_path))
        if present(step.get("id")) and step.get("id") in step_ids:
            errors.append("{}.id is duplicated".format(step_path))
        if present(step.get("id")):
            step_ids.append(step.get("id"))
        if not present(step.get("stage")):
            errors.append("{}.stage is required".format(step_path))
        if not present(step.get("skill_ids")):
            errors.append("{}.skill_ids must not be empty".format(step_path))
        if not isinstance(step.get("skill_ids"), list):
            errors.append("{}.skill_ids must be a list".format(step_path))
        if not isinstance(step.get("trigger_signals"), list):
            errors.append("{}.trigger_signals must be a list".format(step_path))
    return {"mode": mode, "steps": steps}


def load_builtin_knowledge_registry(harness_root, relative_path, root_key, errors):
    path = Path(harness_root) / relative_path
    if not path.is_file():
        errors.append("builtin knowledge registry is missing: {}".format(path))
        return []

    try:
        with open(path, "r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle.read()) or {}
    except yaml.YAMLError as error:
        errors.append(
            "builtin knowledge registry is invalid: {}: {}".format(path, str(error))
        )
        return []

    output = []
    for entry in to_array((document or {}).get(root_key)):
        if not isinstance(entry, dict):
            output.append(entry)
            continue
        ref = entry.get("knowledge_ref") or entry.get("knowledge_file")
        resolved_ref = resolve_file_ref(ref, harness_root, harness_root)
        if not Path(resolved_ref).is_file():
            errors.append("builtin knowledge ref does not exist: {}".format(ref))
        merged = {key: child for key, child in entry.items() if key != "knowledge_file"}
        merged["knowledge_ref"] = resolved_ref
        output.append(merged)
    return output


def resolve_v2_ref(ref, primary_root, team_root, harness_root):
    value = str(ref)
    if value.startswith(("harness://", "team://")) or SCHEME_RE.match(value):
        return resolve_file_ref(value, team_root, harness_root)
    if os.path.isabs(value):
        return os.path.normpath(value)
    candidates = [
        Path(primary_root) / value,
        Path(team_root) / value,
        Path(harness_root) / value,
    ]
    for candidate in candidates:
        if candidate.exists():
            return os.path.normpath(str(candidate))
    return os.path.normpath(str(candidates[0]))


def framework_alignment(harness_root, errors):
    binding_refs = {
        "intent_discovery": ".claude/skills/idc-intent-discovery/SKILL.md",
        "brainstorming": ".claude/skills/idc-brainstorming/SKILL.md",
        "intent_grilling": ".claude/skills/idc-intent-grilling/SKILL.md",
        "intent_grilling_with_docs": (
            ".claude/skills/idc-intent-grilling-with-docs/SKILL.md"
        ),
        "intent_alignment": ".claude/skills/idc-intent-alignment/SKILL.md",
    }
    bindings = {}
    for skill_id, ref in binding_refs.items():
        resolved = resolve_file_ref(ref, harness_root, harness_root)
        if not Path(resolved).is_file():
            errors.append("framework alignment Skill is missing: {}".format(ref))
        bindings[skill_id] = {"skill_ref": resolved}
    steps = [
        {
            "id": "alignment-discovery",
            "stage": "discovery",
            "skill_ids": ["intent_discovery"],
            "trigger_signals": ["raw_idea"],
        },
        {
            "id": "alignment-brainstorming",
            "stage": "divergence",
            "skill_ids": ["brainstorming"],
            "trigger_signals": ["raw_idea", "alternatives_needed"],
        },
        {
            "id": "alignment-grilling",
            "stage": "clarification",
            "skill_ids": ["intent_grilling"],
            "trigger_signals": [
                "critical_gaps_remain",
                "clarification_required",
                "structured_requirement_input",
                "tr3_input",
            ],
        },
        {
            "id": "alignment-grilling-with-docs",
            "stage": "clarification",
            "skill_ids": ["intent_grilling_with_docs"],
            "trigger_signals": ["docs_clarification_required"],
        },
        {
            "id": "alignment-check",
            "stage": "alignment_check",
            "skill_ids": ["intent_alignment"],
            "trigger_signals": [],
        },
    ]
    return {
        "source": "framework-default",
        "bindings": bindings,
        "orchestration": {"mode": "ordered", "steps": steps},
    }


def registry_ids(path, root_keys, errors, label):
    try:
        document = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        errors.append("DOMAIN_PACK_INVALID: {} is invalid: {}".format(label, error))
        return []
    rows = []
    if isinstance(document, dict):
        for root_key in root_keys:
            if root_key in document:
                rows = document.get(root_key) or []
                break
    if not isinstance(rows, list):
        errors.append("DOMAIN_PACK_INVALID: {} must contain a registry list".format(label))
        return []
    return [row.get("id") for row in rows if isinstance(row, dict)]


def validate_fixed_architecture(contract, lane_policy, registries, definition_registries, errors):
    """Validate an optional Pack-owned immutable architecture contract."""
    if contract is None:
        return
    if not isinstance(contract, dict):
        errors.append("DOMAIN_PACK_INVALID: fixed_architecture must be a mapping")
        return
    allowed = {"lane_mode", "coding_layer_ids", "default_test_domain_ids"}
    if set(contract) - allowed:
        errors.append("DOMAIN_PACK_INVALID: fixed_architecture has unsupported fields")
        return
    expected_mode = contract.get("lane_mode")
    if expected_mode and lane_policy.get("mode") != expected_mode:
        errors.append("DOMAIN_PACK_INVALID: fixed architecture lane policy does not match Pack contract")
    expected_layers = contract.get("coding_layer_ids")
    if expected_layers is not None:
        if not isinstance(expected_layers, list) or not all(isinstance(item, str) for item in expected_layers):
            errors.append("DOMAIN_PACK_INVALID: fixed_architecture.coding_layer_ids must be a string list")
        elif registry_ids(registries.get("coding_layers_ref", ""), ["layers", "coding_layers"], errors,
                          "fixed architecture coding layer registry") != expected_layers:
            errors.append("DOMAIN_PACK_INVALID: fixed architecture coding layer registry does not match Pack contract")
    expected_tests = contract.get("default_test_domain_ids")
    if expected_tests is not None and not definition_registries:
        if not isinstance(expected_tests, list) or not all(isinstance(item, str) for item in expected_tests):
            errors.append("DOMAIN_PACK_INVALID: fixed_architecture.default_test_domain_ids must be a string list")
        elif registry_ids(registries.get("test_domains_ref", ""), ["domains", "test_domains"], errors,
                          "fixed architecture test domain registry") != expected_tests:
            errors.append("DOMAIN_PACK_INVALID: fixed architecture test domain registry does not match Pack contract")


def materialize_completion_predicates(module, errors):
    """Expand fixed-Pack test obligations from the effective registry, not its shared file."""
    document = yaml.safe_load(Path(module["completion_predicate_ref"]).read_text()) or {}
    predicates = list(document.get("completion_predicates") or [])
    if not module.get("fixed_architecture"):
        return predicates
    registry = yaml.safe_load(Path(module["registries"]["test_domains_ref"]).read_text()) or {}
    rows = registry.get("test_domains", registry.get("domains", [])) if isinstance(registry, dict) else []
    test_ids = [row.get("id") for row in rows if isinstance(row, dict) and present(row.get("id"))]
    if not test_ids:
        errors.append("DOMAIN_POLICY_INVALID: fixed architecture requires effective test-domain registry")
        return []
    expanded = [
        {"predicate_id": f"{test_id}_green", "required": True,
         "expected_status": "PASS", "evidence_required": True}
        for test_id in test_ids
    ]
    expanded.extend(row for row in predicates
                    if isinstance(row, dict) and row.get("predicate_id") != "required_dt_domains_green")
    return expanded


def resolve_v2_alignment(config, team_root, harness_root, errors):
    configured = config.get("alignment")
    if configured is None:
        return framework_alignment(harness_root, errors), []
    if not isinstance(configured, dict):
        errors.append("alignment must be a mapping")
        return {}, []
    bindings, orchestration = configured.get("bindings"), configured.get("orchestration")
    if not isinstance(bindings, dict) or not isinstance(orchestration, dict):
        errors.append("alignment bindings and orchestration must be mappings")
        return {}, []
    resolved_bindings, refs = {}, []
    for skill_id, binding in bindings.items():
        path = "alignment.bindings.{}".format(skill_id)
        if not isinstance(binding, dict) or not present(binding.get("skill_ref")):
            errors.append("{}.skill_ref is required".format(path))
            continue
        resolved = resolve_file_ref(binding["skill_ref"], team_root, harness_root)
        resolved_path = Path(resolved)
        if not (resolved_path.name == "SKILL.md" and IDC_SKILL_DIR_RE.match(resolved_path.parent.name)):
            errors.append("{}.skill_ref must resolve to an idc-*/SKILL.md path".format(path))
        elif not resolved_path.is_file():
            errors.append("{}.skill_ref does not exist: {}".format(path, resolved))
        resolved_bindings[skill_id] = dict(binding, skill_ref=resolved)
        refs.append(resolved)
    if orchestration.get("mode") != "ordered" or not isinstance(orchestration.get("steps"), list):
        errors.append("alignment.orchestration must contain ordered steps")
        steps = []
    else:
        steps = orchestration["steps"]
    seen, stages, signals, clarification_signals = set(), set(), set(), set()
    for index, step in enumerate(steps):
        path = "alignment.orchestration.steps[{}]".format(index)
        if not isinstance(step, dict) or not present(step.get("id")) or step.get("id") in seen:
            errors.append("{}.id must be unique and nonempty".format(path))
            continue
        seen.add(step["id"])
        if step.get("stage") not in {"discovery", "divergence", "clarification", "alignment_check"}:
            errors.append("{}.stage is invalid".format(path))
        else:
            stages.add(step["stage"])
        if not isinstance(step.get("skill_ids"), list) or not step["skill_ids"]:
            errors.append("{}.skill_ids must not be empty".format(path))
        else:
            for skill_id in step["skill_ids"]:
                if skill_id not in resolved_bindings:
                    errors.append("{}.skill_ids references an unbound Skill".format(path))
        if not isinstance(step.get("trigger_signals"), list):
            errors.append("{}.trigger_signals must be a list".format(path))
        else:
            signals.update(step["trigger_signals"])
            if step.get("stage") == "clarification":
                clarification_signals.update(step["trigger_signals"])
    for stage in {"discovery", "divergence", "clarification", "alignment_check"} - stages:
        errors.append("alignment.orchestration requires stage {}".format(stage))
    for signal in {"raw_idea", "critical_gaps_remain"} - signals:
        errors.append("alignment trigger signal floor is missing {}".format(signal))
    for signal in {"structured_requirement_input", "tr3_input"} - clarification_signals:
        errors.append(
            "alignment clarification signal floor is missing {}: NEEDS_TEAM_CONFIG".format(
                signal
            )
        )
    return {"source": "configured", "bindings": resolved_bindings,
            "orchestration": {"mode": "ordered", "steps": steps}}, refs


def apply_v2_team_capabilities(config, modules, team_root, harness_root, errors):
    bindings = config.get("bindings") or {}
    extensions = config.get("adapter_extensions") or []
    if not isinstance(bindings, dict):
        errors.append("bindings must be a mapping")
        bindings = {}
    if not isinstance(extensions, list):
        errors.append("adapter_extensions must be a list")
        extensions = []
    refs, overrides = [], []
    for module in modules.values():
        capabilities = module.get("available_capabilities") or []
        by_id = {row.get("id"): row for row in capabilities}
        for capability_id, binding in bindings.items():
            if not isinstance(binding, dict) or not present(binding.get("skill_ref")):
                errors.append("bindings.{}.skill_ref is required".format(capability_id))
                continue
            resolved = resolve_file_ref(binding["skill_ref"], team_root, harness_root)
            if not SCHEME_RE.match(resolved) and not Path(resolved).is_file():
                errors.append("bindings.{}.skill_ref does not exist".format(capability_id))
            binding["skill_ref"] = resolved
            refs.append(resolved)
            if capability_id in by_id:
                old_ref = by_id[capability_id].get("skill_ref")
                by_id[capability_id]["skill_ref"] = resolved
                overrides.append({"capability_id": capability_id, "from": old_ref, "to": resolved})
        for index, raw in enumerate(extensions):
            path = "adapter_extensions[{}]".format(index)
            if not isinstance(raw, dict) or not str(raw.get("id") or "").startswith("idc-"):
                errors.append("{}.id must start with idc-".format(path))
                continue
            if raw.get("execution_role") is None:
                raw["execution_role"] = "atomic_capability"
            if raw.get("execution_role") not in {"atomic_capability", "verification_capability",
                                                  "pre_alignment_capability"}:
                errors.append("{}.execution_role is invalid".format(path))
            for field in ["composes_with", "supersedes"]:
                if raw.get(field) is None:
                    raw[field] = []
            for field in ["capability_keys", "allowed_stages", "eligible_lanes", "execution_profiles",
                          "trigger_signals", "requires", "blocks_when", "composes_with", "supersedes"]:
                if not isinstance(raw.get(field), list):
                    errors.append("{}.{} must be a list".format(path, field))
            if not raw.get("capability_keys") or not raw.get("allowed_stages"):
                errors.append("{} requires capability_keys and allowed_stages".format(path))
            if set(raw.get("capability_keys") or []) & {"domain_selection", "lane_selection",
                    "contract_gate", "human_alignment", "completion_gate", "workflow_orchestration",
                    "domain_execution", "delegation"}:
                errors.append("{}.capability_keys contains protected ownership".format(path))
            may_override = raw.get("may_override")
            if isinstance(may_override, dict) and set(may_override) & {
                    "domain_selection", "lane_selection", "contract_gate", "human_alignment",
                    "completion_gate"}:
                errors.append("{}.may_override contains protected ownership".format(path))
            if set(raw.get("allowed_stages") or []) - {
                    "planning", "implementation", "verification", "completion", "review", "fix",
                    "discovery", "divergence", "clarification", "alignment_check", "pre_alignment",
                    "dt_design", "dt_writing", "dt_build", "tran_build", "debugging", "finishing"}:
                errors.append("{}.allowed_stages contains an unsupported stage".format(path))
            if set(raw.get("eligible_lanes") or []) - {"fast", "lite", "complex"}:
                errors.append("{}.eligible_lanes contains an unsupported Lane".format(path))
            if raw.get("id") in by_id:
                errors.append("available capability IDs are duplicated: {}".format(raw.get("id")))
                continue
            resolved = resolve_file_ref(raw.get("skill_ref"), team_root, harness_root)
            if not Path(resolved).is_file():
                errors.append("{}.skill_ref does not exist".format(path))
            extension = dict(raw, skill_ref=resolved)
            refs.append(resolved)
            for field in ["input_contract_ref", "output_contract_ref"]:
                if extension.get(field):
                    extension[field] = resolve_file_ref(extension[field], team_root, harness_root)
                    refs.append(extension[field])
            capabilities.append(extension)
            by_id[extension["id"]] = extension
            extensions[index] = extension
        ids = set(by_id)
        extension_ids = {entry.get("id") for entry in extensions if isinstance(entry, dict)}
        for capability in capabilities:
            if capability.get("id") not in extension_ids:
                continue
            for relation in ["composes_with", "supersedes"]:
                for target in capability.get(relation) or []:
                    if target not in ids or (relation == "supersedes" and target == capability.get("id")):
                        errors.append("{}.{} references an invalid capability: {}".format(
                            capability.get("id"), relation, target))
        for left, right in itertools.combinations(capabilities, 2):
            if not (set(left.get("capability_keys") or []) & set(right.get("capability_keys") or [])
                    and set(left.get("allowed_stages") or []) & set(right.get("allowed_stages") or [])):
                continue
            scoped = (set(left.get("eligible_lanes") or []) & set(right.get("eligible_lanes") or [])
                      or set(left.get("execution_profiles") or []) & set(right.get("execution_profiles") or []))
            if not scoped:
                continue
            left_signals, right_signals = left.get("trigger_signals") or [], right.get("trigger_signals") or []
            if left_signals and right_signals and not set(left_signals) & set(right_signals):
                continue
            related = (right.get("id") in (left.get("composes_with") or [])
                       or left.get("id") in (right.get("composes_with") or [])
                       or right.get("id") in (left.get("supersedes") or [])
                       or left.get("id") in (right.get("supersedes") or []))
            if not related:
                errors.append("ambiguous capability registration: {} conflicts with {}".format(
                    left.get("id"), right.get("id")))
        validate_profiles(module.get("lane_profiles") or {}, capabilities)
    return bindings, extensions, refs, overrides


def compile_v2_runtime(config, source_text, config_path, team_root, harness_root, errors):
    supported_config_fields = {
        "config_version", "team", "domains", "lane", "bindings",
        "adapter_extensions", "alignment", "knowledge", "capability_selection",
        "self_optimization",
    }
    unknown_config_fields = set(config) - supported_config_fields
    if unknown_config_fields:
        errors.append("CONFIG_UNSUPPORTED: unsupported top-level fields: {}".format(
            ", ".join(sorted(unknown_config_fields))))
    team = config.get("team")
    if not isinstance(team, dict):
        errors.append("team must be a mapping for config_version 2")
        team = {}
    unknown_team_fields = set(team) - {"id", "repo_path"}
    if unknown_team_fields:
        errors.append("TEAM_UNSUPPORTED: unsupported fields: {}".format(
            ", ".join(sorted(unknown_team_fields))))
    domains = config.get("domains")
    if not isinstance(domains, dict):
        errors.append("domains must be a mapping for config_version 2")
        domains = {}
    unknown_domain_fields = set(domains) - {"enabled", "default", "definitions"}
    if unknown_domain_fields:
        errors.append("DOMAINS_UNSUPPORTED: unsupported fields: {}".format(
            ", ".join(sorted(unknown_domain_fields))))
    if "domain" in config:
        errors.append("V2_OWNERSHIP_CONFLICT: legacy domain ownership is not allowed")

    enabled = domains.get("enabled")
    default_domain = domains.get("default")
    definitions = domains.get("definitions")
    if not isinstance(enabled, list) or not enabled:
        errors.append("domains.enabled must be a non-empty list")
        enabled = []
    normalized_enabled = []
    for domain_id in enabled:
        if not isinstance(domain_id, str) or not DOMAIN_ID_RE.fullmatch(domain_id):
            errors.append("domains.enabled contains invalid Domain ID: {}".format(domain_id))
            continue
        if domain_id in normalized_enabled:
            errors.append("domains.enabled must contain unique IDs")
            continue
        normalized_enabled.append(domain_id)
    enabled = normalized_enabled
    if default_domain not in enabled:
        errors.append("domains.default must name an enabled Domain")
    if not isinstance(definitions, dict):
        errors.append("domains.definitions must be a mapping")
        definitions = {}

    modules = {}
    dependency_files = {}
    knowledge_catalog = {}
    for domain_id in enabled:
        definition = definitions.get(domain_id)
        if not isinstance(definition, dict):
            errors.append(
                "DOMAIN_PACK_MISSING: domains.definitions.{} must be a mapping".format(
                    domain_id
                )
            )
            continue
        pack_ref = definition.get("pack_ref")
        if not present(pack_ref):
            errors.append(
                "DOMAIN_PACK_MISSING: domains.definitions.{}.pack_ref is missing".format(
                    domain_id
                )
            )
            continue
        pack_path = resolve_v2_ref(pack_ref, config_path.parent, team_root, harness_root)
        if not Path(pack_path).is_file():
            errors.append(
                "DOMAIN_PACK_MISSING: enabled Domain {} pack_ref is missing: {}".format(
                    domain_id, pack_path
                )
            )
            continue
        try:
            pack_document = yaml.safe_load(Path(pack_path).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as error:
            errors.append(
                "DOMAIN_PACK_INVALID: enabled Domain {} pack is invalid: {}".format(
                    domain_id, error
                )
            )
            continue
        pack = pack_document.get("domain_pack") if isinstance(pack_document, dict) else None
        if not isinstance(pack, dict):
            errors.append(
                "DOMAIN_PACK_INVALID: enabled Domain {} requires domain_pack mapping".format(
                    domain_id
                )
            )
            continue
        supported_pack_fields = {
            "id", "trigger_rules", "lane_policy", "fixed_architecture",
            "workflow_profile_ref", "capability_policy_ref",
            "completion_predicate_ref", "registries", "knowledge_root_ref",
        }
        unknown_pack_fields = set(pack) - supported_pack_fields
        if unknown_pack_fields:
            errors.append("DOMAIN_PACK_UNSUPPORTED: {} fields: {}".format(
                domain_id, ", ".join(sorted(unknown_pack_fields))))
        if pack.get("id") != domain_id:
            errors.append(
                "DOMAIN_PACK_ID_MISMATCH: enabled Domain {} does not match pack ID {}".format(
                    domain_id, pack.get("id")
                )
            )
            continue

        # Definition ownership replaces Pack defaults, including explicit empty values.
        overlay_fields = {"trigger_rules", "workflow_profile_ref", "capability_policy_ref",
                          "completion_predicate_ref", "registries"}
        if set(definition) - overlay_fields - {"pack_ref"}:
            errors.append("DOMAIN_PACK_UNSUPPORTED: unsupported definition fields")
        pack = dict(pack, **{key: definition[key] for key in overlay_fields
                            if key in definition and key != "registries"})

        trigger_rules = pack.get("trigger_rules")
        lane_policy = pack.get("lane_policy")
        pack_registries = pack.get("registries")
        definition_registries = definition.get("registries")
        if definition_registries is not None and not isinstance(definition_registries, dict):
            errors.append("DOMAIN_PACK_INVALID: definition registries must be a mapping")
            definition_registries = {}
        registries = dict(pack_registries or {})
        registries.update(definition_registries or {})
        if set(registries) - {"coding_layers_ref", "test_domains_ref"}:
            errors.append("DOMAIN_PACK_INVALID: unsupported registry fields")
        if not isinstance(trigger_rules, list):
            errors.append("DOMAIN_PACK_INVALID: {}.trigger_rules must be a list".format(domain_id))
            trigger_rules = []
        if not isinstance(lane_policy, dict):
            errors.append("DOMAIN_PACK_INVALID: {}.lane_policy must be a mapping".format(domain_id))
            lane_policy = {}
        lane_mode = lane_policy.get("mode")
        if lane_mode not in ("dynamic", "fixed", "not_applicable"):
            errors.append("DOMAIN_PACK_INVALID: {} lane policy mode is invalid".format(domain_id))
        if lane_mode == "fixed" and lane_policy.get("selected_lane") not in (
            "fast",
            "lite",
            "complex",
        ):
            errors.append("DOMAIN_PACK_INVALID: {} fixed lane is required".format(domain_id))
        if lane_mode != "fixed" and present(lane_policy.get("selected_lane")):
            errors.append("DOMAIN_PACK_INVALID: {} selected_lane requires fixed mode".format(domain_id))
        if not isinstance(registries, dict):
            errors.append("DOMAIN_PACK_INVALID: {}.registries must be a mapping".format(domain_id))
            registries = {}

        resolved_refs = {}
        for field in [
            "workflow_profile_ref",
            "capability_policy_ref",
            "completion_predicate_ref",
        ]:
            ref = pack.get(field)
            if not present(ref):
                errors.append("DOMAIN_PACK_INVALID: {}.{} is required".format(domain_id, field))
                continue
            ref_root = config_path.parent if field in definition else Path(pack_path).parent
            resolved = resolve_v2_ref(ref, ref_root, team_root, harness_root)
            if not Path(resolved).is_file():
                errors.append("DOMAIN_PACK_MISSING: {}.{} is missing: {}".format(domain_id, field, resolved))
            resolved_refs[field] = resolved

        resolved_registries = {}
        for field in ["coding_layers_ref", "test_domains_ref"]:
            ref = registries.get(field)
            if not present(ref):
                errors.append("DOMAIN_PACK_INVALID: {}.registries.{} is required".format(domain_id, field))
                continue
            ref_root = config_path.parent if field in (definition_registries or {}) else Path(pack_path).parent
            resolved = resolve_v2_ref(ref, ref_root, team_root, harness_root)
            if not Path(resolved).is_file():
                errors.append("DOMAIN_PACK_MISSING: {} registry {} is missing: {}".format(domain_id, field, resolved))
            resolved_registries[field] = resolved

        knowledge_ref = pack.get("knowledge_root_ref")
        if not present(knowledge_ref):
            errors.append("DOMAIN_PACK_INVALID: {}.knowledge_root_ref is required".format(domain_id))
            resolved_knowledge_ref = None
        else:
            resolved_knowledge_ref = resolve_v2_ref(
                knowledge_ref, Path(pack_path).parent, team_root, harness_root
            )
            if not Path(resolved_knowledge_ref).exists():
                errors.append(
                    "DOMAIN_PACK_MISSING: {} knowledge root is missing: {}".format(
                        domain_id, resolved_knowledge_ref
                    )
                )

        fixed_architecture = pack.get("fixed_architecture")
        validate_fixed_architecture(
            fixed_architecture, lane_policy, resolved_registries,
            definition_registries, errors,
        )

        module = {
            "id": domain_id,
            "source": "domain-pack",
            "pack_ref": pack_path,
            "trigger_rules": trigger_rules,
            "lane_policy": lane_policy,
            "lane_applicability": lane_mode,
            "execution_profile": (
                "lane_driven" if lane_mode in ("dynamic", "fixed") else "domain_pack_fixed_workflow"
            ),
            "registries": resolved_registries,
            "knowledge_root_ref": resolved_knowledge_ref,
            "fixed_architecture": fixed_architecture,
        }
        module.update(resolved_refs)
        try:
            dependency_files.update(materialize_policy(
                module, lambda ref, base: resolve_v2_ref(ref, base, team_root, harness_root)))
            team_profiles = (config.get("lane") or {}).get("profiles") or {}
            if not isinstance(team_profiles, dict):
                raise ValueError("POLICY_INVALID: lane.profiles must be a mapping")
            profiles = dict(module["lane_profiles"] or {})
            profiles.update(team_profiles)
            validate_profiles(profiles, module["available_capabilities"])
            module["lane_profiles"] = profiles
            policy = (yaml.safe_load(Path(module["capability_policy_ref"]).read_text()) or {}).get("capability_policy") or {}
            module["execution_profile"] = policy.get("execution_profile") or module["execution_profile"]
            module["lane_applicability"] = policy.get("lane_applicability") or lane_mode
            module["selection_profile"] = policy.get("selection_profile")
            module["completion_predicates"] = materialize_completion_predicates(module, errors)
        except (ValueError, OSError, TypeError, KeyError, AttributeError, yaml.YAMLError) as error:
            errors.append("DOMAIN_POLICY_INVALID: {}: {}".format(domain_id, error))
        modules[domain_id] = module
        knowledge_catalog[domain_id] = {
            "registries": resolved_registries,
            "knowledge_root_ref": resolved_knowledge_ref,
        }

    bindings, extensions, team_refs, registration_overrides = apply_v2_team_capabilities(
        config, modules, team_root, harness_root, errors
    )
    alignment, alignment_refs = resolve_v2_alignment(config, team_root, harness_root, errors)
    for ref in team_refs + alignment_refs:
        if not SCHEME_RE.match(str(ref)) and Path(ref).is_file():
            dependency_files[str(Path(ref).resolve())] = hashlib.sha256(Path(ref).read_bytes()).hexdigest()

    lane = config.get("lane") if isinstance(config.get("lane"), dict) else {}
    lane = {
        "default": lane.get("default") or "lite",
        "profiles": lane.get("profiles") if isinstance(lane.get("profiles"), dict) else {},
    }
    effective = {
        "generated": True,
        "status": "READY" if not errors else "INVALID",
        "source_ref": str(config_path),
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "config_version": 2,
        "runtime_dependency_files": dependency_files,
        "runtime_dependency_sha256": digest(dependency_files),
        "team": dict(team, repo_path=str(team_root)),
        "domain": modules.get(default_domain) or {},
        "domains": {"enabled": enabled, "default": default_domain, "modules": modules},
        "enabled_domains": enabled,
        "bindings": bindings,
        "adapter_extensions": extensions,
        "available_capabilities": (modules.get(default_domain) or {}).get("available_capabilities", []),
        "registration_audit": {"status": "PASS", "conflicts": [],
                               "declared_overrides": registration_overrides},
        "knowledge": config.get("knowledge"),
        "knowledge_catalog": knowledge_catalog,
        "lane": lane,
        "diagnostics": [],
        "alignment": alignment,
        "capability_selection": config.get("capability_selection") or {
            "mode": "autonomous_minimal_sufficient",
            "lane_profiles": {},
            "require_selected_and_skipped_reasons": True,
        },
        "self_optimization": config.get("self_optimization") or {
            "mode": "observe",
            "auto_modify_core": False,
        },
        "readiness": {
            "status": "READY" if not errors else "INVALID",
            "errors": errors,
            "warnings": [],
        },
    }
    effective["status"] = "READY" if not errors else "INVALID"
    effective["readiness"]["status"] = effective["status"]
    return effective


def main():
    parser = argparse.ArgumentParser(
        prog="resolve_team_config.py",
        description="Usage: resolve_team_config.py --config PATH [--registry PATH] [--check | --output PATH]",
    )
    parser.add_argument("--config", dest="config")
    parser.add_argument("--registry", dest="registry")
    parser.add_argument("--check", dest="check", action="store_true", default=False)
    parser.add_argument("--output", dest="output")
    options = parser.parse_args()

    if not options.config:
        abort("ERROR: --config is required")
    if not options.check and not options.output:
        abort("ERROR: choose --check or --output")

    config_path = Path(os.path.abspath(options.config))
    if not config_path.is_file():
        abort("ERROR: config not found: {}".format(config_path))

    root_candidates = [Path.cwd(), config_path.parent]
    root_candidates.extend(config_path.parent.parents)
    harness_root = next(
        (
            candidate
            for candidate in root_candidates
            if (candidate / ".claude/skills/idc-workflow").is_dir()
        ),
        None,
    )
    if harness_root is None:
        abort("ERROR: cannot locate IDC harness root")

    if options.registry:
        domain_registry_path = Path(os.path.abspath(options.registry))
    else:
        domain_registry_path = (
            harness_root / ".claude/skills/idc-workflow/references/domains/registry.yaml"
        )

    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            source_text = handle.read()
        config = yaml.safe_load(source_text)
    except yaml.YAMLError as error:
        abort("ERROR: invalid YAML: {}".format(str(error)))

    errors = []
    warnings = []

    if not isinstance(config, dict):
        abort("ERROR: root must be a mapping")

    forbidden_keys = ["command", "build_command", "run_command", "pass_condition"]
    for key_path, key in walk_keys(config):
        if key in forbidden_keys:
            errors.append(
                "{} is forbidden; bind a skill_ref instead".format(".".join(key_path))
            )

    if config.get("config_version") not in (1, 2):
        errors.append("config_version must be 1 or 2")
    if not present(value_at(config, "team", "id")):
        errors.append("team.id is required")
    if not present(value_at(config, "team", "repo_path")):
        errors.append("team.repo_path is required")

    team_repo_ref = value_at(config, "team", "repo_path")
    if present(team_repo_ref):
        raw_path = str(team_repo_ref)
        if os.path.isabs(raw_path):
            team_root = Path(os.path.normpath(raw_path))
        else:
            team_root = Path(os.path.normpath(os.path.join(str(harness_root), raw_path)))
    else:
        team_root = harness_root
    if not team_root.is_dir():
        errors.append(
            "team.repo_path does not exist or is not a directory: {}".format(team_repo_ref)
        )

    if config.get("config_version") == 2:
        effective = compile_v2_runtime(
            config,
            source_text,
            config_path,
            team_root,
            harness_root,
            errors,
        )
        if errors:
            if options.output:
                Path(options.output).parent.mkdir(parents=True, exist_ok=True)
                Path(options.output).write_text(yaml.safe_dump(effective, allow_unicode=True))
            print("INVALID team-config.yaml", file=sys.stderr)
            for error in errors:
                print("- {}".format(error), file=sys.stderr)
            sys.exit(1)
        if options.output:
            output_path = Path(os.path.abspath(options.output))
            os.makedirs(str(output_path.parent), exist_ok=True)
            temporary_path = output_path.parent / ".{}.tmp-{}".format(
                output_path.name, os.getpid()
            )
            with open(temporary_path, "w", encoding="utf-8") as handle:
                handle.write(
                    "# Generated by idc-team-config. Do not edit.\n"
                    + yaml.dump(
                        json.loads(json.dumps(effective)),
                        allow_unicode=True,
                        sort_keys=False,
                    )
                )
            os.replace(str(temporary_path), str(output_path))
            print("READY: wrote {}".format(output_path))
        else:
            print("READY: team-config.yaml is valid")
        return

    if "domains" in config:
        errors.append(
            "V1_OWNERSHIP_CONFLICT: domains is reserved for config_version 2"
        )

    mode = value_at(config, "domain", "mode")
    if mode not in ("d3a", "general", "custom"):
        errors.append("domain.mode must be d3a, general, or custom")
    configured_enabled_modes = value_at(config, "domain", "enabled")
    enabled_modes = [mode] if configured_enabled_modes is None else configured_enabled_modes
    if not isinstance(enabled_modes, list) or not enabled_modes:
        errors.append("domain.enabled must be a non-empty list")
        enabled_modes = [mode]
    unknown_enabled_modes = [item for item in enabled_modes if item not in ("d3a", "general", "custom")]
    if unknown_enabled_modes:
        errors.append(
            "domain.enabled contains unknown mode(s): {}".format(
                ", ".join(str(item) for item in unknown_enabled_modes)
            )
        )
    if len(set(enabled_modes)) != len(enabled_modes):
        errors.append("domain.enabled must not contain duplicates")
    if mode not in enabled_modes:
        errors.append("domain.mode must be included in domain.enabled")

    # Gate 1: every enabled builtin domain must be active-registered in the shared
    # domain module registry; `custom` domains are inline-registered via
    # domain.custom. Configs without domain.enabled remain single-domain.
    active_domain_ids = []
    enabled_builtin_modes = [item for item in enabled_modes if item in ("d3a", "general")]
    if enabled_builtin_modes:
        if domain_registry_path.is_file():
            try:
                with open(domain_registry_path, "r", encoding="utf-8") as handle:
                    domain_registry = yaml.safe_load(handle.read()) or {}
            except yaml.YAMLError as error:
                errors.append(
                    "domain module registry is invalid: {}: {}".format(
                        domain_registry_path, str(error)
                    )
                )
                domain_registry = {}
            domain_entries = (domain_registry or {}).get("domain_modules")
            if isinstance(domain_entries, list):
                active_domain_ids = [
                    entry.get("id")
                    for entry in domain_entries
                    if isinstance(entry, dict) and entry.get("status") == "active"
                ]
                active_domain_ids = [item for item in active_domain_ids if item is not None]
            else:
                errors.append(
                    "domain module registry must list domain_modules: {}".format(
                        domain_registry_path
                    )
                )
        else:
            errors.append("domain module registry is missing: {}".format(domain_registry_path))
        for enabled_mode in enabled_builtin_modes:
            if enabled_mode not in active_domain_ids:
                errors.append(
                    "domain.mode {} is not registered in the domain module registry; "
                    "register it or switch domain.mode".format(enabled_mode)
                )

    validate_registry(
        value_at(config, "domain", "d3a", "dt_domains") or [],
        "domain.d3a.dt_domains",
        errors,
    )
    d3a_orchestration = normalized_domain_orchestration(
        value_at(config, "domain", "d3a", "orchestration"),
        "domain.d3a.orchestration",
        "framework_default",
        ["framework_default", "ordered"],
        errors,
    )
    validate_registry(value_at(config, "general", "components") or [], "general.components", errors)
    validate_registry(
        value_at(config, "general", "test_domains") or [], "general.test_domains", errors
    )

    custom = value_at(config, "domain", "custom") or {}
    if not isinstance(custom, dict):
        custom = {}
    custom_orchestration = normalized_domain_orchestration(
        custom.get("orchestration"),
        "domain.custom.orchestration",
        "workflow_skill",
        ["workflow_skill", "ordered"],
        errors,
    )
    if "custom" in enabled_modes:
        if not present(custom.get("id")):
            errors.append("domain.custom.id is required")
        reserved_domain_keywords = ["d3a", "general", "custom"]
        if present(custom.get("id")) and str(custom.get("id")) in reserved_domain_keywords:
            errors.append(
                "domain.custom.id must not reuse a reserved domain keyword: {} "
                "(reserved: {})".format(
                    custom.get("id"), ", ".join(reserved_domain_keywords)
                )
            )
        if not present(custom.get("trigger_rules")):
            errors.append("domain.custom.trigger_rules must not be empty")
        validate_registry(custom.get("coding_layers") or [], "domain.custom.coding_layers", errors)
        validate_registry(custom.get("test_domains") or [], "domain.custom.test_domains", errors)
        if not present(custom.get("coding_layers")):
            errors.append("domain.custom.coding_layers must not be empty")
        if not present(custom.get("test_domains")):
            errors.append("domain.custom.test_domains must not be empty")
        for key in ("workflow_skill_ref", "planner_skill_ref", "completion_skill_ref"):
            if not present(custom.get(key)):
                errors.append("domain.custom.{} is required".format(key))
        allowed_contract_ids = [
            "task_contract",
            "verification_contract",
            "api_contract",
            "d3a_specification",
        ]
        if custom.get("required_contracts") is not None:
            required_contracts_config = custom.get("required_contracts")
            if not isinstance(required_contracts_config, list):
                errors.append(
                    "domain.custom.required_contracts must be a list of contract ids: {}".format(
                        ", ".join(allowed_contract_ids)
                    )
                )
            else:
                for contract_id in required_contracts_config:
                    if contract_id not in allowed_contract_ids:
                        errors.append(
                            "domain.custom.required_contracts contains unknown contract id {!r}; "
                            "allowed ids: {}".format(
                                contract_id, ", ".join(allowed_contract_ids)
                            )
                        )

    lane_policy = custom.get("lane_policy") or {}
    if not isinstance(lane_policy, dict):
        lane_policy = {}
    if "custom" in enabled_modes:
        policy_mode = lane_policy.get("mode")
        if policy_mode not in ("dynamic", "fixed", "not_applicable"):
            errors.append("domain.custom.lane_policy.mode is invalid")
        if policy_mode == "fixed" and lane_policy.get("selected_lane") not in (
            "fast",
            "lite",
            "complex",
        ):
            errors.append("domain.custom.lane_policy.selected_lane is required for fixed mode")
        if policy_mode != "fixed" and present(lane_policy.get("selected_lane")):
            errors.append(
                "domain.custom.lane_policy.selected_lane is allowed only for fixed mode"
            )

    if not isinstance(config.get("lane"), dict):
        config["lane"] = {}
    lane_default = value_at(config, "lane", "default")
    if lane_default is None:
        lane_default = "lite"
        config["lane"]["default"] = lane_default
        warnings.append("lane.default is absent; using lite")
    if lane_default not in ("fast", "lite", "complex"):
        errors.append("lane.default must be fast, lite, or complex")

    lane_profiles = value_at(config, "lane", "profiles")
    if lane_profiles is None:
        lane_profiles = {}
        warnings.append("lane.profiles is absent; using backward-compatible autonomous profiles")
    elif not isinstance(lane_profiles, dict):
        errors.append("lane.profiles must be a mapping")
        lane_profiles = {}
    for lane_id in ("fast", "lite", "complex"):
        profile = lane_profiles.get(lane_id)
        if profile is None:
            profile = {
                "skills": {"allow": [], "deny": [], "required": []},
                "orchestration": {"mode": "autonomous", "steps": []},
            }
            lane_profiles[lane_id] = profile
        elif not isinstance(profile, dict):
            errors.append("lane.profiles.{} must be a mapping".format(lane_id))
            continue
        skill_policy = profile.get("skills")
        if not isinstance(skill_policy, dict):
            errors.append("lane.profiles.{}.skills must be a mapping".format(lane_id))
            skill_policy = {}
        for key in ("allow", "deny", "required"):
            value = skill_policy.get(key)
            if not isinstance(value, list):
                errors.append(
                    "lane.profiles.{}.skills.{} must be a list".format(lane_id, key)
                )
            if isinstance(value, list) and len(set(value)) != len(value):
                errors.append(
                    "lane.profiles.{}.skills.{} must contain unique skill IDs".format(
                        lane_id, key
                    )
                )
        allowed = to_array(skill_policy.get("allow"))
        denied = to_array(skill_policy.get("deny"))
        required = to_array(skill_policy.get("required"))
        if [item for item in required if item in denied]:
            errors.append(
                "lane.profiles.{}.skills.required cannot also be denied".format(lane_id)
            )
        if allowed and [item for item in required if item not in allowed]:
            errors.append(
                "lane.profiles.{}.skills.required must be included in allow when allow "
                "is non-empty".format(lane_id)
            )

        orchestration = profile.get("orchestration")
        if not isinstance(orchestration, dict):
            errors.append("lane.profiles.{}.orchestration must be a mapping".format(lane_id))
            continue
        orchestration_mode = orchestration.get("mode")
        if orchestration_mode not in ("autonomous", "ordered"):
            errors.append(
                "lane.profiles.{}.orchestration.mode must be autonomous or ordered".format(
                    lane_id
                )
            )
        steps = orchestration.get("steps")
        if not isinstance(steps, list):
            errors.append(
                "lane.profiles.{}.orchestration.steps must be a list".format(lane_id)
            )
            continue
        if orchestration_mode == "ordered" and not steps:
            errors.append(
                "lane.profiles.{}.orchestration.steps must not be empty in ordered mode".format(
                    lane_id
                )
            )
        step_ids = []
        for index, step in enumerate(steps):
            path = "lane.profiles.{}.orchestration.steps[{}]".format(lane_id, index)
            if not isinstance(step, dict):
                errors.append("{} must be a mapping".format(path))
                continue
            if not present(step.get("id")):
                errors.append("{}.id is required".format(path))
            if present(step.get("id")) and step.get("id") in step_ids:
                errors.append("{}.id is duplicated".format(path))
            if present(step.get("id")):
                step_ids.append(step.get("id"))
            if not present(step.get("stage")):
                errors.append("{}.stage is required".format(path))
            if not present(step.get("skill_ids")):
                errors.append("{}.skill_ids must not be empty".format(path))
            if not isinstance(step.get("skill_ids"), list):
                errors.append("{}.skill_ids must be a list".format(path))
            if not isinstance(step.get("trigger_signals"), list):
                errors.append("{}.trigger_signals must be a list".format(path))

    alignment_default_bindings = {
        "intent_discovery": {"skill_ref": ".claude/skills/idc-intent-discovery/SKILL.md"},
        "brainstorming": {"skill_ref": ".claude/skills/idc-brainstorming/SKILL.md"},
        "intent_grilling": {"skill_ref": ".claude/skills/idc-intent-grilling/SKILL.md"},
        "intent_grilling_with_docs": {
            "skill_ref": ".claude/skills/idc-intent-grilling-with-docs/SKILL.md"
        },
        "intent_alignment": {"skill_ref": ".claude/skills/idc-intent-alignment/SKILL.md"},
    }
    alignment_default_steps = [
        {
            "id": "alignment-discovery",
            "stage": "discovery",
            "skill_ids": ["intent_discovery"],
            "trigger_signals": ["raw_idea"],
        },
        {
            "id": "alignment-brainstorming",
            "stage": "divergence",
            "skill_ids": ["brainstorming"],
            "trigger_signals": ["raw_idea", "alternatives_needed"],
        },
        {
            "id": "alignment-grilling",
            "stage": "clarification",
            "skill_ids": ["intent_grilling"],
            "trigger_signals": ["critical_gaps_remain", "clarification_required", "structured_requirement_input", "tr3_input"],
        },
        {
            "id": "alignment-grilling-with-docs",
            "stage": "clarification",
            "skill_ids": ["intent_grilling_with_docs"],
            "trigger_signals": ["docs_clarification_required"],
        },
        {
            "id": "alignment-check",
            "stage": "alignment_check",
            "skill_ids": ["intent_alignment"],
            "trigger_signals": [],
        },
    ]
    alignment_required_stages = ["discovery", "divergence", "clarification", "alignment_check"]
    alignment_signal_floor = ["raw_idea", "critical_gaps_remain"]
    alignment_clarification_signal_floor = ["structured_requirement_input", "tr3_input"]

    alignment_section = config.get("alignment")
    alignment_bindings_config = None
    alignment_orchestration_config = None
    if alignment_section is not None and not isinstance(alignment_section, dict):
        errors.append("alignment must be a mapping")
    elif isinstance(alignment_section, dict):
        alignment_bindings_config = alignment_section.get("bindings")
        alignment_orchestration_config = alignment_section.get("orchestration")
        if alignment_bindings_config is not None and not isinstance(
            alignment_bindings_config, dict
        ):
            errors.append("alignment.bindings must be a mapping")
            alignment_bindings_config = None
        if alignment_orchestration_config is not None and not isinstance(
            alignment_orchestration_config, dict
        ):
            errors.append("alignment.orchestration must be a mapping")
            alignment_orchestration_config = None

    if alignment_bindings_config is None or alignment_orchestration_config is None:
        # Missing alignment section, bindings, or orchestration falls back to the
        # framework default chain. No warning is recorded so an unconfigured team's
        # resolve output changes only by the materialized alignment section.
        alignment_bindings = {
            key: dict(binding) for key, binding in alignment_default_bindings.items()
        }
        for key, binding in alignment_bindings.items():
            default_ref = binding.get("skill_ref")
            resolved_ref = resolve_file_ref(default_ref, team_root, harness_root)
            if not Path(resolved_ref).is_file():
                errors.append(
                    "alignment.bindings.{}.skill_ref does not exist: {} (resolved to {})".format(
                        key, default_ref, resolved_ref
                    )
                )
            binding["skill_ref"] = resolved_ref
        alignment_effective = {
            "source": "framework-default",
            "bindings": alignment_bindings,
            "orchestration": {
                "mode": "ordered",
                "steps": [dict(step) for step in alignment_default_steps],
            },
        }
    else:
        alignment_bindings = {}
        for key, binding in alignment_bindings_config.items():
            path = "alignment.bindings.{}".format(key)
            if not isinstance(binding, dict):
                errors.append("{} must be a mapping".format(path))
                continue
            original_ref = binding.get("skill_ref")
            if not present(original_ref):
                errors.append("{}.skill_ref is required".format(path))
                continue
            resolved_ref = resolve_file_ref(original_ref, team_root, harness_root)
            resolved_path = Path(resolved_ref)
            if not (
                resolved_path.name == "SKILL.md"
                and IDC_SKILL_DIR_RE.match(resolved_path.parent.name)
            ):
                errors.append(
                    "{}.skill_ref must resolve to an idc-*/SKILL.md path "
                    "(idc- prefix discipline): {}".format(path, original_ref)
                )
                continue
            if not Path(resolved_ref).is_file():
                errors.append(
                    "{}.skill_ref does not exist: {} (resolved to {})".format(
                        path, original_ref, resolved_ref
                    )
                )
            binding["skill_ref"] = resolved_ref
            alignment_bindings[key] = binding

        if alignment_orchestration_config.get("mode") != "ordered":
            errors.append("alignment.orchestration.mode must be ordered")
        alignment_steps = alignment_orchestration_config.get("steps")
        if not isinstance(alignment_steps, list):
            errors.append("alignment.orchestration.steps must be a list")
            alignment_steps = []
        if not alignment_steps:
            errors.append("alignment.orchestration.steps must not be empty")
        alignment_step_ids = []
        for index, step in enumerate(alignment_steps):
            path = "alignment.orchestration.steps[{}]".format(index)
            if not isinstance(step, dict):
                errors.append("{} must be a mapping".format(path))
                continue
            if not present(step.get("id")):
                errors.append("{}.id is required".format(path))
            if present(step.get("id")) and step.get("id") in alignment_step_ids:
                errors.append("{}.id is duplicated".format(path))
            if present(step.get("id")):
                alignment_step_ids.append(step.get("id"))
            if not present(step.get("stage")):
                errors.append("{}.stage is required".format(path))
            if not present(step.get("skill_ids")):
                errors.append("{}.skill_ids must not be empty".format(path))
            if not isinstance(step.get("skill_ids"), list):
                errors.append("{}.skill_ids must be a list".format(path))
            if not isinstance(step.get("trigger_signals"), list):
                errors.append("{}.trigger_signals must be a list".format(path))
            for skill_id in to_array(step.get("skill_ids")):
                bound = alignment_bindings.get(skill_id)
                if not (isinstance(bound, dict) and present(bound.get("skill_ref"))):
                    errors.append(
                        "{}.skill_ids references {} without an alignment.bindings "
                        "entry: NEEDS_TEAM_CONFIG".format(path, skill_id)
                    )

        alignment_covered_stages = uniq(
            [
                step.get("stage")
                for step in alignment_steps
                if isinstance(step, dict) and present(step.get("stage"))
            ]
        )
        for required_stage in alignment_required_stages:
            if required_stage in alignment_covered_stages:
                continue
            if required_stage == "alignment_check":
                errors.append(
                    "alignment.orchestration stage alignment_check cannot be removed; "
                    "rebind alignment.bindings.intent_alignment.skill_ref instead"
                )
            else:
                errors.append(
                    "alignment.orchestration NEEDS_ORCHESTRATION_MAPPING: ordered mode "
                    "has no step for stage {}".format(required_stage)
                )

        alignment_covered_signals = [
            signal
            for step in alignment_steps
            if isinstance(step, dict) and isinstance(step.get("trigger_signals"), list)
            for signal in step.get("trigger_signals")
        ]
        for required_signal in alignment_signal_floor:
            if required_signal not in alignment_covered_signals:
                errors.append(
                    "alignment.orchestration.trigger_signals must cover the framework "
                    "signal floor: {}".format(required_signal)
                )
        clarification_signals = [
            signal
            for step in alignment_steps
            if isinstance(step, dict)
            and step.get("stage") == "clarification"
            and isinstance(step.get("trigger_signals"), list)
            for signal in step.get("trigger_signals")
        ]
        for required_signal in alignment_clarification_signal_floor:
            if required_signal not in clarification_signals:
                errors.append(
                    "alignment.orchestration clarification trigger_signals must cover "
                    "the mandatory maturity signal: {} (NEEDS_TEAM_CONFIG)".format(
                        required_signal
                    )
                )

        alignment_effective = {
            "source": "configured",
            "bindings": alignment_bindings,
            "orchestration": {"mode": "ordered", "steps": alignment_steps},
        }

    capability_selection = config.get("capability_selection")
    if capability_selection is None:
        capability_selection = {
            "mode": "autonomous_minimal_sufficient",
            "lane_profiles": {
                "fast": {"max_optional_skills": 1},
                "lite": {"max_optional_skills": 3},
                "complex": {"max_optional_skills": None},
            },
            "fixed_workflow": {"max_optional_skills": None},
            "require_selected_and_skipped_reasons": True,
        }
        config["capability_selection"] = capability_selection
        warnings.append("capability_selection is absent; using safe defaults")
    if not isinstance(capability_selection, dict):
        capability_selection = {}
    if capability_selection.get("mode") != "autonomous_minimal_sufficient":
        errors.append("capability_selection.mode must be autonomous_minimal_sufficient")
    if capability_selection.get("require_selected_and_skipped_reasons") is not True:
        errors.append(
            "capability_selection.require_selected_and_skipped_reasons must be true"
        )
    for lane_id in ("fast", "lite", "complex"):
        budget = value_at(capability_selection, "lane_profiles", lane_id, "max_optional_skills")
        if budget is not None and (
            not isinstance(budget, int) or isinstance(budget, bool) or budget < 0
        ):
            errors.append(
                "capability_selection.lane_profiles.{}.max_optional_skills must be null "
                "or a non-negative integer".format(lane_id)
            )
    fixed_budget = value_at(capability_selection, "fixed_workflow", "max_optional_skills")
    if fixed_budget is not None and (
        not isinstance(fixed_budget, int) or isinstance(fixed_budget, bool) or fixed_budget < 0
    ):
        errors.append(
            "capability_selection.fixed_workflow.max_optional_skills must be null or a "
            "non-negative integer"
        )

    bindings = config.get("bindings") or {}
    if not isinstance(bindings, dict):
        errors.append("bindings must be a mapping")
        bindings = {}

    extensions = config.get("adapter_extensions") or []
    if not isinstance(extensions, list):
        errors.append("adapter_extensions must be a list")
        extensions = []
    for index, entry in enumerate(extensions):
        path = "adapter_extensions[{}]".format(index)
        if not isinstance(entry, dict):
            errors.append("{} must be a mapping".format(path))
            continue
        if not str(entry.get("id") or "").startswith("idc-"):
            errors.append("{}.id must start with idc-".format(path))
        if not present(entry.get("capability_keys")):
            errors.append("{}.capability_keys must not be empty".format(path))
        if not present(entry.get("allowed_stages")):
            errors.append("{}.allowed_stages must not be empty".format(path))
        if not present(entry.get("skill_ref")):
            errors.append("{}.skill_ref is required".format(path))
        if entry.get("execution_role") is None:
            entry["execution_role"] = "atomic_capability"
            warnings.append(
                "{}.execution_role is absent; using atomic_capability".format(path)
            )
        if entry.get("execution_role") not in (
            "atomic_capability",
            "verification_capability",
            "pre_alignment_capability",
        ):
            errors.append(
                "{}.execution_role cannot own orchestration; use atomic_capability, "
                "verification_capability, or pre_alignment_capability".format(path)
            )
        for key in ("composes_with", "supersedes"):
            if entry.get(key) is None:
                entry[key] = []
            if not isinstance(entry.get(key), list):
                errors.append("{}.{} must be a list".format(path, key))
        if [
            item
            for item in to_array(entry.get("composes_with"))
            if item in to_array(entry.get("supersedes"))
        ]:
            errors.append(
                "{} cannot both compose with and supersede the same skill".format(path)
            )
        reserved_capability_keys = [
            "domain_selection",
            "lane_selection",
            "contract_gate",
            "human_alignment",
            "completion_gate",
            "workflow_orchestration",
            "domain_execution",
            "delegation",
        ]
        attempted_keys = [
            item for item in to_array(entry.get("capability_keys")) if item in reserved_capability_keys
        ]
        if attempted_keys:
            errors.append(
                "{}.capability_keys contains protected orchestration ownership: {}".format(
                    path, ", ".join(str(item) for item in attempted_keys)
                )
            )
        forbidden_ownership = ["domain_selection", "lane_selection", "contract_gate", "human_alignment", "completion_gate"]
        may_override = entry.get("may_override")
        override_keys = list(may_override.keys()) if isinstance(may_override, dict) else []
        attempted = [item for item in forbidden_ownership if item in override_keys]
        if attempted:
            errors.append(
                "{}.may_override cannot contain protected ownership keys: {}".format(
                    path, ", ".join(str(item) for item in attempted)
                )
            )

    skill_refs = []
    for name, binding in bindings.items():
        if isinstance(binding, dict) and present(binding.get("skill_ref")):
            skill_refs.append(["bindings.{}.skill_ref".format(name), binding, "skill_ref"])
    for key in ("workflow_skill_ref", "planner_skill_ref", "completion_skill_ref"):
        if present(custom.get(key)):
            skill_refs.append(["domain.custom.{}".format(key), custom, key])
    for index, entry in enumerate(extensions):
        if isinstance(entry, dict) and present(entry.get("skill_ref")):
            skill_refs.append(
                ["adapter_extensions[{}].skill_ref".format(index), entry, "skill_ref"]
            )
    provider_ref = value_at(config, "knowledge", "repo_context", "provider_skill_ref")
    repo_context = value_at(config, "knowledge", "repo_context")
    if present(provider_ref) and isinstance(repo_context, dict):
        skill_refs.append(
            ["knowledge.repo_context.provider_skill_ref", repo_context, "provider_skill_ref"]
        )

    for path, owner, key in skill_refs:
        original_ref = owner.get(key)
        protected_atomic_skills = [
            "idc-workflow",
            "idc-general-coding",
            "idc-d3a-coding",
            "idc-intent-discovery",
            "idc-intent-grilling",
            "idc-intent-alignment",
            "idc-team-config",
            "idc-self-optimization",
            "idc-skill-adapter-router",
        ]
        if (path.startswith("bindings.") or path.startswith("adapter_extensions[")) and any(
            "/{}/".format(name) in str(original_ref) for name in protected_atomic_skills
        ):
            errors.append(
                "{} binds an orchestration/domain Skill as an atomic capability: {}".format(
                    path, original_ref
                )
            )
        if (
            path.startswith("bindings.")
            and "/idc-brainstorming/" in str(original_ref)
            and path != "bindings.brainstorming.skill_ref"
        ):
            errors.append("{} binds idc-brainstorming outside the brainstorming slot".format(path))
        resolved_ref = resolve_file_ref(original_ref, team_root, harness_root)
        if SCHEME_RE.match(resolved_ref):
            owner[key] = resolved_ref
            continue
        if not Path(resolved_ref).is_file():
            errors.append(
                "{} does not exist: {} (resolved to {})".format(path, original_ref, resolved_ref)
            )
        owner[key] = resolved_ref

    knowledge_refs = []
    registry_sections = [
        ("domain.d3a.dt_domains", value_at(config, "domain", "d3a", "dt_domains")),
        ("domain.custom.coding_layers", custom.get("coding_layers")),
        ("domain.custom.test_domains", custom.get("test_domains")),
        ("general.components", value_at(config, "general", "components")),
        ("general.test_domains", value_at(config, "general", "test_domains")),
    ]
    for path, entries in registry_sections:
        for index, entry in enumerate(to_array(entries)):
            if isinstance(entry, dict) and present(entry.get("knowledge_ref")):
                knowledge_refs.append(
                    ["{}[{}].knowledge_ref".format(path, index), entry, "knowledge_ref"]
                )
    knowledge = config.get("knowledge")
    if isinstance(knowledge, dict):
        for key in ("architecture_doc_ref", "feature_docs_root_ref", "verification_mapping_ref"):
            if present(knowledge.get(key)):
                knowledge_refs.append(["knowledge.{}".format(key), knowledge, key])
        if isinstance(knowledge.get("layer_docs"), dict):
            for layer, ref in knowledge.get("layer_docs").items():
                if present(ref):
                    knowledge_refs.append(
                        ["knowledge.layer_docs.{}".format(layer), knowledge["layer_docs"], layer]
                    )
        lane_docs = knowledge.get("lane_docs")
        if lane_docs is None:
            knowledge["lane_docs"] = {"fast": [], "lite": [], "complex": []}
        elif not isinstance(lane_docs, dict):
            errors.append("knowledge.lane_docs must be a mapping")
        else:
            unknown_lanes = [
                lane for lane in lane_docs.keys() if lane not in ("fast", "lite", "complex")
            ]
            if unknown_lanes:
                errors.append(
                    "knowledge.lane_docs contains unknown lanes: {}".format(
                        ", ".join(str(item) for item in unknown_lanes)
                    )
                )
            for lane_id in ("fast", "lite", "complex"):
                refs = lane_docs.get(lane_id)
                if refs is None:
                    lane_docs[lane_id] = []
                elif not isinstance(refs, list):
                    errors.append("knowledge.lane_docs.{} must be a list".format(lane_id))
                else:
                    for index, ref in enumerate(refs):
                        if present(ref):
                            knowledge_refs.append(
                                [
                                    "knowledge.lane_docs.{}[{}]".format(lane_id, index),
                                    refs,
                                    index,
                                ]
                            )
        if isinstance(repo_context, dict) and present(repo_context.get("policy_ref")):
            knowledge_refs.append(["knowledge.repo_context.policy_ref", repo_context, "policy_ref"])

    for path, owner, key in knowledge_refs:
        original_ref = owner.get(key) if isinstance(key, str) else owner[key]
        resolved_ref = resolve_file_ref(original_ref, team_root, harness_root)
        if SCHEME_RE.match(resolved_ref):
            if isinstance(key, str):
                owner[key] = resolved_ref
            else:
                owner[key] = resolved_ref
            continue
        if not Path(resolved_ref).exists():
            errors.append(
                "{} does not exist: {} (resolved to {})".format(path, original_ref, resolved_ref)
            )
        if isinstance(key, str):
            owner[key] = resolved_ref
        else:
            owner[key] = resolved_ref

    self_optimization = config.get("self_optimization")
    if self_optimization is None:
        self_optimization = {
            "mode": "disabled",
            "event_store_ref": None,
            "replay_cases_ref": None,
            "team_overlay_ref": None,
            "promotion_requires_human_alignment": True,
            "auto_modify_core": False,
        }
        config["self_optimization"] = self_optimization
        warnings.append("self_optimization is absent; using disabled safe defaults")
    if not isinstance(self_optimization, dict):
        self_optimization = {}
    optimization_mode = self_optimization.get("mode")
    if optimization_mode not in ("disabled", "observe", "propose_only"):
        errors.append("self_optimization.mode must be disabled, observe, or propose_only")
    if optimization_mode in ("observe", "propose_only") and not present(
        self_optimization.get("event_store_ref")
    ):
        errors.append(
            "self_optimization.event_store_ref is required when optimization is enabled"
        )
    if optimization_mode == "propose_only":
        if not present(self_optimization.get("replay_cases_ref")):
            errors.append(
                "self_optimization.replay_cases_ref is required in propose_only mode"
            )
        if not present(self_optimization.get("team_overlay_ref")):
            errors.append(
                "self_optimization.team_overlay_ref is required in propose_only mode"
            )
    if self_optimization.get("auto_modify_core") is not False:
        errors.append("self_optimization.auto_modify_core must remain false")
    if self_optimization.get("promotion_requires_human_alignment") is not True:
        errors.append("self_optimization.promotion_requires_human_alignment must remain true")

    builtin_d3a_layers = load_builtin_knowledge_registry(
        harness_root,
        ".claude/skills/idc-workflow/references/registries/d3a-layers.yaml",
        "layers",
        errors,
    )
    builtin_dt_domains = load_builtin_knowledge_registry(
        harness_root,
        ".claude/skills/idc-workflow/references/registries/dt-domains.yaml",
        "domains",
        errors,
    )
    builtin_general_components = load_builtin_knowledge_registry(
        harness_root,
        ".claude/skills/idc-workflow/references/registries/general-components.yaml",
        "components",
        errors,
    )
    builtin_general_test_domains = load_builtin_knowledge_registry(
        harness_root,
        ".claude/skills/idc-workflow/references/registries/general-test-domains.yaml",
        "test_domains",
        errors,
    )

    d3a_overrides = value_at(config, "domain", "d3a", "dt_domains") or []
    general_component_overrides = value_at(config, "general", "components") or []
    general_test_overrides = value_at(config, "general", "test_domains") or []
    d3a_test_domains = builtin_dt_domains if not d3a_overrides else d3a_overrides
    general_components = (
        builtin_general_components if not general_component_overrides else general_component_overrides
    )
    general_test_domains = (
        builtin_general_test_domains if not general_test_overrides else general_test_overrides
    )

    available_knowledge_catalog = {
        "d3a": {"layers": builtin_d3a_layers, "test_domains": d3a_test_domains},
        "general": {"components": general_components, "test_domains": general_test_domains},
        "custom": {
            "layers": to_array(custom.get("coding_layers")),
            "test_domains": to_array(custom.get("test_domains")),
        },
    }
    if configured_enabled_modes is None:
        knowledge_catalog = available_knowledge_catalog
    else:
        knowledge_catalog = {
            domain_id: available_knowledge_catalog[domain_id]
            for domain_id in enabled_modes
            if domain_id in available_knowledge_catalog
        }

    def build_effective_domain(domain_mode):
        if legacy_is_fixed_domain(domain_mode):
            return {
                "id": "d3a",
                "source": "builtin",
                "lane_applicability": "not_applicable",
                "execution_profile": "d3a_fixed_workflow",
                "fixed_architecture": {
                    "lane_mode": "not_applicable",
                    "coding_layer_ids": D3A_LAYER_IDS,
                    "default_test_domain_ids": D3A_TEST_DOMAIN_IDS,
                },
                "orchestration": d3a_orchestration,
                "coding_layers_source": "registries/d3a-layers.yaml",
                "test_domains_source": (
                    "registries/dt-domains.yaml" if not d3a_overrides else "team-config.yaml"
                ),
                "coding_layers": builtin_d3a_layers,
                "test_domains": d3a_test_domains,
            }
        if domain_mode == "general":
            return {
                "id": "general",
                "source": "builtin",
                "lane_applicability": "applicable",
                "execution_profile": "lane_driven",
                "components": general_components,
                "test_domains": general_test_domains,
            }
        if domain_mode == "custom":
            return {
                "id": custom.get("id"),
                "source": "team-config-inline",
                "lane_policy": custom.get("lane_policy"),
                "trigger_rules": custom.get("trigger_rules"),
                "coding_layers": custom.get("coding_layers"),
                "test_domains": custom.get("test_domains"),
                "required_contracts": custom.get("required_contracts"),
                "workflow_skill_ref": custom.get("workflow_skill_ref"),
                "planner_skill_ref": custom.get("planner_skill_ref"),
                "completion_skill_ref": custom.get("completion_skill_ref"),
                "orchestration": custom_orchestration,
            }
        return {}

    domain_modules_effective = {
        enabled_mode: build_effective_domain(enabled_mode) for enabled_mode in enabled_modes
    }
    domain_effective = build_effective_domain(mode)
    domains_effective = {
        "enabled": enabled_modes,
        "default": mode,
        "modules": domain_modules_effective,
    }
    lane_applicabilities = [
        domain.get("lane_applicability")
        or value_at(domain, "lane_policy", "mode")
        for domain in domain_modules_effective.values()
    ]
    diagnostics = []
    if lane_applicabilities and all(
        applicability == "not_applicable" for applicability in lane_applicabilities
    ):
        diagnostics = [
            {
                "path": "lane.profiles.{}".format(lane_id),
                "status": "UNREACHABLE",
                "reason": "all enabled domains declare Lane not_applicable",
            }
            for lane_id in ("fast", "lite", "complex")
        ]
    diagnostics.append(
        {
            "path": "domain",
            "status": "FALLBACK_USED",
            "reason": "config_version 1 uses implicit Domain ownership",
        }
    )

    capability_registry_path = (
        harness_root / ".claude/skills/idc-workflow/references/registries/team-capabilities.yaml"
    )
    capability_rows = []
    if capability_registry_path.is_file():
        try:
            with open(capability_registry_path, "r", encoding="utf-8") as handle:
                registry = yaml.safe_load(handle.read()) or {}
            capability_rows = (registry or {}).get("team_capabilities") or []
        except yaml.YAMLError as error:
            errors.append("team capability registry is invalid: {}".format(str(error)))
    else:
        errors.append("team capability registry is missing: {}".format(capability_registry_path))

    available_capabilities = []
    for row in capability_rows:
        if not isinstance(row, dict):
            continue
        skill_ref = dotted_value(config, row.get("binding_path"))
        if present(skill_ref):
            merged = dict(row)
            merged.update({"skill_ref": skill_ref, "source": "fixed-binding"})
            available_capabilities.append(merged)
    for entry in extensions:
        if not (isinstance(entry, dict) and present(entry.get("skill_ref"))):
            continue
        merged = dict(entry)
        merged.update(
            {
                "binding_path": "adapter_extensions",
                # Ruby `entry["eligible_lanes"] || [...]` keeps an explicit []
                # truthy; Python `or` would swallow it.
                "eligible_lanes": (
                    entry["eligible_lanes"]
                    if entry.get("eligible_lanes") is not None
                    else ["fast", "lite", "complex"]
                ),
                "execution_profiles": entry.get("execution_profiles") or [],
                "trigger_signals": entry.get("trigger_signals") or [],
                "source": "adapter-extension",
            }
        )
        available_capabilities.append(merged)

    registration_conflicts = []
    registration_overrides = []
    available_ids = [capability.get("id") for capability in available_capabilities]
    duplicate_ids = [
        item_id
        for item_id, count in {
            item_id: available_ids.count(item_id) for item_id in available_ids
        }.items()
        if count > 1
    ]
    if duplicate_ids:
        errors.append(
            "available capability IDs are duplicated: {}".format(
                ", ".join(str(item) for item in duplicate_ids)
            )
        )

    for capability in available_capabilities:
        for target in to_array(capability.get("composes_with")):
            if target not in available_ids:
                errors.append(
                    "{}.composes_with references unavailable capability: {}".format(
                        capability.get("id"), target
                    )
                )
        for target in to_array(capability.get("supersedes")):
            if target not in available_ids:
                errors.append(
                    "{}.supersedes references unavailable capability: {}".format(
                        capability.get("id"), target
                    )
                )
            if target == capability.get("id"):
                errors.append("{} cannot supersede itself".format(capability.get("id")))

    for left, right in itertools.combinations(available_capabilities, 2):
        shared_keys = [
            item for item in to_array(left.get("capability_keys")) if item in to_array(right.get("capability_keys"))
        ]
        shared_stages = [
            item for item in to_array(left.get("allowed_stages")) if item in to_array(right.get("allowed_stages"))
        ]
        shared_lanes = [
            item for item in to_array(left.get("eligible_lanes")) if item in to_array(right.get("eligible_lanes"))
        ]
        shared_profiles = [
            item
            for item in to_array(left.get("execution_profiles"))
            if item in to_array(right.get("execution_profiles"))
        ]
        both_unscoped = (
            not to_array(left.get("eligible_lanes"))
            and not to_array(right.get("eligible_lanes"))
            and not to_array(left.get("execution_profiles"))
            and not to_array(right.get("execution_profiles"))
        )
        if (
            not shared_keys
            or not shared_stages
            or (not shared_lanes and not shared_profiles and not both_unscoped)
        ):
            continue

        left_signals = to_array(left.get("trigger_signals"))
        right_signals = to_array(right.get("trigger_signals"))
        signals_overlap = (
            not left_signals
            or not right_signals
            or any(signal in right_signals for signal in left_signals)
        )
        if not signals_overlap:
            continue

        composed = right.get("id") in to_array(
            left.get("composes_with")
        ) or left.get("id") in to_array(right.get("composes_with"))
        superseded = right.get("id") in to_array(
            left.get("supersedes")
        ) or left.get("id") in to_array(right.get("supersedes"))
        detail = {
            "left": left.get("id"),
            "right": right.get("id"),
            "capability_keys": shared_keys,
            "stages": shared_stages,
            "lanes": shared_lanes,
            "execution_profiles": shared_profiles,
        }
        if composed or superseded:
            detail["resolution"] = "compose" if composed else "supersede"
            registration_overrides.append(detail)
        else:
            registration_conflicts.append(detail)
            errors.append(
                "ambiguous capability registration: {} conflicts with {} on {} at {}".format(
                    left.get("id"),
                    right.get("id"),
                    ", ".join(str(item) for item in shared_keys),
                    ", ".join(str(item) for item in shared_stages),
                )
            )

    capability_by_id = {
        capability.get("id"): capability for capability in available_capabilities
    }
    for lane_id in ("fast", "lite", "complex"):
        profile = lane_profiles.get(lane_id)
        if not isinstance(profile, dict):
            continue

        skill_policy = profile.get("skills") if isinstance(profile.get("skills"), dict) else {}
        configured_ids = [
            skill_id
            for key in ("allow", "deny", "required")
            for skill_id in to_array(skill_policy.get(key))
        ]
        steps = value_at(profile, "orchestration", "steps")
        configured_ids += [
            skill_id
            for step in to_array(steps)
            if isinstance(step, dict)
            for skill_id in to_array(step.get("skill_ids"))
        ]
        for skill_id in uniq(configured_ids):
            capability = capability_by_id.get(skill_id)
            if capability is None:
                errors.append(
                    "lane.profiles.{} references unavailable skill ID: {}".format(lane_id, skill_id)
                )
                continue
            if lane_id not in to_array(capability.get("eligible_lanes")):
                errors.append(
                    "lane.profiles.{} references lane-ineligible skill ID: {}".format(
                        lane_id, skill_id
                    )
                )

        for index, step in enumerate(to_array(steps)):
            if not (isinstance(step, dict) and present(step.get("stage"))):
                continue
            for skill_id in to_array(step.get("skill_ids")):
                capability = capability_by_id.get(skill_id)
                if capability is None:
                    continue
                if step.get("stage") not in to_array(capability.get("allowed_stages")):
                    errors.append(
                        "lane.profiles.{}.orchestration.steps[{}] uses {} outside its "
                        "allowed stage {}".format(lane_id, index, skill_id, step.get("stage"))
                    )

    for domain_id, orchestration in (
        ("d3a", d3a_orchestration),
        ("custom", custom_orchestration),
    ):
        if not (isinstance(orchestration, dict) and orchestration.get("mode") == "ordered"):
            continue
        for index, step in enumerate(to_array(orchestration.get("steps"))):
            if not isinstance(step, dict):
                continue
            for skill_id in to_array(step.get("skill_ids")):
                capability = capability_by_id.get(skill_id)
                if capability is None:
                    errors.append(
                        "domain.{}.orchestration.steps[{}] references unavailable skill "
                        "ID: {}".format(domain_id, index, skill_id)
                    )
                    continue
                if present(step.get("stage")) and step.get("stage") not in to_array(
                    capability.get("allowed_stages")
                ):
                    errors.append(
                        "domain.{}.orchestration.steps[{}] uses {} outside its allowed "
                        "stage {}".format(domain_id, index, skill_id, step.get("stage"))
                    )

    effective = {
        "generated": True,
        "source_ref": str(config_path),
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "config_version": config.get("config_version"),
        "team": dict(config.get("team") or {}, repo_path=str(team_root)),
        "domain": domain_effective,
        "bindings": {
            name: binding
            for name, binding in bindings.items()
            if isinstance(binding, dict) and present(binding.get("skill_ref"))
        },
        "adapter_extensions": extensions,
        "available_capabilities": available_capabilities,
        "registration_audit": {
            "status": "PASS" if not registration_conflicts else "FAIL",
            "conflicts": registration_conflicts,
            "declared_overrides": registration_overrides,
        },
        "knowledge": config.get("knowledge"),
        "knowledge_catalog": knowledge_catalog,
        "lane": {"default": lane_default, "profiles": lane_profiles},
        "diagnostics": diagnostics,
        "alignment": alignment_effective,
        "capability_selection": capability_selection,
        "self_optimization": self_optimization,
        "readiness": {
            "status": "READY" if not errors else "INVALID",
            "errors": errors,
            "warnings": warnings,
        },
    }
    if configured_enabled_modes is not None:
        effective["domains"] = domains_effective

    if errors:
        print("INVALID team-config.yaml", file=sys.stderr)
        for error in errors:
            print("- {}".format(error), file=sys.stderr)
        sys.exit(1)

    if options.output:
        output_path = Path(os.path.abspath(options.output))
        os.makedirs(str(output_path.parent), exist_ok=True)
        alias_free_effective = json.loads(json.dumps(effective))
        temporary_path = output_path.parent / ".{}.tmp-{}".format(
            output_path.name, os.getpid()
        )
        with open(temporary_path, "w", encoding="utf-8") as handle:
            handle.write(
                "# Generated by idc-team-config. Do not edit.\n"
                + yaml.dump(alias_free_effective, allow_unicode=True, sort_keys=False)
            )
        os.replace(str(temporary_path), str(output_path))
        print("READY: wrote {}".format(output_path))
    else:
        print("READY: team-config.yaml is valid")


if __name__ == "__main__":
    main()
