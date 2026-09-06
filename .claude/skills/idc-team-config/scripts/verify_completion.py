#!/usr/bin/env python3

import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

from runtime_integrity import (IntegrityError, strict_graph, verify_completion_integrity)
from run_event_ledger import process as replay_ledger
from dispatch_state import DispatchStateError, export_snapshot

LEGACY_FIXED_DOMAIN_ID = "d3a"


def legacy_fixed_domain(domain_id):
    """Read V1 compatibility only; V2 consumes the selected Pack module."""
    return domain_id == LEGACY_FIXED_DOMAIN_ID


def safe_yaml_load(source):
    return yaml.safe_load(source)


def present(value):
    return value is not None and value != "" and value != [] and value != {}


def normalized_ref(value):
    text = str(value or "")
    if "://" in text:
        return text
    return str(Path(text).expanduser().resolve())


def load_yaml(path):
    try:
        return safe_yaml_load(Path(path).resolve().read_text()) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def mapping_payload(document, wrapper_key):
    if not isinstance(document, dict):
        return {}
    payload = document.get(wrapper_key) or document
    return payload if isinstance(payload, dict) else {}


parser = argparse.ArgumentParser(
    description="Usage: verify_completion.py --request PATH [--output PATH]"
)
parser.add_argument("--request", metavar="PATH")
parser.add_argument("--output", metavar="PATH")
parser.add_argument("--host-records", metavar="PATH", help="independent host adapter records")
parser.add_argument("--dispatch-state", metavar="PATH", help="host-owned atomic dispatch state")
args = parser.parse_args()

if not args.request:
    print("ERROR: --request is required", file=sys.stderr)
    sys.exit(1)

errors = []
document = load_yaml(args.request)
request = mapping_payload(document, "completion_verification_request")
if not request:
    errors.append("INVALID_REQUEST: completion request must be a mapping")

domain = request.get("selected_domain")
lane = request.get("selected_lane")
execution_unit_ref = request.get("execution_unit_ref")
if not isinstance(domain, str) or not domain.strip():
    errors.append("selected_domain is required")
if not present(execution_unit_ref):
    errors.append("execution_unit_ref is required")
if lane is not None:
    if lane not in ("fast", "lite", "complex"):
        errors.append("selected_lane must be fast, lite, or complex")

authorization_ref = request.get("authorization_result_ref")
authorization_document = load_yaml(authorization_ref) if present(authorization_ref) else {}
authorization = mapping_payload(authorization_document, "execution_authorization_result")
if authorization.get("status") != "AUTHORIZED":
    errors.append("authorization result must be AUTHORIZED")

effective_document = load_yaml(authorization.get("effective_config_ref")) if present(
    authorization.get("effective_config_ref")
) else {}
effective = mapping_payload(effective_document, "effective_runtime")
domains_runtime = effective.get("domains") or {}
domain_modules = domains_runtime.get("modules") if isinstance(domains_runtime, dict) else {}
selected_module = domain_modules.get(domain) if isinstance(domain_modules, dict) else None
is_v2_module = effective.get("config_version") == 2 and isinstance(selected_module, dict)
fixed_architecture = selected_module.get("fixed_architecture") if is_v2_module else None
lane_policy = selected_module.get("lane_policy") if is_v2_module else {}
if is_v2_module:
    lane_mode = (lane_policy or {}).get("mode")
    if lane_mode == "not_applicable" and lane is not None:
        errors.append("selected_lane must be null for a lane-inapplicable Domain Pack")
    elif lane_mode in ("dynamic", "fixed") and lane not in ("fast", "lite", "complex"):
        errors.append("selected_lane is required for a lane-applicable Domain Pack")
    elif lane_mode == "fixed" and lane != (lane_policy or {}).get("selected_lane"):
        errors.append("selected_lane does not match fixed Domain Pack lane policy")
legacy_fixed = not is_v2_module and legacy_fixed_domain(domain)

