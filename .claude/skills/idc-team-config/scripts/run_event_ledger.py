#!/usr/bin/env python3

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_integrity import (IntegrityError, strict_graph, verify_event,
                               verify_graph, verify_host)


HASH_FIELDS = {"sequence", "previous_event_hash", "event_hash"}
ALLOWED_EVENT_TYPES = {"NODE_DISPATCHED", "NODE_SUCCEEDED"}


def load_yaml(path):
    try:
        return yaml.safe_load(Path(path).resolve().read_text(encoding="utf-8")) or {}
    except (FileNotFoundError, OSError, yaml.YAMLError) as error:
        raise ValueError(str(error)) from error


def canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def semantic_event(event):
    return {key: value for key, value in event.items() if key not in HASH_FIELDS}


def error(code, message):
    return {"code": code, "message": message}


def initial_result(request):
    return {
        "status": "INVALID",
        "run_id": request.get("run_id"),
        "graph_sha256": request.get("graph_sha256"),
        "authorization_id": request.get("authorization_id"),
        "state": {},
        "proof": {},
        "ledger_hash": None,
        "events": [],
        "applied_event_count": 0,
        "deduplicated_event_count": 0,
        "errors": [],
    }


def ordered_nodes(graph, errors):
    nodes = graph.get("nodes") or []
    if graph.get("status") != "READY" or not isinstance(nodes, list) or not nodes:
        errors.append(error("INVALID_GRAPH", "Run Graph must be READY with nodes"))
        return []
    if any(not isinstance(node, dict) for node in nodes):
        errors.append(error("INVALID_GRAPH", "Run Graph nodes must be mappings"))
        return []
    if any(
        not isinstance(node.get("execution_order"), int)
        or isinstance(node.get("execution_order"), bool)
        for node in nodes
    ):
        errors.append(error("INVALID_GRAPH", "execution_order values must be integers"))
        return []
    ordered = sorted(nodes, key=lambda node: node.get("execution_order", 0))
    node_ids = [node.get("node_id") for node in ordered]
    execution_orders = [node.get("execution_order") for node in ordered]
    if (
        any(not isinstance(node_id, str) or not node_id for node_id in node_ids)
        or len(node_ids) != len(set(node_ids))
        or execution_orders != list(range(1, len(ordered) + 1))
    ):
        errors.append(
            error(
                "INVALID_GRAPH",
                "Run Graph nodes require unique IDs and contiguous one-based execution_order",
            )
        )
        return []
    return ordered


def current_node_id(nodes, node_states):
    for node in nodes:
        node_id = node["node_id"]
        if node_states[node_id] != "SUCCEEDED":
            return node_id
    return None


def apply_transition(event_row, nodes, node_states):
    node_id = event_row.get("node_id")
    event_type = event_row.get("event_type")
    if event_type not in ALLOWED_EVENT_TYPES:
        return error("INVALID_TRANSITION", "unsupported event_type: {}".format(event_type))
    if node_id not in node_states:
        return error("INVALID_TRANSITION", "event references an unknown node")

    current = current_node_id(nodes, node_states)
    if node_id != current:
        return error(
            "ORDER_VIOLATION",
            "only the current incomplete node may transition",
        )

    if event_type == "NODE_DISPATCHED":
        if node_states[node_id] != "PENDING":
            return error("INVALID_TRANSITION", "node can be dispatched only from PENDING")
        if not event_row.get("dispatch_tool_call_ref") or not event_row.get(
            "executor_session_ref"
        ):
            return error("MISSING_ATTESTATION", "dispatch requires tool-call and session refs")
        node_states[node_id] = "DISPATCHED"
        return None

    if node_states[node_id] != "DISPATCHED":
        return error("INVALID_TRANSITION", "node can succeed only after dispatch")
    if (
        not event_row.get("dispatch_tool_call_ref")
        or not event_row.get("executor_session_ref")
        or not event_row.get("evidence_refs")
    ):
        return error("MISSING_ATTESTATION", "success requires attestations and evidence")
    node_states[node_id] = "SUCCEEDED"
    return None


def event_hash_payload(request, event_row):
    return {
        "run_id": request.get("run_id"),
        "graph_sha256": request.get("graph_sha256"),
        "authorization_id": request.get("authorization_id"),
        "event": {key: value for key, value in event_row.items() if key != "event_hash"},
    }


def proof_for(request, state, ledger_hash, event_count):
    proof_body = {
        "run_id": request.get("run_id"),
        "graph_sha256": request.get("graph_sha256"),
        "authorization_id": request.get("authorization_id"),
        "event_count": event_count,
        "ledger_hash": ledger_hash,
        "state_sha256": canonical_sha256(state),
    }
    return dict(proof_body, proof_sha256=canonical_sha256(proof_body))


