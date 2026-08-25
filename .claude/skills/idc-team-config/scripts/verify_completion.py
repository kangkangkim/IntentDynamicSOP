#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import yaml


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
    description="Usage: verify_completion.py --request PATH [--output PATH]"
)
parser.add_argument("--request", metavar="PATH")
parser.add_argument("--output", metavar="PATH")
args = parser.parse_args()

if not args.request:
    print("ERROR: --request is required", file=sys.stderr)
    sys.exit(1)

document = load_yaml(args.request)
request = document.get("completion_verification_request") or document
errors = []

domain = request.get("selected_domain")
lane = request.get("selected_lane")
execution_unit_ref = request.get("execution_unit_ref")
if domain not in ("general", "d3a", "custom"):
    errors.append("selected_domain must be general, d3a, or custom")
if not present(execution_unit_ref):
    errors.append("execution_unit_ref is required")
if domain in ("general", "custom") and lane is not None:
    if lane not in ("fast", "lite", "complex"):
        errors.append("selected_lane must be fast, lite, or complex")
elif domain == "general":
    errors.append("General selected_lane must not be null")
elif domain == "d3a" and lane is not None:
    errors.append("D3A selected_lane must be null")

authorization_ref = request.get("authorization_result_ref")
authorization_document = load_yaml(authorization_ref) if present(authorization_ref) else {}
authorization = authorization_document.get("execution_authorization_result") or {}
if authorization.get("status") != "AUTHORIZED":
    errors.append("authorization result must be AUTHORIZED")

knowledge_ref = request.get("knowledge_consumption_result_ref")
knowledge_document = load_yaml(knowledge_ref) if present(knowledge_ref) else {}
knowledge = knowledge_document.get("knowledge_consumption_result") or {}
if knowledge.get("status") != "VERIFIED":
    errors.append("knowledge consumption result must be VERIFIED")

receipt = request.get("execution_receipt") or {}
for key in [
    "authorization_id",
    "dispatch_tool_call_ref",
    "executor_session_ref",
    "executor_kind",
    "loaded_domain_execution_skill_ref",
    "knowledge_plan_id",
    "knowledge_consumption_result_ref",
]:
    if not present(receipt.get(key)):
        errors.append(f"execution_receipt.{key} is required")

if receipt.get("authorization_id") != authorization.get("authorization_id"):
    errors.append("execution receipt authorization_id does not match")
if authorization.get("execution_unit_ref") != execution_unit_ref:
    errors.append("authorization execution_unit_ref does not match")
if authorization.get("selected_domain") != domain:
    errors.append("authorization selected_domain does not match")
if authorization.get("selected_lane") != lane:
    errors.append("authorization selected_lane does not match")
if receipt.get("executor_kind") != authorization.get("executor_kind"):
    errors.append("execution receipt executor_kind does not match authorization")
if receipt.get("loaded_domain_execution_skill_ref") != authorization.get("domain_execution_skill_ref"):
    errors.append("execution receipt Domain Skill does not match authorization")
if list(receipt.get("executed_atomic_skill_refs") or []) != list(authorization.get("selected_atomic_skill_refs") or []):
    errors.append("execution receipt atomic Skills do not match authorization")
if receipt.get("knowledge_plan_id") != authorization.get("knowledge_plan_id"):
    errors.append("execution receipt knowledge_plan_id does not match authorization")
if knowledge.get("knowledge_plan_id") != receipt.get("knowledge_plan_id"):
    errors.append("knowledge result knowledge_plan_id does not match execution receipt")
if knowledge.get("execution_unit_ref") != execution_unit_ref:
    errors.append("knowledge result execution_unit_ref does not match")

receipt_knowledge_ref = str(Path(str(receipt.get("knowledge_consumption_result_ref") or "")).resolve())
request_knowledge_ref = str(Path(str(request.get("knowledge_consumption_result_ref") or "")).resolve())
if receipt_knowledge_ref != request_knowledge_ref:
    errors.append("execution receipt knowledge consumption result ref does not match")