# New authorization results retain the effective runtime reference. Validate
# arbitrary Domain IDs against it when available; legacy authorized artifacts
# remain readable and are still bound by authorization/domain/receipt equality.
if domain not in ("general", "d3a", "custom") and present(
    authorization.get("effective_config_ref")
):
    effective_document = load_yaml(authorization.get("effective_config_ref"))
    effective = mapping_payload(effective_document, "effective_runtime")
    domains_runtime = effective.get("domains") or {}
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
    if domain not in enabled_domains or not isinstance(domain_modules.get(domain), dict):
        errors.append(
            f"DOMAIN_MODULE_NOT_ENABLED: selected_domain is not enabled: {domain}"
        )

selection_ref = authorization.get("capability_selection_ref")
selection_document = load_yaml(selection_ref) if present(selection_ref) else {}
selection = mapping_payload(selection_document, "capability_selection_result")
if selection.get("status") != "READY":
    errors.append("authorized capability selection must remain READY")
if selection.get("execution_unit_ref") != execution_unit_ref:
    errors.append("capability selection execution_unit_ref does not match")
if present(selection.get("selected_domain")) and selection.get("selected_domain") != domain:
    errors.append("capability selection selected_domain does not match")
if selection.get("config_identity") != authorization.get("capability_config_identity"):
    errors.append("capability selection config identity changed after authorization")

selected_stage_skills = [
    {
        "step_id": item.get("step_id"),
        "stage": item.get("stage") or selection.get("selected_stage"),
        "capability_id": item.get("capability_id"),
        "skill_ref": item.get("skill_ref"),
        "execution_order": item.get("execution_order"),
    }
    for item in (selection.get("selected") or [])
    if isinstance(item, dict)
]
selection_orchestration = selection.get("orchestration") or {}
if not isinstance(selection_orchestration, dict):
    selection_orchestration = {}
if selection_orchestration.get("mode") == "ordered":
    selection_stage_skills = list(selection.get("ordered_execution") or [])
else:
    selection_stage_skills = selected_stage_skills
if selection_stage_skills != list(authorization.get("authorized_stage_skills") or []):
    errors.append("capability selection skills changed after authorization")

knowledge_ref = request.get("knowledge_consumption_result_ref")
knowledge_document = load_yaml(knowledge_ref) if present(knowledge_ref) else {}
knowledge = mapping_payload(knowledge_document, "knowledge_consumption_result")
if knowledge.get("status") != "VERIFIED":
    errors.append("knowledge consumption result must be VERIFIED")

receipt = request.get("execution_receipt") or {}
if not isinstance(receipt, dict):
    errors.append("INVALID_RECEIPT: execution_receipt must be a mapping")
    receipt = {}
receipt_integrity_errors = []


def add_receipt_error(message, code=None):
    diagnostic = f"{code}: {message}" if code else message
    errors.append(diagnostic)
    receipt_integrity_errors.append(diagnostic)


request_graph_ref = request.get("run_graph_ref")
authorized_graph_ref = authorization.get("run_graph_ref")
graph_contract_active = present(request_graph_ref) or present(authorized_graph_ref)
ledger_ref = request.get("event_ledger_result_ref")
dispatch_snapshot = {}
if args.dispatch_state:
    try:
        dispatch_snapshot = export_snapshot(args.dispatch_state)
    except (DispatchStateError, OSError, ValueError) as exception:
        errors.append(f"DISPATCH_STATE_INVALID: {exception}")
