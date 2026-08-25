#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml


def safe_yaml_load(source):
    return yaml.safe_load(source)


def present(value):
    return value is not None and value != "" and value != [] and value != {}


parser = argparse.ArgumentParser(
    description="Usage: authorize_execution.py --request PATH [--output PATH]"
)
parser.add_argument("--request", metavar="PATH")
parser.add_argument("--output", metavar="PATH")
args = parser.parse_args()

if not args.request:
    print("ERROR: --request is required", file=sys.stderr)
    sys.exit(1)

request_path = Path(args.request).expanduser().resolve()
try:
    document = safe_yaml_load(request_path.read_text()) or {}
except (FileNotFoundError, yaml.YAMLError) as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

request = document.get("execution_authorization_request") or document

errors = []
if request.get("human_alignment_status") != "approved":
    errors.append("human_alignment_status must be approved")
if request.get("capability_selection_status") != "READY":
    errors.append("capability_selection_status must be READY")
if request.get("main_agent_role") != "planning_and_delegation_only":
    errors.append("main_agent_role must be planning_and_delegation_only")

plan_confirmation = request.get("technical_plan_confirmation")
plan_confirmation_errors = []
if isinstance(plan_confirmation, dict):
    if plan_confirmation.get("required") != True:
        plan_confirmation_errors.append(
            "technical_plan_confirmation.required must be true (framework floor)"
        )
    valid_trigger_reasons = [
        "d3a_fixed_workflow",
        "lane=fast",
        "lane=lite",
        "lane=complex",
    ]
    if str(plan_confirmation.get("trigger_reason", "")) not in valid_trigger_reasons:
        plan_confirmation_errors.append(
            "technical_plan_confirmation.trigger_reason must be d3a_fixed_workflow or lane=fast|lite|complex"
        )
    if plan_confirmation.get("status") == "confirmed":
        if not present(plan_confirmation.get("confirmation_ref")):
            plan_confirmation_errors.append(
                "technical_plan_confirmation.confirmation_ref is required when status is confirmed"
            )
        elif present(plan_confirmation.get("confirmation_ref")):
            plan_path = Path(str(plan_confirmation["confirmation_ref"])).resolve()
            if not plan_path.is_file():
                plan_confirmation_errors.append(
                    f"technical_plan_confirmation.confirmation_ref file does not exist: {plan_confirmation['confirmation_ref']}"
                )
    else:
        plan_confirmation_errors.append(
            "technical_plan_confirmation.status must be confirmed when required is true (framework floor)"
        )
else:
    plan_confirmation_errors.append(
        "technical_plan_confirmation is required (framework floor: d3a and all lanes)"
    )
errors.extend(plan_confirmation_errors)

for key in [
    "approved_alignment_ref",
    "execution_unit_ref",
    "context_packet_ref",
    "capability_selection_ref",
    "knowledge_load_plan_ref",
    "knowledge_plan_id",
    "domain_execution_skill_ref",
    "delegation_contract_ref",
]:
    if not present(request.get(key)):
        errors.append(f"{key} is required")
if request.get("knowledge_load_plan_status") != "READY":
    errors.append("knowledge_load_plan_status must be READY")
if not present(request.get("allowed_paths")):
    errors.append("allowed_paths must not be empty")
if not present(request.get("expected_outputs")):
    errors.append("expected_outputs must not be empty")

executor = request.get("executor") or {}
valid_executor_kinds = ["subagent", "agent_team", "official_dynamic_workflow"]
if executor.get("kind") not in valid_executor_kinds:
    errors.append(
        "executor.kind must be subagent, agent_team, or official_dynamic_workflow"
    )
if not present(executor.get("agent_id")):
    errors.append("executor.agent_id is required")
if executor.get("agent_id") == "main_agent" or executor.get("kind") == "main_agent":
    errors.append("main_agent cannot be execution owner")

domain_skill = str(request.get("domain_execution_skill_ref") or "")
selected_domain = request.get("selected_domain")
if selected_domain == "general":
    if "idc-general-coding" not in domain_skill:
        errors.append("general execution must load idc-general-coding")
elif selected_domain == "d3a":
    if "idc-d3a-coding" not in domain_skill:
        errors.append("d3a execution must load idc-d3a-coding")

