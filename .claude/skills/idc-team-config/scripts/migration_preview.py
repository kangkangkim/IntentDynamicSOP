"""Deterministic, preview-only v1 to v2 team configuration migration."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[4]
RESOLVER = Path(__file__).with_name("resolve_team_config.py")
LANES = ("fast", "lite", "complex")
D3A_LAYERS = ("TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def yaml_text(value):
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)


CHILDREN = {
    "": {"config_version", "team", "domain", "general", "bindings", "adapter_extensions",
         "knowledge", "lane", "capability_selection", "self_optimization", "alignment"},
    "team": {"id", "repo_path"},
    "domain": {"enabled", "mode", "d3a", "custom"},
    "domain.d3a": {"dt_domains", "orchestration"},
    "domain.custom": {"id", "trigger_rules", "lane_policy", "coding_layers", "test_domains",
                      "required_contracts", "workflow_skill_ref", "planner_skill_ref",
                      "completion_skill_ref", "orchestration"},
    "domain.custom.lane_policy": {"mode", "selected_lane"},
    "general": {"components", "test_domains"},
    "knowledge": {"architecture_doc_ref", "feature_docs_root_ref", "layer_docs", "lane_docs",
                  "verification_mapping_ref", "repo_context"},
    "knowledge.lane_docs": set(LANES),
    "knowledge.repo_context": {"provider_skill_ref", "policy_ref", "fallback"},
    "lane": {"default", "profiles"},
    "capability_selection": {"mode", "lane_profiles", "d3a_profile",
                             "require_selected_and_skipped_reasons"},
    "capability_selection.d3a_profile": {"max_optional_skills"},
    "self_optimization": {"mode", "event_store_ref", "replay_cases_ref", "team_overlay_ref",
                          "promotion_requires_human_alignment", "auto_modify_core"},
    "alignment": {"bindings", "orchestration"},
}
ROW_KEYS = {"id", "knowledge_ref"}
STEP_KEYS = {"id", "stage", "skill_ids", "trigger_signals"}
PROFILE_KEYS = {"skills", "orchestration"}
SKILL_POLICY_KEYS = {"allow", "deny", "required"}
EXTENSION_KEYS = {"id", "execution_role", "capability_keys", "allowed_stages", "eligible_lanes",
                  "execution_profiles", "trigger_signals", "skill_ref", "input_contract_ref",
                  "output_contract_ref", "evidence_required", "requires", "blocks_when",
                  "composes_with", "supersedes", "may_override"}


def allowed_keys(path):
    normalized = re.sub(r"\[\d+\]", "[]", path)
    if normalized in CHILDREN:
        return CHILDREN[normalized]
    if re.fullmatch(r"(domain\.d3a\.dt_domains|domain\.custom\.(coding_layers|test_domains)|general\.(components|test_domains))\[\]", normalized):
        return ROW_KEYS
    if normalized.endswith(".orchestration"):
        return {"mode", "steps"}
    if normalized.endswith(".orchestration.steps[]"):
        return STEP_KEYS
    if path == "bindings" or path in {"knowledge.layer_docs", "alignment.bindings"}:
        return "*"
    if re.fullmatch(r"(bindings|alignment\.bindings)\.[^.]+", path):
        return {"skill_ref"}
    if path in {"lane.profiles", "capability_selection.lane_profiles"}:
        return "*"
    if re.fullmatch(r"lane\.profiles\.[^.]+", path):
        return PROFILE_KEYS
    if re.fullmatch(r"lane\.profiles\.[^.]+\.skills", path):
        return SKILL_POLICY_KEYS
    if re.fullmatch(r"capability_selection\.lane_profiles\.[^.]+", path):
        return {"max_optional_skills"}
    if normalized == "adapter_extensions[]":
        return EXTENSION_KEYS
    return None


def dispositions(source):
    rows, unsupported = [], []
    opaque = ("domain.custom.trigger_rules",)

    def visit(value, path, inherited=False):
        if path:
            status = "UNSUPPORTED" if inherited else "MAPPED"
            rows.append({"source_path": path, "target_paths": [], "status": status,
                         "reason": "unknown v1 field" if inherited else "preserved by deterministic mapping"})
            if inherited:
                unsupported.append(path)
        if any(path == item or path.startswith(item + "[") or path.startswith(item + ".")
               for item in opaque):
            return
        if isinstance(value, dict):
            permitted = allowed_keys(path)
            for key, child in value.items():
                child_path = str(key) if not path else path + "." + str(key)
                unknown = inherited or permitted is None or (permitted != "*" and key not in permitted)
                visit(child, child_path, unknown)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, "{}[{}]".format(path, index), inherited)

    visit(source, "")
    return rows, unsupported


def resolve(config_path, output_path):
    completed = subprocess.run(
        [sys.executable, str(RESOLVER), "--config", str(config_path), "--output", str(output_path)],
        cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, timeout=60,
    )
    if completed.returncode:
        return None, completed.stderr.strip()
    return yaml.safe_load(output_path.read_text(encoding="utf-8")), ""


def registry_rows(module, kind):
    direct = ("coding_layers", "components") if kind == "layers" else ("test_domains",)
    for key in direct:
        if key in module:
            return copy.deepcopy(module[key] or [])
    ref_key = "coding_layers_ref" if kind == "layers" else "test_domains_ref"
    document = yaml.safe_load(Path(module["registries"][ref_key]).read_text()) or {}
    keys = ("layers", "coding_layers", "components") if kind == "layers" else ("test_domains", "domains")
    return copy.deepcopy(next((document[key] for key in keys if key in document), []))


def add_asset(assets, path, document):
    content = yaml_text(document)
    assets.append({"path": path, "content": content, "sha256": sha(content.encode())})


def domain_assets(domain_id, legacy_key, module, effective, assets):
    prefix = "assets/{}/".format(domain_id)
    layers, tests = registry_rows(module, "layers"), registry_rows(module, "tests")
    add_asset(assets, prefix + "layers.yaml", {"layers": layers})
    add_asset(assets, prefix + "tests.yaml", {"test_domains": tests})
    extension_ids = {row.get("id") for row in effective.get("adapter_extensions") or []}
    capabilities = [copy.deepcopy(row) for row in effective.get("available_capabilities") or []
                    if row.get("id") not in extension_ids]
    if legacy_key == "d3a":
        lane_policy = {"mode": "not_applicable", "selected_lane": None}
        required = ["d3a_specification", "api_contract", "task_contract", "verification_contract"]
        execution_skill = ROOT / ".claude/skills/idc-d3a-coding/SKILL.md"
        profiles = {}
    elif legacy_key == "general":
        lane_policy = {"mode": "dynamic", "selected_lane": None}
        required = ["task_contract", "verification_contract"]
        execution_skill = ROOT / ".claude/skills/idc-general-coding/SKILL.md"
        profiles = copy.deepcopy(effective["lane"]["profiles"])
    else:
        lane_policy = copy.deepcopy(module["lane_policy"])
        required = copy.deepcopy(module.get("required_contracts") or [])
        execution_skill = module["workflow_skill_ref"]
        profiles = copy.deepcopy(effective["lane"]["profiles"])
    execution_profile = module.get("execution_profile") or (
        "lane_driven" if lane_policy["mode"] in {"dynamic", "fixed"} else "domain_pack_fixed_workflow")
    workflow = {"id": domain_id + "-migrated-workflow", "execution_profile": execution_profile,
                "domain_execution_skill_ref": str(execution_skill), "phase_refs": {},
                "lane_profiles": profiles}
    if module.get("planner_skill_ref"):
        workflow["planner_skill_ref"] = module["planner_skill_ref"]
    orchestration = module.get("orchestration") or {}
    if orchestration.get("mode") == "ordered":
        workflow["orchestration"] = orchestration
    add_asset(assets, prefix + "workflow.yaml", {"workflow_profile": workflow})
    add_asset(assets, prefix + "policy.yaml", {"capability_policy": {
        "id": domain_id + "-migrated-policy", "execution_profile": execution_profile,
        "lane_applicability": lane_policy["mode"], "required_contracts": required,
        "capabilities": capabilities,
    }})
    completion = {"completion_predicates": [], "completion_rule": {"operator": "all"}}
    if legacy_key == "d3a":
        completion["completion_predicates"] = [
            {"predicate_id": "required_dt_domains_green", "required": True,
             "expected_status": "PASS", "evidence_required": True},
            {"predicate_id": "tran_build_pass", "required": True,
             "expected_status": "PASS", "evidence_required": True},
        ]
    if module.get("completion_skill_ref"):
        completion["completion_skill_ref"] = module["completion_skill_ref"]
    add_asset(assets, prefix + "completion.yaml", completion)
    pack = {
        "id": domain_id, "trigger_rules": copy.deepcopy(module.get("trigger_rules") or
            [{"field": "selected_domain", "equals": domain_id}]),
        "lane_policy": lane_policy, "workflow_profile_ref": "workflow.yaml",
        "capability_policy_ref": "policy.yaml", "completion_predicate_ref": "completion.yaml",
        "registries": {"coding_layers_ref": "layers.yaml", "test_domains_ref": "tests.yaml"},
        "knowledge_root_ref": ".",
    }
    if legacy_key == "d3a":
        pack["fixed_architecture"] = {
            "lane_mode": "not_applicable",
            "coding_layer_ids": list(D3A_LAYERS),
            "default_test_domain_ids": ["TPRINT", "FW", "DPF"],
        }
    add_asset(assets, prefix + "pack.yaml", {"domain_pack": pack})
    definition = {"pack_ref": prefix + "pack.yaml"}
    if legacy_key == "d3a" and [row.get("id") for row in tests] != ["TPRINT", "FW", "DPF"]:
        definition["registries"] = {"test_domains_ref": prefix + "tests.yaml"}
    return definition


def source_dependencies(effective):
    paths = set()

    def visit(value, key=""):
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, child_key)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, str) and (key.endswith("_ref") or key in {"skill_ref", "knowledge_file"}):
            path = Path(value)
            if path.is_file():
                paths.add(path.resolve())
    visit(effective)
    manifest = {str(path): sha(path.read_bytes()) for path in sorted(paths)}
    return sha(canonical(manifest))


def behavior(effective):
    capability_keys = ("id", "capability_id", "capability_keys", "allowed_stages", "eligible_lanes",
                       "execution_profiles", "trigger_signals", "skill_ref", "requires", "blocks_when",
                       "composes_with", "supersedes", "evidence_required")
    list_keys = {"capability_keys", "allowed_stages", "eligible_lanes", "execution_profiles",
                 "trigger_signals", "requires", "blocks_when", "composes_with", "supersedes"}
    capabilities = sorted([{key: (row.get(key) or [] if key in list_keys else row.get(key))
                            for key in capability_keys}
                           for row in effective.get("available_capabilities") or []],
                          key=lambda row: json.dumps(row, sort_keys=True))
    return {key: effective.get(key) for key in ("bindings", "adapter_extensions", "alignment", "lane",
            "knowledge", "capability_selection", "self_optimization")} | {"capabilities": capabilities}


def parity(old, new, key_map):
    if behavior(old) != behavior(new):
        return False
    old_domains = old.get("domains") or {
        "enabled": list(key_map), "default": next(iter(key_map)),
        "modules": {next(iter(key_map)): old["domain"]},
    }
    if new["domains"]["enabled"] != list(key_map.values()) or new["domains"]["default"] != key_map[old_domains["default"]]:
        return False
    for old_key, new_key in key_map.items():
        left, right = old_domains["modules"][old_key], new["domains"]["modules"][new_key]
        if registry_rows(left, "layers") != registry_rows(right, "layers"):
            return False
        if registry_rows(left, "tests") != registry_rows(right, "tests"):
            return False
        if old_key == "custom":
            for field in ("trigger_rules", "lane_policy", "required_contracts", "workflow_skill_ref",
                          "planner_skill_ref", "completion_skill_ref"):
                if left.get(field) != right.get(field):
                    return False
    return True


def build_preview(config_path):
    source_bytes = config_path.read_bytes()
    try:
        source = yaml.safe_load(source_bytes) or {}
    except yaml.YAMLError as error:
        return {"migration_preview": {"status": "INVALID", "diagnostics": [str(error)]}}
    rows, unsupported = dispositions(source)
    with tempfile.TemporaryDirectory(prefix="idc-migration-validation-") as directory:
        temp = Path(directory)
        old, old_error = resolve(config_path, temp / "old.yaml")
        if old is None:
            return {"migration_preview": {"status": "INVALID", "diagnostics": [old_error]}}
        enabled = old.get("domains", {"enabled": [source["domain"]["mode"]]})["enabled"]
        default = old.get("domains", {"default": source["domain"]["mode"]})["default"]
        modules = old.get("domains", {"modules": {default: old["domain"]}})["modules"]
        key_map = {key: (modules[key]["id"] if key == "custom" else key) for key in enabled}
        assets, definitions = [], {}
        for key in enabled:
            definitions[key_map[key]] = domain_assets(key_map[key], key, modules[key], old, assets)
        candidate = {"config_version": 2, "team": old["team"],
                     "domains": {"enabled": list(key_map.values()), "default": key_map[default],
                                 "definitions": definitions}}
        for key in ("bindings", "adapter_extensions", "lane", "knowledge", "capability_selection",
                    "self_optimization"):
            candidate[key] = copy.deepcopy(old.get(key))
        if "alignment" in source:
            candidate["alignment"] = {key: copy.deepcopy(old["alignment"][key])
                                      for key in ("bindings", "orchestration")}
        assets.sort(key=lambda row: row["path"])
        bundle = temp / "bundle"
        for asset in assets:
            target = bundle / asset["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(asset["content"], encoding="utf-8")
        write_yaml = yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True)
        (bundle / "team-config.yaml").write_text(write_yaml, encoding="utf-8")
        new, new_error = resolve(bundle / "team-config.yaml", temp / "new.yaml")
        resolver_ok = new is not None
        parity_ok = resolver_ok and parity(old, new, key_map)
        dependency_sha = source_dependencies(old)
        bundle_sha = sha(canonical({"candidate_config": candidate, "assets": assets,
                                    "source_sha256": sha(source_bytes),
                                    "dependency_sha256": dependency_sha}))
        status = "READY" if not unsupported and resolver_ok and parity_ok else "BLOCKED"
        diagnostics = ([{"code": "UNSUPPORTED_FIELD", "path": path} for path in unsupported]
                       + ([] if resolver_ok else [{"code": "V2_RESOLVER_FAILED", "reason": new_error}])
                       + ([] if parity_ok or not resolver_ok else [{"code": "SEMANTIC_PARITY_FAILED"}]))
        return {"migration_preview": {
            "status": status, "source_version": 1, "target_version": 2,
            "source_sha256": sha(source_bytes), "dependency_sha256": dependency_sha,
            "bundle_sha256": bundle_sha, "source_config": source, "candidate_config": candidate,
            "assets": assets, "field_dispositions": rows,
            "validation": {"resolver": "PASS" if resolver_ok else "FAIL",
                           "semantic_parity": "PASS" if parity_ok and not unsupported else "FAIL"},
            "diagnostics": diagnostics,
        }}