ledger_contract_active = present(ledger_ref) or bool(args.dispatch_state)
predicate_contract_active = "predicate_results" in request or present(
    request.get("required_predicate_ids")
)
proof_contract_active = (
    graph_contract_active or ledger_contract_active or predicate_contract_active
)
graph_match = "PASS"
order_match = "PASS"
run_graph = {}
expected_node_ids = []
executed_nodes = []
if graph_contract_active:
    if not present(request_graph_ref) or not present(authorized_graph_ref):
        errors.append("run graph ref must be present in request and authorization")
        graph_match = "FAIL"
        order_match = "FAIL"
        run_graph = {}
    elif normalized_ref(request_graph_ref) != normalized_ref(authorized_graph_ref):
        errors.append("request run_graph_ref does not match authorization")
        graph_match = "FAIL"
        order_match = "FAIL"
        run_graph = {}
    else:
        graph_document = load_yaml(request_graph_ref)
        if isinstance(graph_document, dict):
            run_graph = graph_document.get("run_graph") or {}
        if not isinstance(run_graph, dict):
            errors.append("run graph payload must be a mapping")
            graph_match = "FAIL"
            run_graph = {}

    expected_nodes = list(run_graph.get("nodes") or [])
    executed_nodes = list(receipt.get("executed_nodes") or [])
    expected_node_ids = [
        node.get("node_id") if isinstance(node, dict) else node
        for node in expected_nodes
    ]
    executed_node_ids = [
        node.get("node_id") if isinstance(node, dict) else node
        for node in executed_nodes
    ]

    if run_graph.get("status") != "READY":
        errors.append("run graph must be READY")
        graph_match = "FAIL"
    if present(run_graph.get("selected_domain")) and run_graph.get("selected_domain") != domain:
        errors.append("CONFIG_DRIFT: run graph selected_domain does not match request")
        graph_match = "FAIL"
    graph_sha256 = run_graph.get("graph_sha256")
    if not present(graph_sha256):
        errors.append("CONFIG_DRIFT: run graph graph_sha256 is required")
        graph_match = "FAIL"
    elif graph_sha256 != authorization.get("graph_sha256"):
        errors.append("CONFIG_DRIFT: run graph identity does not match authorization")
        graph_match = "FAIL"
    if graph_sha256 != receipt.get("graph_sha256"):
        add_receipt_error(
            "run graph identity does not match execution receipt",
            "CONFIG_DRIFT",
        )
        graph_match = "FAIL"
    graph_config_sha256 = run_graph.get("config_sha256")
    authorized_config_identity = authorization.get("capability_config_identity") or {}
    if not isinstance(authorized_config_identity, dict):
        authorized_config_identity = {}
    authorized_config_sha256 = authorized_config_identity.get("source_sha256")
    if ledger_contract_active and (
        not present(graph_config_sha256) or not present(authorized_config_sha256)
    ):
        errors.append("CONFIG_DRIFT: graph and authorization config identity are required")
        graph_match = "FAIL"
    elif (
        present(graph_config_sha256)
        and present(authorized_config_sha256)
        and graph_config_sha256 != authorized_config_sha256
    ):
        errors.append("CONFIG_DRIFT: graph config identity does not match authorization")
        graph_match = "FAIL"
    receipt_config_sha256 = receipt.get("config_sha256")
    if (
        present(receipt_config_sha256)
        and receipt_config_sha256 != graph_config_sha256
    ):
        add_receipt_error(
            "execution receipt config identity does not match run graph",
            "CONFIG_DRIFT",
        )
        graph_match = "FAIL"
    expected_ids_valid = bool(expected_node_ids) and all(
        isinstance(node_id, str) and present(node_id) for node_id in expected_node_ids
    )
    executed_ids_valid = bool(executed_node_ids) and all(
        isinstance(node_id, str) and present(node_id) for node_id in executed_node_ids
    )
    if not expected_ids_valid:
        errors.append("run graph nodes must contain node_id")
        graph_match = "FAIL"
    if not executed_ids_valid:
        add_receipt_error("execution receipt executed_nodes must contain node_id")
        graph_match = "FAIL"
        order_match = "FAIL"
    elif not expected_ids_valid or Counter(executed_node_ids) != Counter(expected_node_ids):
        add_receipt_error("execution receipt nodes do not exactly match run graph nodes")
        graph_match = "FAIL"
        order_match = "FAIL"
    elif executed_node_ids != expected_node_ids:
        add_receipt_error("execution receipt node order does not match run graph order")
        order_match = "FAIL"

    for index, executed_node in enumerate(executed_nodes):
        if not isinstance(executed_node, dict):
            continue
        for attestation_key in ["dispatch_tool_call_ref", "executor_session_ref"]:
            attestation = (
                executed_node.get(attestation_key)
                if attestation_key in executed_node
                else receipt.get(attestation_key)
            )
            if not present(attestation):
                add_receipt_error(
                    "execution receipt node {} {} is required".format(
                        index + 1, attestation_key
                    )
                )