if present(request.get("capability_selection_ref")):
    cap_sel_path = Path(str(request["capability_selection_ref"])).resolve()
    try:
        cap_doc = safe_yaml_load(cap_sel_path.read_text()) or {}
        cap_result = cap_doc.get("capability_selection_result") or {}
        if cap_result.get("status") != "READY":
            errors.append(
                f"capability selection status must be READY (got {cap_result.get('status')!r})"
            )
        if cap_result.get("execution_unit_ref") != request.get("execution_unit_ref"):
            errors.append(
                "capability selection execution_unit_ref does not match request"
            )
        if not any(True for _ in cap_result.get("selected") or []):
            errors.append("capability selection selected_skills must not be empty")
    except (FileNotFoundError, yaml.YAMLError) as e:
        errors.append(f"capability_selection_ref cannot be read: {e}")

harness_root = Path(__file__).resolve().parent.joinpath("../../..").resolve()
team_config_path = harness_root / "team-config.yaml"
if present(request.get("effective_config_ref")):
    effective_config_path = Path(str(request["effective_config_ref"])).resolve()
else:
    effective_config_path = harness_root / ".idc" / "effective-team-config.yaml"

if team_config_path.is_file() and effective_config_path.is_file():
    try:
        effective_doc = safe_yaml_load(effective_config_path.read_text()) or {}
        recorded_sha = str(effective_doc.get("source_sha256") or "")
        actual_sha = hashlib.sha256(team_config_path.read_bytes()).hexdigest()
        if recorded_sha != actual_sha:
            errors.append(
                f"BLOCKED_STALE_EFFECTIVE_CONFIG: team-config.yaml has changed since last prepare_runtime.py "
                f"(recorded={recorded_sha[:12]}… actual={actual_sha[:12]}…); "
                f"re-run prepare_runtime.py and verify status: READY before authorizing"
            )
    except (FileNotFoundError, yaml.YAMLError) as e:
        errors.append(f"effective config integrity check failed: {e}")
elif team_config_path.is_file() and not effective_config_path.is_file():
    errors.append(
        "BLOCKED_STALE_EFFECTIVE_CONFIG: .idc/effective-team-config.yaml does not exist; run prepare_runtime.py first"
    )

if present(request.get("knowledge_load_plan_ref")):
    knowledge_plan_path = Path(str(request["knowledge_load_plan_ref"])).resolve()
    try:
        knowledge_document = safe_yaml_load(knowledge_plan_path.read_text()) or {}
        knowledge_plan = knowledge_document.get("knowledge_load_plan") or {}
        if knowledge_plan.get("status") != "READY":
            errors.append("knowledge load plan must be READY")
        knowledge_body = {k: v for k, v in knowledge_plan.items() if k != "knowledge_plan_id"}
        computed_knowledge_plan_id = hashlib.sha256(
            json.dumps(knowledge_body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if knowledge_plan.get("knowledge_plan_id") != computed_knowledge_plan_id:
            errors.append("knowledge plan integrity check failed")
        if knowledge_plan.get("knowledge_plan_id") != request.get("knowledge_plan_id"):
            errors.append("knowledge plan ID does not match")
        if knowledge_plan.get("execution_unit_ref") != request.get("execution_unit_ref"):
            errors.append("knowledge plan execution unit does not match")
        if knowledge_plan.get("selected_domain") != request.get("selected_domain"):
            errors.append("knowledge plan domain does not match")
    except (FileNotFoundError, yaml.YAMLError) as e:
        errors.append(f"knowledge load plan cannot be read: {e}")

canonical = json.dumps(dict(sorted(request.items())), separators=(",", ":"))
authorization_id = hashlib.sha256(canonical.encode()).hexdigest() if not errors else None
if plan_confirmation_errors:
    status = "BLOCKED_PLAN_CONFIRMATION_REQUIRED"
elif not errors:
    status = "AUTHORIZED"
else:
    status = "BLOCKED_DELEGATION_REQUIRED"

result = {
    "execution_authorization_result": {
        "status": status,
        "authorization_id": authorization_id,
        "execution_unit_ref": request.get("execution_unit_ref") if not errors else None,
        "selected_domain": request.get("selected_domain") if not errors else None,
        "selected_lane": request.get("selected_lane") if not errors else None,
        "executor_kind": executor.get("kind") if not errors else None,
        "domain_execution_skill_ref": request.get("domain_execution_skill_ref") if not errors else None,
        "knowledge_load_plan_ref": request.get("knowledge_load_plan_ref") if not errors else None,
        "knowledge_plan_id": request.get("knowledge_plan_id") if not errors else None,
        "technical_plan_confirmation": plan_confirmation if not errors else None,
        "selected_atomic_skill_refs": list(request.get("selected_atomic_skill_refs") or []) if not errors else [],
        "allowed_paths": list(request.get("allowed_paths") or []) if not errors else [],
        "expected_outputs": list(request.get("expected_outputs") or []) if not errors else [],
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

sys.exit(0 if not errors else 3)
