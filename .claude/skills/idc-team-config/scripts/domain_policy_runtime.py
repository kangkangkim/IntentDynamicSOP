"""Small shared validators for file-backed Domain policy and ordered occurrences."""
import hashlib
import json
from pathlib import Path

import yaml

LANES = {"fast", "lite", "complex"}
STAGES = {"planning", "implementation", "verification", "completion", "review", "fix",
          "discovery", "divergence", "clarification", "alignment_check", "pre_alignment",
          "dt_design", "dt_writing", "dt_build", "tran_build", "debugging", "finishing"}
CAPABILITY_FIELDS = {"id", "skill_ref", "allowed_stages", "eligible_lanes",
                     "capability_keys", "trigger_signals", "execution_profiles", "supersedes",
                     "execution_role", "evidence_required", "requires", "blocks_when",
                     "composes_with", "input_contract_ref", "output_contract_ref", "binding_path",
                     "source"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def mapping(value, fields, label):
    if not isinstance(value, dict) or set(value) - set(fields):
        raise ValueError("POLICY_INVALID: unsupported {} fields".format(label))
    return value


def strings(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        raise ValueError("POLICY_INVALID: {} requires a string list".format(label))
    return value


def file_hashes(refs):
    return {str(Path(ref).resolve()): hashlib.sha256(Path(ref).read_bytes()).hexdigest()
            for ref in sorted(set(refs))}


def validate_profiles(profiles, capabilities):
    if not isinstance(profiles, dict) or set(profiles) - LANES:
        raise ValueError("POLICY_INVALID: unsupported Lane")
    for lane, profile in profiles.items():
        ordered_rows(profile, {}, capabilities, lane, [], validate_only=True)


def ordered_rows(profile, module, capabilities, lane, signals, validate_only=False):
    if not isinstance(profile, dict):
        raise ValueError("POLICY_INVALID: Lane profile must be a mapping")
    skill_policy = mapping(profile.get("skills", {}), {"allow", "deny", "required"}, "skills")
    by_id = {cap["id"]: cap for cap in capabilities}
    for key, ids in skill_policy.items():
        if set(strings(ids, key)) - set(by_id):
            raise ValueError("UNKNOWN_SKILL: Lane policy references an unregistered Skill")
    orchestration = module.get("orchestration") or profile.get("orchestration") or {}
    mapping(orchestration, {"mode", "steps"}, "orchestration")
    if orchestration.get("mode", "autonomous") not in {"ordered", "autonomous"}:
        raise ValueError("POLICY_INVALID: unsupported orchestration mode")
    steps, rows, seen = orchestration.get("steps", []), [], set()
    if not isinstance(steps, list):
        raise ValueError("POLICY_INVALID: steps must be a list")
    for step in steps:
        mapping(step, {"id", "stage", "skill_ids", "trigger_signals"}, "step/guard")
        step_id, stage = step.get("id"), step.get("stage")
        if not isinstance(step_id, str) or not step_id or step_id in seen or stage not in STAGES:
            raise ValueError("POLICY_INVALID: invalid step identity or stage")
        seen.add(step_id)
        triggers = strings(step.get("trigger_signals", []), "trigger_signals")
        ids = strings(step.get("skill_ids"), "skill_ids")
        if not ids:
            raise ValueError("POLICY_INVALID: empty Skill step")
        for skill_id in ids:
            cap = by_id.get(skill_id)
            if cap is None:
                raise ValueError("UNKNOWN_SKILL: {}".format(skill_id))
            if (stage not in cap.get("allowed_stages", [])
                    or (lane is not None and lane not in cap.get("eligible_lanes", []))
                    or skill_id in skill_policy.get("deny", [])
                    or (skill_policy.get("allow") and skill_id not in skill_policy["allow"])):
                raise ValueError("POLICY_INVALID: configured Skill is ineligible")
            if all(trigger in signals for trigger in triggers):
                rows.append({"step_id": step_id, "stage": stage, "capability_id": skill_id,
                             "skill_ref": cap.get("skill_ref"), "execution_order": len(rows) + 1})
    if not validate_only and (orchestration.get("mode") != "ordered" or not rows):
        raise ValueError("ORDERED_SELECTION_REQUIRED: configured ordered workflow is required")
    return rows


def materialize_policy(module, resolve_ref):
    """Consume declared policy files; returned files form the byte identity manifest."""
    workflow_path, capability_path = module["workflow_profile_ref"], module["capability_policy_ref"]
    workflow = (yaml.safe_load(Path(workflow_path).read_text()) or {}).get("workflow_profile")
    policy = (yaml.safe_load(Path(capability_path).read_text()) or {}).get("capability_policy")
    completion_document = yaml.safe_load(Path(module["completion_predicate_ref"]).read_text()) or {}
    mapping(workflow, {"id", "execution_profile", "domain_execution_skill_ref", "execution_contract_ref",
                       "phase_refs", "lane_profiles", "orchestration", "planner_skill_ref"},
            "workflow_profile")
    mapping(policy, {"id", "capabilities", "allowed", "execution_profile", "lane_applicability",
                     "selection_profile", "fixed_architecture", "required_contracts"}, "capability_policy")
    refs = [module["pack_ref"], workflow_path, capability_path, module["completion_predicate_ref"]]
    refs.extend(module["registries"].values())
    for registry_ref in module["registries"].values():
        registry = yaml.safe_load(Path(registry_ref).read_text()) or {}
        if not isinstance(registry, dict):
            raise ValueError("POLICY_INVALID: registry must be a mapping")
        rows = next((registry[key] for key in ("layers", "coding_layers", "components",
                    "domains", "test_domains") if key in registry), [])
        if not isinstance(rows, list):
            raise ValueError("POLICY_INVALID: registry rows must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("POLICY_INVALID: registry row must be a mapping")
            knowledge_ref = row.get("knowledge_ref") or row.get("knowledge_file")
            if knowledge_ref:
                refs.append(resolve_ref(knowledge_ref, Path(registry_ref).parent))
    capabilities = policy.get("capabilities", [])
    if not isinstance(capabilities, list):
        raise ValueError("POLICY_INVALID: capabilities must be a list")
    bound, seen = [], set()
    for raw in capabilities:
        cap = dict(mapping(raw, CAPABILITY_FIELDS, "capability"))
        cid = cap.get("id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ValueError("POLICY_INVALID: capability IDs must be unique nonempty strings")
        seen.add(cid)
        for field in ["allowed_stages", "eligible_lanes", "capability_keys", "trigger_signals",
                      "execution_profiles", "supersedes", "requires", "blocks_when", "composes_with"]:
            cap[field] = strings(cap.get(field, []), field)
        if not set(cap["allowed_stages"]) <= STAGES or not set(cap["eligible_lanes"]) <= LANES:
            raise ValueError("POLICY_INVALID: unsupported capability stage or Lane")
        if not isinstance(cap.get("skill_ref"), str) or not cap["skill_ref"]:
            raise ValueError("POLICY_INVALID: capability Skill ref required")
        cap["skill_ref"] = resolve_ref(cap["skill_ref"], Path(capability_path).parent)
        refs.append(cap["skill_ref"])
        for field in ["input_contract_ref", "output_contract_ref"]:
            if cap.get(field):
                cap[field] = resolve_ref(cap[field], Path(capability_path).parent)
                refs.append(cap[field])
        bound.append(cap)
    profiles = workflow.get("lane_profiles", {})
    validate_profiles(profiles, bound)
    required_contracts = strings(policy.get("required_contracts", []), "required_contracts")
    module.update({"available_capabilities": bound, "lane_profiles": profiles,
                   "required_contracts": required_contracts})
    if "orchestration" in workflow:
        module["orchestration"] = workflow["orchestration"]
        ordered_rows({}, module, bound, None, [], validate_only=True)
    for field in ["domain_execution_skill_ref", "execution_contract_ref", "planner_skill_ref"]:
        if field in workflow:
            module[field] = resolve_ref(workflow[field], Path(workflow_path).parent)
            refs.append(module[field])
    if "domain_execution_skill_ref" in module:
        module["workflow_skill_ref"] = module["domain_execution_skill_ref"]
    if completion_document.get("completion_skill_ref"):
        module["completion_skill_ref"] = resolve_ref(
            completion_document["completion_skill_ref"], Path(module["completion_predicate_ref"]).parent)
        refs.append(module["completion_skill_ref"])
    phase_refs = workflow.get("phase_refs", {})
    if not isinstance(phase_refs, dict):
        raise ValueError("POLICY_INVALID: phase_refs must be a mapping")
    for values in phase_refs.values():
        refs.extend(resolve_ref(ref, Path(workflow_path).parent) for ref in strings(values, "phase_refs"))
    return file_hashes(refs)


def policy_view(effective, domain_id, lane):
    """Scope capability and Lane policy to exactly one enabled v2 module."""
    if effective.get("config_version") != 2:
        return effective
    modules = effective.get("domains", {})
    if domain_id not in modules.get("enabled", []):
        raise ValueError("DOMAIN_MISMATCH: Domain is not enabled")
    module = modules.get("modules", {}).get(domain_id)
    if effective.get("status") != "READY" or not isinstance(module, dict):
        raise ValueError("POLICY_INVALID: effective runtime is not READY")
    mode = module.get("lane_policy", {}).get("mode")
    if ((mode == "not_applicable" and lane is not None)
            or (mode != "not_applicable" and lane not in LANES)
            or (mode == "fixed" and lane != module["lane_policy"].get("selected_lane"))):
        raise ValueError("LANE_MISMATCH: Lane violates Domain policy")
    manifest = effective.get("runtime_dependency_files") or {}
    if not manifest or digest(file_hashes(manifest)) != effective.get("runtime_dependency_sha256"):
        raise ValueError("CONFIG_DRIFT: runtime dependency bytes changed")
    view = dict(effective)
    view["available_capabilities"] = module.get("available_capabilities", [])
    view["lane"] = dict(effective.get("lane") or {}, profiles=module.get("lane_profiles", {}))
    view["domains"] = dict(modules, modules={domain_id: module})
    return view