ledger = {}
if ledger_contract_active:
    if dispatch_snapshot:
        ledger = dispatch_snapshot.get("run_event_ledger_result") or {}
        if dispatch_snapshot.get("status") != "COMPLETE":
            errors.append("DISPATCH_STATE_INCOMPLETE: every graph node must succeed")
        if (dispatch_snapshot.get("authorization_id") != authorization.get("authorization_id")
                or dispatch_snapshot.get("graph_sha256") != run_graph.get("graph_sha256")):
            add_receipt_error("protected state identity differs", "DISPATCH_STATE_MISMATCH")
        tickets = dispatch_snapshot.get("tickets") or {}
        dispatched_events = {
            row.get("node_id"): row for row in dispatch_snapshot.get("events") or []
            if isinstance(row, dict) and row.get("event_type") == "NODE_DISPATCHED"
        }
        succeeded_events = {
            row.get("node_id"): row for row in dispatch_snapshot.get("events") or []
            if isinstance(row, dict) and row.get("event_type") == "NODE_SUCCEEDED"
        }
        for node_id in expected_node_ids:
            ticket, event = tickets.get(node_id) or {}, dispatched_events.get(node_id) or {}
            succeeded = succeeded_events.get(node_id) or {}
            receipt_node = next((row for row in executed_nodes
                                 if isinstance(row, dict) and row.get("node_id") == node_id), {})
            dispatch_ref = receipt_node.get("dispatch_tool_call_ref",
                                            receipt.get("dispatch_tool_call_ref"))
            session_ref = receipt_node.get("executor_session_ref",
                                           receipt.get("executor_session_ref"))
            if (ticket.get("authorization_id") != authorization.get("authorization_id")
                    or ticket.get("graph_sha256") != run_graph.get("graph_sha256")
                    or ticket.get("node_id") != node_id
                    or not ticket.get("predecessor_state_sha256")
                    or not ticket.get("idempotency_key")
                    or ticket.get("dispatch_tool_call_ref") != dispatch_ref
                    or ticket.get("executor_session_ref") != session_ref
                    or event.get("ticket_id") != ticket.get("ticket_id")
                    or event.get("dispatch_tool_call_ref") != dispatch_ref
                    or event.get("executor_session_ref") != session_ref
                    or succeeded.get("ticket_id") != ticket.get("ticket_id")
                    or succeeded.get("dispatch_tool_call_ref") != dispatch_ref
                    or succeeded.get("executor_session_ref") != session_ref):
                add_receipt_error("ticket/event/receipt binding differs", "DISPATCH_TICKET_MISMATCH")
    else:
        ledger_document = load_yaml(ledger_ref) if present(ledger_ref) else {}
        if isinstance(ledger_document, dict):
            ledger = mapping_payload(ledger_document, "run_event_ledger_result")
    if not isinstance(ledger, dict):
        errors.append("LEDGER_INVALID: event ledger result must be a mapping")
        ledger = {}
    if not graph_contract_active:
        errors.append("LEDGER_INVALID: event ledger requires an authorized run graph")
        graph_match = "FAIL"
    if ledger.get("status") != "COMPLETE":
        errors.append("LEDGER_INCOMPLETE: event ledger status must be COMPLETE")
    if ledger.get("graph_sha256") != run_graph.get("graph_sha256"):
        add_receipt_error(
            "event ledger graph identity does not match run graph",
            "CONFIG_DRIFT",
        )
        graph_match = "FAIL"
    if ledger.get("authorization_id") != authorization.get("authorization_id"):
        add_receipt_error(
            "event ledger authorization_id does not match authorization",
            "AUTHORIZATION_DRIFT",
        )
    ledger_config_sha256 = ledger.get("config_sha256")
    if (
        present(ledger_config_sha256)
        and ledger_config_sha256 != run_graph.get("config_sha256")
    ):
        add_receipt_error(
            "event ledger config identity does not match run graph",
            "CONFIG_DRIFT",
        )
        graph_match = "FAIL"
    if present(receipt.get("run_id")) and receipt.get("run_id") != ledger.get("run_id"):
        add_receipt_error("execution receipt run_id does not match event ledger")

    ledger_state = ledger.get("state") or {}
    ledger_nodes = ledger_state.get("nodes") if isinstance(ledger_state, dict) else []
    ledger_node_ids = [
        node.get("node_id") if isinstance(node, dict) else None
        for node in (ledger_nodes or [])
    ]
    ledger_nodes_succeeded = bool(ledger_nodes) and all(
        isinstance(node, dict) and node.get("status") == "SUCCEEDED"
        for node in ledger_nodes
    )
    if (
        ledger_node_ids != expected_node_ids
        or not ledger_nodes_succeeded
        or ledger_state.get("current_node_id") is not None
    ):
        errors.append(
            "LEDGER_INCOMPLETE: ledger state must contain every graph node in SUCCEEDED order"
        )
    ledger_hash = ledger.get("ledger_hash")
    ledger_proof = ledger.get("proof") or {}
    ledger_events = ledger.get("events") or []
    if (
        not present(ledger_hash)
        or not isinstance(ledger_proof, dict)
        or ledger_proof.get("ledger_hash") != ledger_hash
        or ledger_proof.get("event_count") != ledger.get("applied_event_count")
        or ledger.get("applied_event_count") != len(ledger_events)
    ):
        errors.append("LEDGER_INVALID: event ledger proof is incomplete or inconsistent")

