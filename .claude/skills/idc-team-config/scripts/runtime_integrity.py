"""Integrity checks for host-controlled execution, not a signature service.

host_records is an independent host adapter input, never request/receipt data.
The caller must protect its provenance and storage from the executor. Local
hashes prove consistency with those records, not authenticity of arbitrary YAML.
"""

import hashlib
import json
import re
from pathlib import Path


HASH_FIELDS = {"sequence", "previous_event_hash", "event_hash"}


class IntegrityError(ValueError):
    pass


def fail(code, message):
    raise IntegrityError("{}: {}".format(code, message))


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def strict_graph(graph, authorized_hash=None):
    # Narrow compatibility for pre-compiler public fixtures only. Real graph-*
    # identities, authoritative hashes and all other inputs default to strict.
    legacy = (graph.get("graph_sha256") == "placeholder-graph-sha256"
              and "placeholder" in str(graph.get("graph_id") or "")
              and not str(graph.get("graph_id") or "").startswith("graph-"))
    return not legacy or authorized_hash not in (None, "placeholder-graph-sha256")


def verify_graph(graph):
    body = {key: value for key, value in graph.items()
            if key not in ("graph_id", "graph_sha256")}
    actual = canonical_hash(body)
    if (graph.get("status") != "READY" or graph.get("graph_sha256") != actual
            or graph.get("graph_id") != "graph-" + actual[:16]):
        fail("GRAPH_HASH_INVALID", "compiled graph content/identity changed")


def verify_host(host, identity):
    if not isinstance(host, dict):
        fail("HOST_ATTESTATION_REQUIRED", "independent host records are required")
    for key in ("run_id", "authorization_id", "graph_sha256"):
        if not isinstance(host.get(key), str) or not host[key] or host[key] != identity.get(key):
            fail("HOST_ATTESTATION_MISMATCH", "host identity mismatch: " + key)
    if not isinstance(host.get("events"), list):
        fail("HOST_ATTESTATION_INVALID", "host events must be a list")


def verify_evidence(refs, host):
    if not isinstance(refs, list) or not refs:
        fail("EVIDENCE_REQUIRED", "evidence references are required")
    hashes = host.get("evidence_sha256")
    if not isinstance(hashes, dict):
        fail("EVIDENCE_HASH_MISSING", "host evidence content hashes are required")
    for ref in refs:
        expected = hashes.get(ref) if isinstance(ref, str) else None
        if not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected):
            fail("EVIDENCE_HASH_MISSING", "reference is not bound by host records")
        try:
            actual = hashlib.sha256(Path(ref).read_bytes()).hexdigest()
        except (OSError, ValueError):
            fail("EVIDENCE_UNREADABLE", "host-bound evidence cannot be read")
        if actual != expected:
            fail("EVIDENCE_HASH_MISMATCH", "host-bound evidence bytes changed")


def event_semantics(event):
    return {key: value for key, value in event.items() if key not in HASH_FIELDS}


def verify_event(event, host, dispatched):
    matches = [row for row in host["events"] if isinstance(row, dict)
               and row.get("idempotency_key") == event.get("idempotency_key")]
    if len(matches) != 1 or canonical_hash(event_semantics(matches[0])) != canonical_hash(event_semantics(event)):
        fail("HOST_ATTESTATION_MISMATCH", "event is not an exact host-recorded event")
    pair = (event.get("dispatch_tool_call_ref"), event.get("executor_session_ref"))
    if any(not isinstance(value, str) or not value for value in pair):
        fail("HOST_ATTESTATION_INVALID", "dispatch/session identities are required")
    node = event.get("node_id")
    if event.get("event_type") == "NODE_DISPATCHED":
        dispatched[node] = pair
    elif event.get("event_type") == "NODE_SUCCEEDED":
        if dispatched.get(node) != pair:
            fail("HOST_ATTESTATION_MISMATCH", "success does not match original dispatch session")
        verify_evidence(event.get("evidence_refs"), host)