if not present(receipt.get("changed_paths")):
    errors.append("execution_receipt.changed_paths must not be empty")
if not present(receipt.get("evidence_refs")):
    errors.append("execution_receipt.evidence_refs must not be empty")

allowed_paths = [str(p).rstrip("/") for p in (authorization.get("allowed_paths") or [])]
for changed_path in (receipt.get("changed_paths") or []):
    changed = str(changed_path)
    covered = any(
        changed == allowed or changed.startswith(allowed + "/")
        for allowed in allowed_paths
    )
    if not covered:
        errors.append(f"changed path is outside authorization: {changed_path}")

loaded_domain_skill = str(receipt.get("loaded_domain_execution_skill_ref") or "")
if domain == "general":
    if "idc-general-coding" not in loaded_domain_skill:
        errors.append("general completion must load idc-general-coding")
elif domain == "d3a":
    if "idc-d3a-coding" not in loaded_domain_skill:
        errors.append("d3a completion must load idc-d3a-coding")

evidence = request.get("evidence") or {}
if domain == "d3a":
    required_evidence = [
        "d3a_specification_ref",
        "api_contract_ref",
        "completion_summary_ref",
    ]
elif domain == "custom" and lane is None:
    required_evidence = ["custom_completion_evidence_refs", "completion_summary_ref"]
elif lane == "fast":
    required_evidence = [
        "task_summary_ref",
        "acceptance_criteria_ref",
        "changed_files_review_ref",
        "verification_evidence_refs",
        "completion_summary_ref",
    ]
elif lane == "lite":
    required_evidence = [
        "task_contract_ref",
        "acceptance_criteria_ref",
        "focused_plan_ref",
        "relevant_context_refs",
        "verification_evidence_refs",
        "completion_summary_ref",
    ]
else:
    required_evidence = [
        "task_contract_ref",
        "detailed_plan_ref",
        "evidence_plan_ref",
        "verification_evidence_refs",
        "audit_or_review_ref",
        "completion_summary_ref",
    ]

for key in required_evidence:
    if not present(evidence.get(key)):
        label = "d3a" if domain == "d3a" else lane
        errors.append(f"evidence.{key} is required for {label} completion")

if domain in ("general", "custom") and request.get("test_based_verification") == True and lane is not None and lane != "fast":
    coverage_present = present(evidence.get("coverage_evidence_ref"))
    exemption = evidence.get("coverage_exemption") or {}
    exemption_present = present(exemption.get("reason"))
    if not coverage_present and not exemption_present:
        errors.append("coverage evidence or a reasoned exemption is required")

if domain == "d3a":
    d3a = request.get("d3a") or {}
    required_domains = list(d3a.get("required_dt_domains") or [])
    if not required_domains:
        errors.append("d3a.required_dt_domains must not be empty")
    if len(required_domains) != len(set(required_domains)):
        errors.append("d3a.required_dt_domains must contain unique IDs")
    red = d3a.get("red_evidence_by_domain") or {}
    green = d3a.get("green_evidence_by_domain") or {}
    for dt_domain in required_domains:
        if not present(red.get(dt_domain)):
            errors.append(f"missing RED evidence for DT domain {dt_domain}")
        if not present(green.get(dt_domain)):
            errors.append(f"missing GREEN evidence for DT domain {dt_domain}")
    if d3a.get("tran_build_status") != "PASS":
        errors.append("d3a.tran_build_status must be PASS")
    if not present(d3a.get("tran_build_evidence_ref")):
        errors.append("d3a.tran_build_evidence_ref is required")

result = {
    "completion_verification_result": {
        "status": "DONE" if not errors else "BLOCKED_COMPLETION",
        "selected_domain": domain,
        "selected_lane": lane,
        "execution_unit_ref": execution_unit_ref,
        "authorization_id": receipt.get("authorization_id") if not errors else None,
        "knowledge_plan_id": receipt.get("knowledge_plan_id") if not errors else None,
        "errors": errors,
    }
}

output = yaml.dump(result, allow_unicode=True)
if args.output:
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
else:
    print(output, end="")

sys.exit(0 if not errors else 4)