strict_integrity = (
    (graph_contract_active and strict_graph(run_graph, authorization.get("graph_sha256")))
    or authorization.get("graph_sha256") not in (None, "placeholder-graph-sha256")
    or args.host_records is not None
)
if strict_integrity:
    host_records = dispatch_snapshot.get("host_execution_records") if dispatch_snapshot else None
    if not host_records and args.host_records:
        host_records = mapping_payload(load_yaml(args.host_records), "host_execution_records")
    if not args.dispatch_state and not args.host_records:
        add_receipt_error(
            "protected host attestation dispatch state is required; request fields cannot self-prove",
            "DISPATCH_STATE_REQUIRED",
        )
    try:
        verify_completion_integrity(run_graph, authorization, request, receipt,
                                    ledger, host_records, replay_ledger)
    except (IntegrityError, TypeError, ValueError, KeyError) as exception:
        add_receipt_error(str(exception), "STRICT_INTEGRITY_FAILED")
        if "GRAPH" in str(exception):
            graph_match = "FAIL"

predicate_results = request.get("predicate_results") or []
if "predicate_results" in request and not isinstance(request.get("predicate_results"), list):
    errors.append("PREDICATE_INVALID: predicate_results must be a list")
    predicate_results = []
predicate_by_id = {}
for index, predicate in enumerate(predicate_results):
    if not isinstance(predicate, dict):
        errors.append(f"PREDICATE_INVALID: predicate result {index + 1} must be a mapping")
        continue
    predicate_id = predicate.get("predicate_id") or predicate.get("id")
    if not present(predicate_id):
        errors.append(f"PREDICATE_INVALID: predicate result {index + 1} requires an ID")
        continue
    if predicate_id in predicate_by_id:
        errors.append(f"PREDICATE_INVALID: duplicate predicate result {predicate_id}")
        continue
    predicate_by_id[predicate_id] = predicate
    status = predicate.get("status")
    if status not in ("PASS", "FAIL", "SKIPPED"):
        code = "PREDICATE_MISSING" if predicate.get("required") is True else "PREDICATE_INVALID"
        errors.append(f"{code}: predicate {predicate_id} has no valid status")
    elif predicate.get("required") is True and status != "PASS":
        errors.append(f"PREDICATE_FAILED: required predicate {predicate_id} must PASS")
    if predicate.get("required") is True and not present(predicate.get("evidence_refs")):
        errors.append(f"PREDICATE_MISSING: required predicate {predicate_id} needs evidence")

required_predicate_ids = list(authorization.get("required_predicate_ids") or [])
reported_predicate_ids = request.get("required_predicate_ids")
if reported_predicate_ids is not None and reported_predicate_ids != required_predicate_ids:
    errors.append("PREDICATE_AUTHORITY_MISMATCH: request cannot change authorized predicates")
if not isinstance(required_predicate_ids, list):
    errors.append("PREDICATE_INVALID: required_predicate_ids must be a list")
    required_predicate_ids = []
for predicate_id in required_predicate_ids:
    predicate = predicate_by_id.get(predicate_id)
    if not predicate:
        errors.append(f"PREDICATE_MISSING: required predicate {predicate_id} is absent")
    elif predicate.get("status") != "PASS":
        errors.append(f"PREDICATE_FAILED: required predicate {predicate_id} must PASS")

