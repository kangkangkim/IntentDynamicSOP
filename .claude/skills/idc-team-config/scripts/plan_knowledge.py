#!/usr/bin/env python3

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml


class PsychString(str):
    """Emitted double-quoted, matching Ruby Psych which refuses plain style
    for values like absolute paths (``/...``) and dot-relative refs (``.x/y``)."""


def _psych_string_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style='"')


yaml.add_representer(PsychString, _psych_string_representer)


def psych_style(value):
    """Recursively wrap strings Psych would quote (leading `/` or `.`)."""
    if isinstance(value, str):
        return PsychString(value) if value.startswith(("/", ".")) else value
    if isinstance(value, list):
        return [psych_style(item) for item in value]
    if isinstance(value, dict):
        return {key: psych_style(item) for key, item in value.items()}
    return value


def safe_yaml_load(source):
    return yaml.safe_load(source)


def present(value):
    return value is not None and value != "" and value != [] and value != {}


def load_yaml(path):
    try:
        return safe_yaml_load(Path(path).resolve().read_text()) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


parser = argparse.ArgumentParser(
    description="Usage: plan_knowledge.py --effective PATH --demand PATH [--output PATH]"
)
parser.add_argument("--effective", metavar="PATH")
parser.add_argument("--demand", metavar="PATH")
parser.add_argument("--output", metavar="PATH")
args = parser.parse_args()

if not args.effective or not args.demand:
    print("ERROR: --effective and --demand are required", file=sys.stderr)
    sys.exit(1)

effective = load_yaml(args.effective)
demand_document = load_yaml(args.demand)
demand = demand_document.get("knowledge_demand") or demand_document

errors = []
if effective.get("generated") != True:
    errors.append("effective config is not generated runtime state")
execution_unit_ref = demand.get("execution_unit_ref")
domain = demand.get("selected_domain")
if not present(execution_unit_ref):
    errors.append("execution_unit_ref is required")

domains_runtime = effective.get("domains") or {}
enabled_domains = list(domains_runtime.get("enabled") or []) if isinstance(domains_runtime, dict) else []
domain_modules = domains_runtime.get("modules") or {} if isinstance(domains_runtime, dict) else {}
selected_module = None
module_backed_domain = False
if isinstance(domain_modules, dict) and domain_modules:
    if domain not in enabled_domains or not isinstance(domain_modules.get(domain), dict):
        errors.append(f"selected_domain is not enabled in effective runtime: {domain}")
    else:
        selected_module = domain_modules[domain]
        module_backed_domain = selected_module.get("source") == "domain-pack"
elif domain not in ("general", "d3a", "custom"):
    errors.append("selected_domain is not available in effective runtime")

selected_layer = demand.get("selected_layer")
selected_lane = demand.get("selected_lane")
selected_components = list(demand.get("selected_components") or [])
selected_test_domains = list(demand.get("selected_test_domains") or [])
if len(selected_components) != len(set(selected_components)):
    errors.append("selected_components must contain unique IDs")
if len(selected_test_domains) != len(set(selected_test_domains)):
    errors.append("selected_test_domains must contain unique IDs")

if isinstance(selected_module, dict) and selected_module.get("fixed_architecture"):
    if not present(selected_layer):
        errors.append("selected_layer is required for fixed-architecture Domain knowledge")
    if not selected_test_domains:
        errors.append("fixed-architecture Domain knowledge requires at least one selected_test_domain")
    if selected_components:
        errors.append("fixed-architecture Domain knowledge cannot select General components")
elif domain == "general":
    if present(selected_layer):
        errors.append("General knowledge cannot select a Layer")
    knowledge = effective.get("knowledge") or {}
    lane_docs = knowledge.get("lane_docs") or {}
    lane_docs_configured = any(
        list(refs) for refs in lane_docs.values() if isinstance(refs, list)
    )
    if lane_docs_configured and selected_lane not in ("fast", "lite", "complex"):
        errors.append("selected_lane is required for configured General lane knowledge")
elif domain == "custom":
    if not present(selected_layer):
        errors.append("selected_layer is required for Custom Domain knowledge")
    if selected_components:
        errors.append("Custom Domain knowledge cannot select General components")
elif module_backed_domain:
    if selected_components:
        errors.append("Domain Pack knowledge cannot select General components")
    lane_mode = ((selected_module.get("lane_policy") or {}).get("mode"))
    if lane_mode in ("dynamic", "fixed") and selected_lane not in (
        "fast",
        "lite",
        "complex",
    ):
        errors.append("selected_lane is required for lane-applicable Domain Pack knowledge")

catalog = (effective.get("knowledge_catalog") or {}).get(domain) or {}
knowledge = effective.get("knowledge") or {}
selected_entries = []
scope_entries = []
module_knowledge_root = None


def load_module_registry(registry_key, payload_key):
    registries = (selected_module or {}).get("registries") or {}
    registry_ref = registries.get(registry_key) if isinstance(registries, dict) else None
    if not present(registry_ref):
        errors.append(f"selected Domain module is missing registries.{registry_key}")
        return []
    try:
        document = safe_yaml_load(Path(str(registry_ref)).resolve().read_text()) or {}
    except (FileNotFoundError, OSError, yaml.YAMLError) as error:
        errors.append(f"selected Domain registry cannot be read: {error}")
        return []
    entries = document.get(payload_key) if isinstance(document, dict) else None
    if not isinstance(entries, list):
        errors.append(f"selected Domain registry must contain {payload_key}")
        return []
    return entries


