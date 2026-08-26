#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml


def safe_yaml_load(source):
    return yaml.safe_load(source)


def load_yaml(path):
    try:
        return safe_yaml_load(Path(path).resolve().read_text()) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def normalize_ref(ref):
    value = str(ref or "")
    if re.match(r'^[a-z][a-z0-9+.\-]*:', value, re.IGNORECASE):
        return value
    return str(Path(value).resolve())


parser = argparse.ArgumentParser(
    description="Usage: verify_knowledge_consumption.py --plan PATH --receipt PATH [--output PATH]"
)
parser.add_argument("--plan", metavar="PATH")
parser.add_argument("--receipt", metavar="PATH")
parser.add_argument("--output", metavar="PATH")
args = parser.parse_args()

if not args.plan or not args.receipt:
    print("ERROR: --plan and --receipt are required", file=sys.stderr)
    sys.exit(1)

plan = load_yaml(args.plan).get("knowledge_load_plan") or {}
receipt = load_yaml(args.receipt).get("knowledge_consumption_receipt") or {}
errors = []

if plan.get("status") != "READY":
    errors.append("knowledge plan must be READY")
plan_body = {k: v for k, v in plan.items() if k != "knowledge_plan_id"}
computed_plan_id = hashlib.sha256(
    json.dumps(plan_body, separators=(",", ":")).encode()
).hexdigest()
if plan.get("knowledge_plan_id") != computed_plan_id:
    errors.append("knowledge plan integrity check failed")
if receipt.get("knowledge_plan_id") != plan.get("knowledge_plan_id"):
    errors.append("knowledge_plan_id does not match")
if receipt.get("execution_unit_ref") != plan.get("execution_unit_ref"):
    errors.append("execution_unit_ref does not match")

required_refs = list(
    dict.fromkeys(
        normalize_ref(e.get("ref")) for e in (plan.get("required_static_knowledge") or [])
    )
)
for ref in required_refs:
    if not re.match(r'^[a-z][a-z0-9+.\-]*:', ref, re.IGNORECASE):
        if not Path(ref).is_file():
            errors.append(f"required local knowledge ref no longer exists: {ref}")

loaded_refs = [normalize_ref(r) for r in (receipt.get("loaded_static_refs") or [])]
missing_refs = [r for r in required_refs if r not in loaded_refs]
unplanned_refs = [r for r in loaded_refs if r not in required_refs]
if missing_refs:
    errors.append(f"required knowledge refs were not loaded: {', '.join(missing_refs)}")
if unplanned_refs:
    errors.append(f"unplanned knowledge refs were loaded: {', '.join(unplanned_refs)}")

search_scopes = list(plan.get("search_scopes") or [])
search_scope_result_refs = list(receipt.get("search_scope_result_refs") or [])
if search_scopes and not search_scope_result_refs:
    errors.append("search_scope_result_refs are required")

provider_result_refs = list(receipt.get("provider_result_refs") or [])
if (plan.get("repo_context") or {}).get("required") == True and not provider_result_refs:
    errors.append("provider_result_refs are required")

knowledge_summary_refs = list(receipt.get("knowledge_summary_refs") or [])
if required_refs and not knowledge_summary_refs:
    errors.append("loaded knowledge must be summarized with evidence refs")

result = {
    "knowledge_consumption_result": {
        "status": "VERIFIED" if not errors else "BLOCKED_KNOWLEDGE_CONSUMPTION",
        "knowledge_plan_id": plan.get("knowledge_plan_id"),
        "execution_unit_ref": plan.get("execution_unit_ref"),
        "loaded_static_refs": loaded_refs,
        "provider_result_refs": provider_result_refs,
        "search_scope_result_refs": search_scope_result_refs,
        "knowledge_summary_refs": knowledge_summary_refs,
        "errors": errors,
    }
}

output = yaml.dump(result, allow_unicode=True)
if args.output:
    Path(args.output).resolve().write_text(output)
else:
    print(output, end="")

sys.exit(0 if not errors else 3)