def process(graph, request, host_records=None):
    result = initial_result(request)
    errors = result["errors"]
    nodes = ordered_nodes(graph, errors)
    strict = strict_graph(graph) or host_records is not None
    if strict:
        try:
            verify_graph(graph)
            verify_host(host_records, request)
        except (IntegrityError, TypeError, ValueError) as exception:
            errors.append(error("INTEGRITY_INVALID", str(exception)))

    if not request.get("run_id") or not request.get("authorization_id"):
        errors.append(error("INVALID_REQUEST", "run_id and authorization_id are required"))
    if not graph.get("graph_sha256"):
        errors.append(error("INVALID_GRAPH", "Run Graph graph_sha256 is required"))
    if request.get("graph_sha256") != graph.get("graph_sha256"):
        errors.append(error("GRAPH_MISMATCH", "request graph_sha256 does not match Run Graph"))
    input_events = request.get("events")
    if not isinstance(input_events, list):
        errors.append(error("INVALID_REQUEST", "events must be a list"))
        input_events = []
    if errors:
        return result

    node_states = {node["node_id"]: "PENDING" for node in nodes}
    persisted_events = []
    idempotency = {}
    idempotency_events = {}
    deduplicated = 0
    previous_hash = None
    dispatched = {}

    for source_event in input_events:
        if not isinstance(source_event, dict):
            errors.append(error("INVALID_EVENT", "events must be mappings"))
            break
        event_row = dict(source_event)
        idempotency_key = event_row.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            errors.append(error("INVALID_EVENT", "idempotency_key is required"))
            break

        persisted = any(field in event_row for field in HASH_FIELDS)
        if persisted and not HASH_FIELDS.issubset(event_row):
            errors.append(error("HASH_CHAIN_INVALID", "persisted event hash fields are incomplete"))
            break
        if persisted and event_row.get("event_hash") != canonical_sha256(
            event_hash_payload(request, event_row)
        ):
            errors.append(error("HASH_CHAIN_INVALID", "persisted event hash is invalid"))
            break

        semantic = semantic_event(event_row)
        semantic_hash = canonical_sha256(semantic)
        previous_semantic_hash = idempotency.get(idempotency_key)
        if previous_semantic_hash is not None:
            if previous_semantic_hash != semantic_hash:
                errors.append(
                    error(
                        "IDEMPOTENCY_CONFLICT",
                        "idempotency key was reused with different event content",
                    )
                )
                break
            if persisted and event_row != idempotency_events[idempotency_key]:
                errors.append(error("HASH_CHAIN_INVALID", "persisted duplicate event changed"))
                break
            deduplicated += 1
            continue

        expected_sequence = len(persisted_events) + 1
        if persisted:
            if (
                type(event_row.get("sequence")) is not int
                or
                event_row.get("sequence") != expected_sequence
                or event_row.get("previous_event_hash") != previous_hash
            ):
                errors.append(error("HASH_CHAIN_INVALID", "event hash chain verification failed"))
                break
        else:
            event_row["sequence"] = expected_sequence
            event_row["previous_event_hash"] = previous_hash
            event_row["event_hash"] = canonical_sha256(event_hash_payload(request, event_row))

        if strict:
            try:
                verify_event(event_row, host_records, dispatched)
            except (IntegrityError, TypeError, ValueError) as exception:
                errors.append(error("INTEGRITY_INVALID", str(exception)))
                break
        transition_error = apply_transition(event_row, nodes, node_states)
        if transition_error:
            errors.append(transition_error)
            break
        idempotency[idempotency_key] = semantic_hash
        idempotency_events[idempotency_key] = event_row
        persisted_events.append(event_row)
        previous_hash = event_row["event_hash"]

    state = {
        "sequence": len(persisted_events),
        "current_node_id": current_node_id(nodes, node_states),
        "nodes": [
            {"node_id": node["node_id"], "status": node_states[node["node_id"]]}
            for node in nodes
        ],
    }
    result.update(
        {
            "status": (
                "INVALID"
                if errors
                else ("COMPLETE" if state["current_node_id"] is None else "IN_PROGRESS")
            ),
            "state": state,
            "proof": proof_for(request, state, previous_hash, len(persisted_events)),
            "ledger_hash": previous_hash,
            "events": persisted_events,
            "applied_event_count": len(persisted_events),
            "deduplicated_event_count": deduplicated,
        }
    )
    return result


def write_result(path, result):
    output = yaml.safe_dump(
        {"run_event_ledger_result": result},
        allow_unicode=True,
        sort_keys=False,
    )
    Path(path).resolve().write_text(output, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Replay and verify an ordered Run Graph ledger")
    parser.add_argument("--graph", required=True, metavar="PATH")
    parser.add_argument("--request", required=True, metavar="PATH")
    parser.add_argument("--output", required=True, metavar="PATH")
    parser.add_argument("--host-records", metavar="PATH", help="independent host adapter records")
    args = parser.parse_args()

    try:
        graph_document = load_yaml(args.graph)
        request_document = load_yaml(args.request)
        if not isinstance(graph_document, dict) or not isinstance(request_document, dict):
            raise ValueError("graph and request documents must be mappings")
        graph = graph_document.get("run_graph") or graph_document
        request = request_document.get("event_ledger_request") or request_document
        if not isinstance(graph, dict) or not isinstance(request, dict):
            raise ValueError("graph and request payloads must be mappings")
        host = load_yaml(args.host_records).get("host_execution_records") if args.host_records else None
        result = process(graph, request, host_records=host)
    except (TypeError, ValueError) as exception:
        result = initial_result({})
        result["errors"].append(error("INVALID_INPUT", str(exception)))

    write_result(args.output, result)
    if result.get("status") == "INVALID":
        for item in result.get("errors") or []:
            print("{}: {}".format(item.get("code"), item.get("message")), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