if module_backed_domain:
    root_ref = (selected_module or {}).get("knowledge_root_ref")
    if not present(root_ref):
        errors.append("selected Domain module is missing knowledge_root_ref")
    else:
        module_knowledge_root = Path(str(root_ref)).resolve()
        if not module_knowledge_root.is_dir():
            errors.append("selected Domain knowledge_root_ref is not a directory")
    catalog = {
        "layers": (
            load_module_registry("coding_layers_ref", "coding_layers")
            if present(selected_layer)
            else []
        ),
        "test_domains": (
            load_module_registry("test_domains_ref", "test_domains")
            if selected_test_domains
            else []
        ),
        "components": [],
    }
    knowledge = {}


def select_entry(entries, entry_id, kind):
    entries = list(entries or [])
    entry = next(
        (e for e in entries if isinstance(e, dict) and e.get("id") == entry_id), None
    )
    if entry is None:
        errors.append(
            f"{kind} is not available in effective knowledge catalog: {entry_id}"
        )
        return
    ref = entry.get("knowledge_ref")
    if present(ref):
        if module_backed_domain:
            if module_knowledge_root is None:
                return
            candidate = Path(str(ref))
            if not candidate.is_absolute():
                candidate = (module_knowledge_root / candidate).resolve()
            else:
                candidate = candidate.resolve()
            try:
                candidate.relative_to(module_knowledge_root)
            except (ValueError, TypeError):
                errors.append(
                    f"{kind} knowledge_ref is outside selected Domain knowledge_root_ref: {entry_id}"
                )
                return
            if not candidate.is_file():
                errors.append(f"{kind} knowledge_ref does not exist: {entry_id}")
                return
            ref = str(candidate)
        selected_entries.append(
            {
                "kind": kind,
                "id": entry_id,
                "ref": ref,
                "source": "knowledge_catalog",
            }
        )
    else:
        errors.append(f"{kind} has no knowledge_ref: {entry_id}")


if present(selected_layer):
    layer_override = (knowledge.get("layer_docs") or {}).get(selected_layer)
    if present(layer_override):
        selected_entries.append(
            {
                "kind": "layer",
                "id": selected_layer,
                "ref": layer_override,
                "source": "knowledge.layer_docs",
            }
        )
    else:
        select_entry(catalog.get("layers"), selected_layer, "layer")

for cid in selected_components:
    select_entry(catalog.get("components"), cid, "component")
for tid in selected_test_domains:
    select_entry(catalog.get("test_domains"), tid, "test_domain")

if domain == "general" and selected_lane in ("fast", "lite", "complex"):
    lane_refs = list((knowledge.get("lane_docs") or {}).get(selected_lane) or [])
    for index, ref in enumerate(lane_refs):
        if present(ref):
            selected_entries.append(
                {
                    "kind": "lane",
                    "id": f"{selected_lane}-{index + 1}",
                    "ref": ref,
                    "source": f"knowledge.lane_docs.{selected_lane}",
                }
            )

for kind, (demand_key, knowledge_key) in {
    "architecture": ("include_architecture", "architecture_doc_ref"),
    "verification_mapping": (
        "include_verification_mapping",
        "verification_mapping_ref",
    ),
}.items():
    if demand.get(demand_key) == True:
        ref = knowledge.get(knowledge_key)
        if present(ref):
            selected_entries.append(
                {
                    "kind": kind,
                    "id": kind,
                    "ref": ref,
                    "source": f"knowledge.{knowledge_key}",
                }
            )
        else:
            errors.append(f"{knowledge_key} is required by knowledge demand")

if demand.get("include_feature_docs_scope") == True:
    feature_root = knowledge.get("feature_docs_root_ref")
    if present(feature_root):
        scope_entries.append(
            {
                "kind": "feature_docs_scope",
                "id": "feature_docs_root",
                "ref": feature_root,
                "source": "knowledge.feature_docs_root_ref",
            }
        )
    else:
        errors.append("feature_docs_root_ref is required by knowledge demand")

repo_context = knowledge.get("repo_context") or {}
repo_context_required = demand.get("repo_context_required") == True
if present(repo_context.get("provider_skill_ref")):
    provider_mode = "bound_skill"
elif repo_context.get("fallback") == "bounded_grep":
    provider_mode = "bounded_grep"
else:
    provider_mode = "none"

if repo_context_required and provider_mode == "none":
    errors.append(
        "repo context is required but no provider_skill_ref or bounded_grep fallback is available"
    )

body = {
    "status": "READY" if not errors else "NEEDS_KNOWLEDGE_MAPPING",
    "source_sha256": effective.get("source_sha256"),
    "execution_unit_ref": execution_unit_ref,
    "selected_domain": domain,
    "selected_lane": selected_lane,
    "selected_layer": selected_layer,
    "selected_components": selected_components,
    "selected_test_domains": selected_test_domains,
    "required_static_knowledge": selected_entries,
    "search_scopes": scope_entries,
    "repo_context": {
        "required": repo_context_required,
        "mode": provider_mode,
        "provider_skill_ref": repo_context.get("provider_skill_ref"),
        "policy_ref": repo_context.get("policy_ref"),
        "fallback": repo_context.get("fallback"),
    },
    "consumption_policy": {
        "all_required_static_refs_must_be_loaded": True,
        "unplanned_static_refs_forbidden": True,
        "search_scope_result_required": bool(scope_entries),
        "provider_result_required": repo_context_required,
    },
    "errors": errors,
}
if not errors:
    body["knowledge_plan_id"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

output = yaml.dump({"knowledge_load_plan": psych_style(body)}, allow_unicode=True)
if args.output:
    Path(args.output).resolve().write_text(output)
else:
    print(output, end="")

sys.exit(0 if not errors else 2)