for key in [
    "authorization_id",
    "dispatch_tool_call_ref",
    "executor_session_ref",
    "executor_kind",
    "loaded_domain_execution_skill_ref",
    "capability_selection_ref",
    "executed_stage_skills",
    "executed_atomic_skill_refs",
    "knowledge_plan_id",
    "knowledge_consumption_result_ref",
]:
    if not present(receipt.get(key)):
        add_receipt_error(f"execution_receipt.{key} is required")

if receipt.get("authorization_id") != authorization.get("authorization_id"):
    add_receipt_error(
        "execution receipt authorization_id does not match",
        "AUTHORIZATION_DRIFT",
    )
if authorization.get("execution_unit_ref") != execution_unit_ref:
    errors.append("authorization execution_unit_ref does not match")
if authorization.get("selected_domain") != domain:
    errors.append("authorization selected_domain does not match")
if authorization.get("selected_lane") != lane:
    errors.append("authorization selected_lane does not match")
if receipt.get("executor_kind") != authorization.get("executor_kind"):
    add_receipt_error("execution receipt executor_kind does not match authorization")
if receipt.get("loaded_domain_execution_skill_ref") != authorization.get("domain_execution_skill_ref"):
    add_receipt_error("execution receipt Domain Skill does not match authorization")
if normalized_ref(receipt.get("capability_selection_ref")) != normalized_ref(selection_ref):
    add_receipt_error(
        "execution receipt capability_selection_ref does not match authorization"
    )
if list(receipt.get("executed_atomic_skill_refs") or []) != list(authorization.get("selected_atomic_skill_refs") or []):
    add_receipt_error("execution receipt atomic Skills do not match authorization")

executed_stage_skills = list(receipt.get("executed_stage_skills") or [])
if len(executed_stage_skills) != len(selection_stage_skills):
    add_receipt_error(
        "execution receipt stage Skills are missing or contain unselected entries"
    )
for index, selected_skill in enumerate(selection_stage_skills):
    if index >= len(executed_stage_skills):
        break
    executed_skill = executed_stage_skills[index] or {}
    for key in ["stage", "step_id", "capability_id", "execution_order"]:
        if executed_skill.get(key) != selected_skill.get(key):
            add_receipt_error(
                f"execution receipt stage Skill order/identity mismatch at position {index + 1}: {key}"
            )
    if normalized_ref(executed_skill.get("skill_ref")) != normalized_ref(selected_skill.get("skill_ref")):
        add_receipt_error(
            f"execution receipt stage Skill order/identity mismatch at position {index + 1}: skill_ref"
        )
    if str(executed_skill.get("status") or "").lower() not in ("completed", "succeeded"):
        add_receipt_error(
            f"execution receipt stage Skill did not succeed at position {index + 1}"
        )
    if not present(executed_skill.get("evidence_refs")):
        add_receipt_error(
            f"execution receipt stage Skill evidence_refs missing at position {index + 1}"
        )
if receipt.get("knowledge_plan_id") != authorization.get("knowledge_plan_id"):
    add_receipt_error("execution receipt knowledge_plan_id does not match authorization")
if knowledge.get("knowledge_plan_id") != receipt.get("knowledge_plan_id"):
    errors.append("knowledge result knowledge_plan_id does not match execution receipt")
if knowledge.get("execution_unit_ref") != execution_unit_ref:
    errors.append("knowledge result execution_unit_ref does not match")

receipt_knowledge_ref = str(Path(str(receipt.get("knowledge_consumption_result_ref") or "")).resolve())
request_knowledge_ref = str(Path(str(request.get("knowledge_consumption_result_ref") or "")).resolve())
if receipt_knowledge_ref != request_knowledge_ref:
    add_receipt_error("execution receipt knowledge consumption result ref does not match")
if not present(receipt.get("changed_paths")):
    add_receipt_error("execution_receipt.changed_paths must not be empty")
if not present(receipt.get("evidence_refs")):
    add_receipt_error("execution_receipt.evidence_refs must not be empty")

