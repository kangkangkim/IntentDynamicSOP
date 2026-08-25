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
if domain not in ("general", "d3a", "custom"):
    errors.append("selected_domain must be general, d3a, or custom")

selected_layer = demand.get("selected_layer")
selected_lane = demand.get("selected_lane")
selected_components = list(demand.get("selected_components") or [])
selected_test_domains = list(demand.get("selected_test_domains") or [])
if len(selected_components) != len(set(selected_components)):
    errors.append("selected_components must contain unique IDs")
if len(selected_test_domains) != len(set(selected_test_domains)):
    errors.append("selected_test_domains must contain unique IDs")

if domain == "d3a":
    if not present(selected_layer):
        errors.append("selected_layer is required for D3A knowledge")
    if not selected_test_domains:
        errors.append("D3A knowledge requires at least one selected_test_domain")
    if selected_components:
        errors.append("D3A knowledge cannot select General components")
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

catalog = (effective.get("knowledge_catalog") or {}).get(domain) or {}
knowledge = effective.get("knowledge") or {}
selected_entries = []
scope_entries = []


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
