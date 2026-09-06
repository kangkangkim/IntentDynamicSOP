#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml


TEAM_CONFIG_SCRIPTS = Path(__file__).resolve().parents[2] / "idc-team-config" / "scripts"
sys.path.insert(0, str(TEAM_CONFIG_SCRIPTS))
from domain_policy_runtime import policy_view
from runtime_integrity import IntegrityError, strict_graph, verify_graph


def safe_yaml_load(source):
    return yaml.safe_load(source)


def present(value):
    return value is not None and value != "" and value != [] and value != {}


def normalize_ref(value):
    text = str(value or "")
    if "://" in text:
        return text
    return str(Path(text).expanduser().resolve())


def load_yaml_document(path, label, errors):
    try:
        return safe_yaml_load(Path(path).resolve().read_text()) or {}
    except (FileNotFoundError, OSError, yaml.YAMLError) as error:
        errors.append(f"{label} cannot be read: {error}")
        return {}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(value, prefix=""):
    """Canonical mappings are recursively sorted; ordered lists stay ordered."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(prefix.encode() + payload).hexdigest()


def file_identity(ref):
    path = Path(str(ref)).expanduser().resolve()
    if not path.is_file():
        return None
    return {"ref": str(path), "sha256": sha256_file(path)}


def validate_host_control(request, graph, effective, cap_selection_ref, knowledge_plan_ref, errors):
    """Bind real-graph authorization to an external, host-selected record.

    The record's hashes are integrity identifiers, not signatures.  The host
    must choose a record location that the selected executor cannot write.
    """
    if "host_control" in request or "host_control_record" in request:
        errors.append("HOST_CONTROL_REQUEST_FORBIDDEN: request cannot self-authorize")
    if not present(args.host_control_record):
        errors.append("BLOCKED_HOST_CONTROL_REQUIRED: --host-control-record is required")
        return None
    control_path = Path(str(args.host_control_record)).expanduser().resolve()
    if not control_path.is_file():
        errors.append("BLOCKED_HOST_CONTROL_REQUIRED: host control record cannot be read")
        return None
    try:
        document = safe_yaml_load(control_path.read_text()) or {}
    except (OSError, yaml.YAMLError) as error:
        errors.append(f"HOST_CONTROL_INTEGRITY: control record cannot be parsed: {error}")
        return None
    record = document.get("host_control_record")
    if not isinstance(record, dict):
        errors.append("HOST_CONTROL_INTEGRITY: host_control_record must be a mapping")
        return None
    control_id, control_sha = record.get("control_id"), record.get("control_sha256")
    body = {key: value for key, value in record.items() if key not in {"control_id", "control_sha256"}}
    if control_id != canonical_sha256(body, "host-control-record:") or control_sha != canonical_sha256(body):
        errors.append("HOST_CONTROL_INTEGRITY: control_id or control_sha256 is invalid")
        return None

    def source_identity():
        source = file_identity(effective.get("source_ref"))
        if not source:
            return None
        return {**source, "runtime_dependency_sha256": effective.get("runtime_dependency_sha256")}

    def bound_file(ref):
        identity = file_identity(ref)
        return identity or {"ref": normalize_ref(ref), "sha256": None}

    expected = {
        "task_id": request.get("task_id"),
        "execution_unit_ref": request.get("execution_unit_ref"),
        "selected_domain": request.get("selected_domain"),
        "selected_lane": request.get("selected_lane"),
        "graph_sha256": graph.get("graph_sha256"),
        "effective_source": source_identity(),
        "capability_selection": bound_file(cap_selection_ref),
        "knowledge_load_plan": {
            **bound_file(knowledge_plan_ref), "knowledge_plan_id": request.get("knowledge_plan_id"),
        },
        "technical_plan_confirmation": bound_file(
            (request.get("technical_plan_confirmation") or {}).get("confirmation_ref")
        ),
        "approved_alignment": bound_file(request.get("approved_alignment_ref")),
        "delegation": bound_file(request.get("delegation_contract_ref")),
        "executor": request.get("executor"),
        "allowed_paths": list(request.get("allowed_paths") or []),
        "expected_outputs": list(request.get("expected_outputs") or []),
    }
    required = set(expected) | {"control_id", "control_sha256"}
    if set(record) != required:
        errors.append("HOST_CONTROL_INTEGRITY: control record fields are missing or unsupported")
        return None
    for field, expected_value in expected.items():
        actual_value = record.get(field)
        if field in {"effective_source", "capability_selection", "knowledge_load_plan",
                     "technical_plan_confirmation", "approved_alignment", "delegation"}:
            if not isinstance(actual_value, dict) or not isinstance(expected_value, dict):
                errors.append(f"HOST_CONTROL_INTEGRITY: {field} must bind ref and bytes")
                continue
            normalized = dict(actual_value)
            if "ref" in normalized:
                normalized["ref"] = normalize_ref(normalized["ref"])
            if normalized != expected_value:
                errors.append(f"HOST_CONTROL_INTEGRITY: {field} differs from actual input bytes")
        elif actual_value != expected_value:
            errors.append(f"HOST_CONTROL_INTEGRITY: {field} differs from authorization request")
    return control_id


def required_module_predicates(effective, selected_domain, errors):
    """Derive completion obligations from the enabled module, never the request."""
    modules = (effective.get("domains") or {}).get("modules") or {}
    module = modules.get(selected_domain)
    if not isinstance(module, dict):
        errors.append("PREDICATE_AUTHORITY_MISSING: selected module is unavailable")
        return []
    predicates = module.get("completion_predicates")
    if predicates is None:
        predicate_ref = module.get("completion_predicate_ref")
        if not present(predicate_ref):
            errors.append("PREDICATE_AUTHORITY_MISSING: completion_predicate_ref is required")
            return []
        document = load_yaml_document(predicate_ref, "completion predicate", errors)
        predicates = document.get("completion_predicates") or []
    if not isinstance(predicates, list):
        errors.append("PREDICATE_AUTHORITY_MISSING: completion predicates must be a list")
        return []
    required = []
    for predicate in predicates:
        predicate_id = predicate.get("predicate_id") if isinstance(predicate, dict) else None
        if isinstance(predicate, dict) and predicate.get("required") is True:
            if not isinstance(predicate_id, str) or not predicate_id or predicate_id in required:
                errors.append("PREDICATE_AUTHORITY_MISSING: required predicate ID is invalid")
                continue
            required.append(predicate_id)
    if not required:
        errors.append("PREDICATE_AUTHORITY_MISSING: module has no required predicates")
    return required


def verify_effective_source(effective, errors):
    """Check the source referred to by the effective artifact, not a harness guess."""
    source_ref = effective.get("source_ref")
    source_sha = effective.get("source_sha256")
    if not present(source_ref):
        if effective.get("config_version") == 2:
            errors.append("BLOCKED_STALE_EFFECTIVE_CONFIG: effective source_ref is required")
        return
    source_path = Path(str(source_ref)).expanduser().resolve()
    if not source_path.is_file():
        errors.append("BLOCKED_STALE_EFFECTIVE_CONFIG: effective source_ref cannot be read")
        return
    actual_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if not isinstance(source_sha, str) or source_sha != actual_sha:
        errors.append(
            "BLOCKED_STALE_EFFECTIVE_CONFIG: effective source_ref changed since runtime preparation"
        )


def graph_binding_required(request, effective):
    """Keep only pre-graph, incomplete legacy requests compatible.

    A v2 request with the schema-required task identity is a real authorization
    request.  It must carry a graph.  Old public fixtures that omit task_id
    remain readable until their callers are migrated.
    """
    return present(request.get("run_graph_ref")) or (
        effective.get("config_version") == 2 and present(request.get("task_id"))
    )


def validate_graph_binding(request, effective, cap_result, authorized_stage_skills, errors):
    graph_ref = request.get("run_graph_ref")
    required = graph_binding_required(request, effective)
    if not present(graph_ref):
        if required:
            errors.append("RUN_GRAPH_REQUIRED: real authorization requires run_graph_ref")
        return {}, []
    graph_path = Path(str(graph_ref)).expanduser().resolve()
    graph_document = load_yaml_document(graph_path, "run graph", errors)
    graph = graph_document.get("run_graph") or graph_document
    if not isinstance(graph, dict):
        errors.append("GRAPH_INVALID: run_graph must be a mapping")
        return {}, []
    strict = strict_graph(graph)
    try:
        if strict:
            verify_graph(graph)
    except IntegrityError as error:
        errors.append(str(error))
    if strict or effective.get("config_version") == 2:
        if graph.get("selected_domain") != request.get("selected_domain"):
            errors.append("GRAPH_AUTHORIZATION_MISMATCH: selected Domain differs from graph")
        if graph.get("selected_lane") != request.get("selected_lane"):
            errors.append("GRAPH_AUTHORIZATION_MISMATCH: selected Lane differs from graph")
        if graph.get("config_sha256") != effective.get("source_sha256"):
            errors.append("CONFIG_DRIFT: graph source identity differs from effective runtime")
        dependency_sha = effective.get("runtime_dependency_sha256")
        if not isinstance(dependency_sha, str) or not dependency_sha:
            errors.append("CONFIG_DRIFT: real graph requires runtime dependency identity")
        elif graph.get("runtime_dependency_sha256") != dependency_sha:
            errors.append("CONFIG_DRIFT: graph runtime dependency identity differs")
        selection_identity = cap_result.get("config_identity") or {}
        if selection_identity.get("runtime_dependency_sha256") != dependency_sha:
            errors.append("CONFIG_DRIFT: selection runtime dependency identity differs")
        try:
            policy_view(effective, request.get("selected_domain"), request.get("selected_lane"))
        except (ValueError, OSError, TypeError, KeyError) as error:
            errors.append(str(error))
        nodes = graph.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            errors.append("GRAPH_INVALID: real graph requires ordered nodes")
            nodes = []
        for selected in authorized_stage_skills:
            selected_identity = (
                selected.get("step_id"), selected.get("stage"),
                selected.get("capability_id"), normalize_ref(selected.get("skill_ref")),
            )
            matches = [node for node in nodes if isinstance(node, dict) and (
                node.get("step_id"), node.get("stage"), node.get("skill_id"),
                normalize_ref(node.get("skill_ref")),
            ) == selected_identity]
            if len(matches) != 1:
                errors.append("GRAPH_SELECTION_MISMATCH: selected Skill is not an authorized graph node")
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    return graph, nodes


parser = argparse.ArgumentParser(
    description="Usage: authorize_execution.py --request PATH [--output PATH]"
)
parser.add_argument("--request", metavar="PATH")
parser.add_argument("--output", metavar="PATH")
parser.add_argument("--host-control-record", metavar="PATH")
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

cap_result = {}
authorized_stage_skills = []
derived_atomic_skill_refs = []
cap_sel_path = None
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
        if present(cap_result.get("selected_domain")) and cap_result.get(
            "selected_domain"
        ) != request.get("selected_domain"):
            errors.append("capability selection selected_domain does not match request")
        if not any(True for _ in cap_result.get("selected") or []):
            errors.append("capability selection selected_skills must not be empty")
        selected_entries = list(cap_result.get("selected") or [])
        execution_orders = [item.get("execution_order") for item in selected_entries]
        if execution_orders != list(range(1, len(selected_entries) + 1)):
            errors.append("capability selection execution_order must be contiguous and deterministic")
        orchestration = cap_result.get("orchestration") or {}
        selected_stage_skills = [
            {
                "step_id": item.get("step_id"),
                "stage": item.get("stage") or cap_result.get("selected_stage"),
                "capability_id": item.get("capability_id"),
                "skill_ref": item.get("skill_ref"),
                "execution_order": item.get("execution_order"),
            }
            for item in selected_entries
        ]
        if orchestration.get("mode") == "ordered":
            execution_plan = list(orchestration.get("execution_plan") or [])
            stage_order = list(orchestration.get("stage_order") or [])
            expected_stage_order = list(dict.fromkeys(
                step.get("stage") for step in execution_plan
                if isinstance(step, dict) and step.get("stage")
            ))
            if not execution_plan or stage_order != expected_stage_order:
                errors.append(
                    "ordered capability selection stage_order must cover configured stages without gaps or reordering"
                )
            matched_step_ids = set(orchestration.get("matched_step_ids") or [])
            for item in selected_entries:
                if item.get("step_id") not in matched_step_ids:
                    errors.append(
                        f"ordered selected capability is not bound to a matched step: {item.get('capability_id')}"
                    )
            ordered_execution = list(cap_result.get("ordered_execution") or [])
            if ordered_execution != selected_stage_skills:
                errors.append("ordered_execution must exactly match selected capabilities and order")
            authorized_stage_skills = ordered_execution
        else:
            authorized_stage_skills = selected_stage_skills
        derived_atomic_skill_refs = [item.get("skill_ref") for item in authorized_stage_skills]
        if "selected_atomic_skill_refs" in request:
            reported_refs = list(request.get("selected_atomic_skill_refs") or [])
            if [normalize_ref(ref) for ref in reported_refs] != [normalize_ref(ref) for ref in derived_atomic_skill_refs]:
                errors.append(
                    "selected_atomic_skill_refs must exactly match capability selection artifact order"
                )
    except (FileNotFoundError, yaml.YAMLError) as e:
        errors.append(f"capability_selection_ref cannot be read: {e}")

harness_root = Path(__file__).resolve().parents[4]
team_config_path = harness_root / "team-config.yaml"
effective_config_explicit = present(request.get("effective_config_ref"))
if effective_config_explicit:
    effective_config_path = Path(str(request["effective_config_ref"])).resolve()
else:
    effective_config_path = harness_root / ".idc" / "effective-team-config.yaml"

effective_doc = {}
if effective_config_path.is_file():
    try:
        loaded_effective = safe_yaml_load(effective_config_path.read_text()) or {}
        effective_doc = loaded_effective.get("effective_runtime") or loaded_effective
        if not isinstance(effective_doc, dict):
            effective_doc = {}
            errors.append("effective_config_ref must contain a runtime mapping")
    except (OSError, yaml.YAMLError) as e:
        errors.append(f"effective config cannot be read: {e}")

if effective_config_path.is_file() and (
    effective_config_explicit or present(request.get("run_graph_ref"))
):
    verify_effective_source(effective_doc, errors)
    recorded_sha = str(effective_doc.get("source_sha256") or "")
    selection_identity = cap_result.get("config_identity") or {}
    if cap_result and recorded_sha and selection_identity.get("source_sha256") != recorded_sha:
        errors.append(
            "capability selection config identity does not match effective config source_sha256"
        )
elif effective_config_explicit and team_config_path.is_file():
    errors.append(
        "BLOCKED_STALE_EFFECTIVE_CONFIG: .idc/effective-team-config.yaml does not exist; run prepare_runtime.py first"
    )

# V2 outer execution is always owned by the selected module workflow profile.
# Config-version 1 remains a legacy adapter and retains its historical request
# contract without injecting a name-based rule into the v2 Core.
if effective_doc.get("config_version") == 2:
    domains_runtime = effective_doc.get("domains") or {}
    enabled_domains = (
        list(domains_runtime.get("enabled") or [])
        if isinstance(domains_runtime, dict)
        else []
    )
    domain_modules = (
        domains_runtime.get("modules") or {}
        if isinstance(domains_runtime, dict)
        else {}
    )
    selected_module = (
        domain_modules.get(selected_domain)
        if isinstance(domain_modules, dict)
        else None
    )
    if selected_domain not in enabled_domains or not isinstance(selected_module, dict):
            errors.append(f"DOMAIN_MODULE_NOT_ENABLED: selected_domain is not enabled: {selected_domain}")
    else:
        workflow_ref = selected_module.get("workflow_profile_ref")
        if not present(workflow_ref):
            errors.append("DOMAIN_EXECUTION_CONTRACT_INVALID: workflow_profile_ref is required")
        else:
            try:
                workflow_path = Path(str(workflow_ref)).resolve()
                workflow_document = safe_yaml_load(workflow_path.read_text()) or {}
                workflow_profile = workflow_document.get("workflow_profile") or workflow_document
                expected_domain_skill = workflow_profile.get(
                    "domain_execution_skill_ref"
                ) if isinstance(workflow_profile, dict) else None
                execution_contract_ref = workflow_profile.get(
                    "execution_contract_ref"
                ) if isinstance(workflow_profile, dict) else None
                if not present(expected_domain_skill) or not present(execution_contract_ref):
                    errors.append(
                        "DOMAIN_EXECUTION_CONTRACT_INVALID: workflow profile must declare "
                        "domain_execution_skill_ref and execution_contract_ref"
                    )
                else:
                    contract_path = Path(str(execution_contract_ref))
                    if not contract_path.is_absolute():
                        contract_path = workflow_path.parent / contract_path
                    expected_skill_path = Path(str(expected_domain_skill))
                    if not expected_skill_path.is_absolute() and "://" not in str(
                        expected_domain_skill
                    ):
                        expected_domain_skill = str(
                            (workflow_path.parent / expected_skill_path).resolve()
                        )
                    if not contract_path.resolve().is_file():
                        errors.append(
                            "DOMAIN_EXECUTION_CONTRACT_INVALID: execution_contract_ref does not exist"
                        )
                    if normalize_ref(domain_skill) != normalize_ref(expected_domain_skill):
                        errors.append(
                            "DOMAIN_EXECUTION_SKILL_MISMATCH: request Domain execution Skill "
                            "does not match selected module workflow profile"
                        )
            except (OSError, yaml.YAMLError) as e:
                errors.append(f"DOMAIN_EXECUTION_CONTRACT_INVALID: {e}")

# A current v2 request is bound to the compiler's immutable graph, not merely
# to the selected stage slice.  Legacy pre-graph public fixtures remain narrow
# compatibility cases (see graph_binding_required()).
bound_graph, authorized_graph_nodes = validate_graph_binding(
    request, effective_doc, cap_result, authorized_stage_skills, errors
)
required_predicate_ids = []
if graph_binding_required(request, effective_doc):
    required_predicate_ids = required_module_predicates(
        effective_doc, selected_domain, errors
    )
    if "required_predicate_ids" in request:
        reported_predicates = request.get("required_predicate_ids")
        if reported_predicates != required_predicate_ids:
            errors.append("PREDICATE_AUTHORITY_MISMATCH: request cannot change module predicates")
    if "proof_required" in request and request.get("proof_required") is not True:
        errors.append("PROOF_REQUIRED: request cannot disable required completion proof")

knowledge_plan_path = None
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

host_control_errors = []
host_control_id = None
if graph_binding_required(request, effective_doc):
    before = len(errors)
    host_control_id = validate_host_control(
        request, bound_graph, effective_doc, cap_sel_path, knowledge_plan_path, errors
    )
    host_control_errors = errors[before:]

authorization_payload = dict(request)
authorization_payload["selected_atomic_skill_refs"] = derived_atomic_skill_refs
authorization_payload["authorized_stage_skills"] = authorized_stage_skills
authorization_id = canonical_sha256(authorization_payload) if not errors else None
if plan_confirmation_errors:
    status = "BLOCKED_PLAN_CONFIRMATION_REQUIRED"
elif host_control_errors:
    status = ("BLOCKED_HOST_CONTROL_REQUIRED"
              if any(item.startswith("BLOCKED_HOST_CONTROL_REQUIRED") for item in host_control_errors)
              else "BLOCKED_HOST_CONTROL_INTEGRITY")
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
        "effective_config_ref": request.get("effective_config_ref") if not errors else None,
        "knowledge_load_plan_ref": request.get("knowledge_load_plan_ref") if not errors else None,
        "knowledge_plan_id": request.get("knowledge_plan_id") if not errors else None,
        "technical_plan_confirmation": plan_confirmation if not errors else None,
        "capability_selection_ref": request.get("capability_selection_ref") if not errors else None,
        "capability_config_identity": cap_result.get("config_identity") if not errors else None,
        "orchestration": cap_result.get("orchestration") if not errors else None,
        "authorized_stage_skills": authorized_stage_skills if not errors else [],
        "selected_atomic_skill_refs": derived_atomic_skill_refs if not errors else [],
        "run_graph_ref": request.get("run_graph_ref")
        if not errors and present(request.get("run_graph_ref")) else None,
        "graph_sha256": bound_graph.get("graph_sha256") if not errors else None,
        "runtime_dependency_sha256": effective_doc.get("runtime_dependency_sha256")
        if not errors and bound_graph else None,
        "authorized_graph_nodes": authorized_graph_nodes if not errors else [],
        "authorized_atomic_skill_refs": [node.get("skill_ref") for node in authorized_graph_nodes]
        if not errors else [],
        "required_predicate_ids": required_predicate_ids if not errors else [],
        "proof_required": True if not errors and graph_binding_required(request, effective_doc) else None,
        "host_control_id": host_control_id if not errors else None,
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