def verify_predicates(authorization, request, host):
    required = authorization.get("required_predicate_ids")
    if (not isinstance(required, list)
            or any(not isinstance(value, str) or not value for value in required)
            or len(required) != len(set(required))):
        fail("PREDICATE_AUTHORITY_MISSING", "authorization must bind required predicate IDs")
    claimed_ids = request.get("required_predicate_ids", required)
    if not isinstance(claimed_ids, list) or any(value not in claimed_ids for value in required):
        fail("PREDICATE_AUTHORITY_MISMATCH", "request cannot remove authorized predicates")
    supplied = request.get("predicate_results")
    records = host.get("predicate_results")
    if not isinstance(supplied, list) or not isinstance(records, list):
        fail("PREDICATE_MISSING", "predicate results and host records are required")
    indexed = {}
    for row in supplied:
        if not isinstance(row, dict) or not isinstance(row.get("predicate_id"), str):
            fail("PREDICATE_INVALID", "predicate result requires an ID")
        pid = row["predicate_id"]
        if pid in indexed:
            fail("PREDICATE_INVALID", "duplicate predicate ID")
        indexed[pid] = row
    for pid in required:
        row = indexed.get(pid) or {}
        if row.get("status") != "PASS" or row.get("required") is False or not row.get("evidence_refs"):
            fail("PREDICATE_FAILED", "authorized predicate must PASS with evidence: " + pid)
    for pid, row in indexed.items():
        if row.get("status") != "PASS":
            continue
        matches = [record for record in records if isinstance(record, dict)
                   and record.get("predicate_id") == pid]
        if (len(matches) != 1 or matches[0].get("status") != "PASS"
                or matches[0].get("evidence_refs") != row.get("evidence_refs")):
            fail("PREDICATE_ATTESTATION_MISMATCH", "PASS is not backed by host evidence: " + pid)
        verify_evidence(row.get("evidence_refs"), host)


def verify_completion_integrity(graph, authorization, request, receipt, ledger, host, replay):
    """Recompute, never accept a producer's COMPLETE/status/proof assertion."""
    verify_graph(graph)
    if graph.get("graph_sha256") != authorization.get("graph_sha256"):
        fail("GRAPH_AUTHORIZATION_MISMATCH", "graph is not authorized")
    if (graph.get("selected_domain") != authorization.get("selected_domain")
            or graph.get("selected_lane") != authorization.get("selected_lane")):
        fail("GRAPH_AUTHORIZATION_MISMATCH", "graph Domain/Lane changed")
    if not isinstance(ledger, dict) or not ledger:
        fail("LEDGER_REQUIRED", "compiled graph completion requires persisted events")
    if ledger.get("errors"):
        fail("LEDGER_UNRESOLVED_ERRORS", "ledger contains unresolved failures")
    events = ledger.get("events")
    if not isinstance(events, list) or not events:
        fail("LEDGER_INVALID", "complete execution requires nonempty event history")
    if any(not isinstance(event, dict) or not HASH_FIELDS.issubset(event) for event in events):
        fail("LEDGER_HASH_CHAIN_INVALID", "completion requires persisted hash fields")
    identity = {key: ledger.get(key) for key in ("run_id", "authorization_id", "graph_sha256")}
    if identity["authorization_id"] != authorization.get("authorization_id"):
        fail("LEDGER_AUTHORIZATION_MISMATCH", "ledger authorization changed")
    verify_host(host, identity)
    replayed = replay(graph, dict(identity, events=events), host_records=host)
    if replayed.get("status") != "COMPLETE" or replayed.get("errors"):
        fail("LEDGER_REPLAY_INVALID", str(replayed.get("errors") or "incomplete execution"))
    for key in ("status", "state", "proof", "ledger_hash", "applied_event_count", "events"):
        if canonical_hash(ledger.get(key)) != canonical_hash(replayed.get(key)):
            fail("LEDGER_HASH_PROOF_INVALID", "replay differs from claimed " + key)
    succeeded = {event["node_id"]: event for event in events if event["event_type"] == "NODE_SUCCEEDED"}
    for row in receipt.get("executed_nodes") or []:
        node_id = row.get("node_id") if isinstance(row, dict) else row
        record = succeeded.get(node_id) or {}
        for key in ("dispatch_tool_call_ref", "executor_session_ref"):
            value = row.get(key, receipt.get(key)) if isinstance(row, dict) else receipt.get(key)
            if value != record.get(key):
                fail("HOST_ATTESTATION_MISMATCH", "receipt does not match executed node")
    verify_predicates(authorization, request, host)
    verify_evidence(receipt.get("evidence_refs"), host)
    for row in receipt.get("executed_stage_skills") or []:
        verify_evidence(row.get("evidence_refs"), host)