allowed_paths = [str(p).rstrip("/") for p in (authorization.get("allowed_paths") or [])]
for changed_path in (receipt.get("changed_paths") or []):
    changed = str(changed_path)
    covered = any(
        changed == allowed or changed.startswith(allowed + "/")
        for allowed in allowed_paths
    )
    if not covered:
        add_receipt_error(f"changed path is outside authorization: {changed_path}")

loaded_domain_skill = str(receipt.get("loaded_domain_execution_skill_ref") or "")
authorized_domain_skill = str(authorization.get("domain_execution_skill_ref") or "")
if authorized_domain_skill and normalized_ref(loaded_domain_skill) != normalized_ref(authorized_domain_skill):
    add_receipt_error("completion must load the authorized selected-module execution Skill")

evidence = request.get("evidence") or {}
if fixed_architecture or legacy_fixed:
    required_evidence = [
        "d3a_specification_ref",
        "api_contract_ref",
        "completion_summary_ref",
    ]
elif lane is None:
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
        label = "fixed architecture" if (fixed_architecture or legacy_fixed) else lane
        errors.append(f"evidence.{key} is required for {label} completion")

if not (fixed_architecture or legacy_fixed) and request.get("test_based_verification") == True and lane is not None and lane != "fast":
    coverage_present = present(evidence.get("coverage_evidence_ref"))
    exemption = evidence.get("coverage_exemption") or {}
    exemption_present = present(exemption.get("reason"))
    if not coverage_present and not exemption_present:
        errors.append("coverage evidence or a reasoned exemption is required")

if fixed_architecture or legacy_fixed:
    legacy_payload = request.get(LEGACY_FIXED_DOMAIN_ID) or {}
    required_domains = []
    if is_v2_module:
        registry_ref = ((selected_module.get("registries") or {}).get("test_domains_ref"))
        registry = load_yaml(registry_ref) if present(registry_ref) else {}
        rows = registry.get("test_domains", registry.get("domains", [])) if isinstance(registry, dict) else []
        required_domains = [row.get("id") for row in rows if isinstance(row, dict) and present(row.get("id"))]
    else:
        required_domains = list(legacy_payload.get("required_dt_domains") or [])
    if not required_domains:
        errors.append("fixed architecture required test domains must not be empty")
    if len(required_domains) != len(set(required_domains)):
        errors.append("fixed architecture required test domains must contain unique IDs")
    if is_v2_module:
        for predicate_id in ["required_dt_domains_green", "tran_build_pass"]:
            if predicate_id not in required_predicate_ids:
                errors.append(f"selected Pack completion policy is missing {predicate_id}")
    else:
        red = legacy_payload.get("red_evidence_by_domain") or {}
        green = legacy_payload.get("green_evidence_by_domain") or {}
        for dt_domain in required_domains:
            if not present(red.get(dt_domain)):
                errors.append(f"missing RED evidence for DT domain {dt_domain}")
            if not present(green.get(dt_domain)):
                errors.append(f"missing GREEN evidence for DT domain {dt_domain}")
    if legacy_fixed and legacy_payload.get("tran_build_status") != "PASS":
        errors.append("legacy fixed architecture tran_build_status must be PASS")
    if legacy_fixed and not present(legacy_payload.get("tran_build_evidence_ref")):
        errors.append("legacy fixed architecture tran_build_evidence_ref is required")

result_key = "completion_result" if proof_contract_active else "completion_verification_result"
result_status = (
    "DONE"
    if not errors
    else ("BLOCKED" if proof_contract_active else "BLOCKED_COMPLETION")
)
result_body = {
    "status": result_status,
    "selected_domain": domain,
    "selected_lane": lane,
    "execution_unit_ref": execution_unit_ref,
    "authorization_id": receipt.get("authorization_id") if not errors else None,
    "knowledge_plan_id": receipt.get("knowledge_plan_id") if not errors else None,
    "errors": errors,
}
if proof_contract_active:
    result_body["graph_match"] = graph_match
    result_body["order_match"] = order_match
    result_body["receipt_integrity"] = (
        "FAIL" if receipt_integrity_errors else "PASS"
    )
    result_body["predicate_results"] = predicate_results

result = {result_key: result_body}

output = yaml.dump(result, allow_unicode=True)
if args.output:
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
else:
    print(output, end="")

sys.exit(0 if not errors else 4)
