#!/usr/bin/env python3
"""Host-owned atomic dispatch state; hashes are identifiers, not signatures.

The host must keep the state path outside executor-writable scope. A replay is
safe to retry only when the downstream honors the bound idempotency key.
"""

import copy
import fcntl
import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_event_ledger import process as replay_ledger
from runtime_integrity import verify_graph


class DispatchStateError(ValueError):
    pass


def _fail(code, message):
    raise DispatchStateError(f"{code}: {message}")


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _state_hash(state):
    return _hash({key: value for key, value in state.items() if key != "state_sha256"})


@contextmanager
def _locked(state_path):
    path = Path(state_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield path
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _load(path):
    try:
        state = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        _fail("DISPATCH_STATE_INVALID", str(error))
    if (not isinstance(state, dict) or state.get("state_sha256") != _state_hash(state)
            or type(state.get("revision")) is not int
            or state.get("revision") != len(state.get("events") or [])):
        _fail("DISPATCH_STATE_INVALID", "state content hash changed")
    return state


def _atomic_write(path, state):
    state["state_sha256"] = _state_hash(state)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", delete=False) as output:
            temporary = Path(output.name)
            yaml.safe_dump(state, output, allow_unicode=True, sort_keys=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _host_records(state, events=None, evidence=None):
    return {
        "run_id": state["run_id"],
        "authorization_id": state["authorization_id"],
        "graph_sha256": state["graph_sha256"],
        "events": copy.deepcopy(state["events"] if events is None else events),
        "predicate_results": list((state.get("predicate_attestations") or {}).values()),
        "evidence_sha256": dict(state["evidence_sha256"] if evidence is None else evidence),
    }


def _replay(state, events, evidence):
    request = {"run_id": state["run_id"], "authorization_id": state["authorization_id"],
               "graph_sha256": state["graph_sha256"], "events": events}
    result = replay_ledger(state["graph"], request,
                           host_records=_host_records(state, events, evidence))
    if result.get("status") == "INVALID":
        _fail("DISPATCH_STATE_INVALID", str(result.get("errors") or []))
    return result


def initialize_state(state_path, graph, authorization, run_id):
    verify_graph(graph)
    if (authorization.get("status") != "AUTHORIZED"
            or not authorization.get("authorization_id")):
        _fail("AUTHORIZATION_MISMATCH", "authorization must be AUTHORIZED")
    if authorization.get("graph_sha256") != graph.get("graph_sha256"):
        _fail("GRAPH_MISMATCH", "authorization does not bind graph")
    if not isinstance(run_id, str) or not run_id:
        _fail("DISPATCH_STATE_INVALID", "run_id is required")
    with _locked(state_path) as path:
        if path.exists():
            state = _load(path)
            expected = (run_id, authorization.get("authorization_id"), graph["graph_sha256"])
            actual = (state.get("run_id"), state.get("authorization_id"), state.get("graph_sha256"))
            if actual != expected:
                _fail("DISPATCH_STATE_CONFLICT", "existing state identity differs")
            return copy.deepcopy(state)
        state = {
            "version": 1,
            "status": "IN_PROGRESS",
            "revision": 0,
            "run_id": run_id,
            "authorization_id": authorization.get("authorization_id"),
            "graph_sha256": graph["graph_sha256"],
            "graph": copy.deepcopy(graph),
            "nodes": [{"node_id": row["node_id"], "status": "PENDING"}
                      for row in graph.get("nodes") or []],
            "tickets": {},
            "successes": {},
            "events": [],
            "evidence_sha256": {},
            "predicate_attestations": {},
        }
        _atomic_write(path, state)
        return copy.deepcopy(state)


def _current_node(state):
    return next((row for row in state["nodes"] if row["status"] != "SUCCEEDED"), None)


def acquire_dispatch(state_path, claim):
    required = ["authorization_id", "graph_sha256", "node_id",
                "predecessor_state_sha256", "dispatch_tool_call_ref",
                "executor_session_ref", "idempotency_key"]
    if not isinstance(claim, dict) or any(not claim.get(key) for key in required):
        _fail("DISPATCH_CLAIM_INVALID", "all ticket identity fields are required")
    with _locked(state_path) as path:
        state = _load(path)
        if claim["authorization_id"] != state["authorization_id"]:
            _fail("AUTHORIZATION_MISMATCH", "claim authorization changed")
        if claim["graph_sha256"] != state["graph_sha256"]:
            _fail("GRAPH_MISMATCH", "claim graph changed")
        existing = state["tickets"].get(claim["node_id"])
        payload = {key: claim[key] for key in required}
        payload.update(run_id=state["run_id"],
                       predecessor_revision=(existing or {}).get(
                           "predecessor_revision", state["revision"]),
                       downstream_idempotency_supported=bool(
                           claim.get("downstream_idempotency_supported")))
        ticket = dict(payload, ticket_id=_hash(payload))
        if existing:
            if existing.get("idempotency_key") != claim["idempotency_key"]:
                _fail("IDEMPOTENCY_CONFLICT", "node already has another idempotency key")
            if existing != ticket:
                _fail("DISPATCH_ALREADY_CLAIMED", "node ticket binding differs")
            status = "REPLAY" if existing["downstream_idempotency_supported"] else "RECOVERY_REQUIRED"
            return {"status": status, "ticket": copy.deepcopy(existing)}
        if claim["predecessor_state_sha256"] != state["state_sha256"]:
            _fail("PREDECESSOR_STATE_MISMATCH", "claim does not bind current state")
        current = _current_node(state)
        if not current or current["node_id"] != claim["node_id"] or current["status"] != "PENDING":
            _fail("ORDER_VIOLATION", "only the current PENDING node may be claimed")
        event = {"idempotency_key": claim["idempotency_key"], "node_id": claim["node_id"],
                 "event_type": "NODE_DISPATCHED",
                 "dispatch_tool_call_ref": claim["dispatch_tool_call_ref"],
                 "executor_session_ref": claim["executor_session_ref"],
                 "ticket_id": ticket["ticket_id"], "evidence_refs": []}
        replayed = _replay(state, state["events"] + [event], state["evidence_sha256"])
        state["events"] = replayed["events"]
        state["tickets"][claim["node_id"]] = ticket
        current["status"] = "DISPATCHED"
        state["revision"] += 1
        _atomic_write(path, state)
        return {"status": "ISSUED", "ticket": copy.deepcopy(ticket)}


def record_success(state_path, success):
    if not isinstance(success, dict) or not success.get("ticket_id"):
        _fail("SUCCESS_INVALID", "ticket_id is required")
    with _locked(state_path) as path:
        state = _load(path)
        tickets = [row for row in state["tickets"].values()
                   if row.get("ticket_id") == success["ticket_id"]]
        if len(tickets) != 1:
            _fail("SUCCESS_CONFLICT", "ticket is not host-owned")
        ticket = tickets[0]
        payload = {"ticket_id": ticket["ticket_id"],
                   "dispatch_tool_call_ref": success.get("dispatch_tool_call_ref"),
                   "executor_session_ref": success.get("executor_session_ref"),
                   "evidence_refs": list(success.get("evidence_refs") or []),
                   "evidence_sha256": dict(success.get("evidence_sha256") or {})}
        existing = state["successes"].get(ticket["ticket_id"])
        if existing:
            if existing != payload:
                _fail("SUCCESS_CONFLICT", "success replay content differs")
            return {"status": "REPLAY", "ticket": copy.deepcopy(ticket)}
        if (payload["dispatch_tool_call_ref"] != ticket["dispatch_tool_call_ref"]
                or payload["executor_session_ref"] != ticket["executor_session_ref"]
                or not payload["evidence_refs"]):
            _fail("SUCCESS_CONFLICT", "success does not match ticket")
        for ref in payload["evidence_refs"]:
            try:
                actual = hashlib.sha256(Path(ref).read_bytes()).hexdigest()
            except OSError:
                _fail("SUCCESS_CONFLICT", "evidence is unreadable")
            if payload["evidence_sha256"].get(ref) != actual:
                _fail("SUCCESS_CONFLICT", "evidence hash differs")
        event = {"idempotency_key": ticket["ticket_id"] + ":success",
                 "node_id": ticket["node_id"], "event_type": "NODE_SUCCEEDED",
                 "dispatch_tool_call_ref": ticket["dispatch_tool_call_ref"],
                 "executor_session_ref": ticket["executor_session_ref"],
                 "ticket_id": ticket["ticket_id"], "evidence_refs": payload["evidence_refs"]}
        evidence = dict(state["evidence_sha256"], **payload["evidence_sha256"])
        replayed = _replay(state, state["events"] + [event], evidence)
        state["events"], state["evidence_sha256"] = replayed["events"], evidence
        state["successes"][ticket["ticket_id"]] = payload
        next(row for row in state["nodes"] if row["node_id"] == ticket["node_id"])["status"] = "SUCCEEDED"
        state["status"] = "COMPLETE" if _current_node(state) is None else "IN_PROGRESS"
        state["revision"] += 1
        _atomic_write(path, state)
        return {"status": "SUCCEEDED", "ticket": copy.deepcopy(ticket)}


def record_predicate(state_path, attestation):
    """Atomically bind an evaluated predicate to this host-owned run identity."""
    required = ["authorization_id", "graph_sha256", "predicate_id", "status", "evidence_refs"]
    if (not isinstance(attestation, dict)
            or any(not attestation.get(key) for key in required)
            or attestation.get("status") not in {"PASS", "FAIL"}):
        _fail("PREDICATE_ATTESTATION_INVALID", "identity, status, and evidence are required")
    with _locked(state_path) as path:
        state = _load(path)
        if (attestation["authorization_id"] != state["authorization_id"]
                or attestation["graph_sha256"] != state["graph_sha256"]):
            _fail("PREDICATE_ATTESTATION_MISMATCH", "predicate identity differs")
        refs = list(attestation["evidence_refs"])
        hashes = dict(attestation.get("evidence_sha256") or {})
        if not refs:
            _fail("PREDICATE_ATTESTATION_INVALID", "predicate evidence is required")
        for ref in refs:
            try:
                actual = hashlib.sha256(Path(ref).read_bytes()).hexdigest()
            except OSError:
                _fail("PREDICATE_ATTESTATION_INVALID", "predicate evidence is unreadable")
            if hashes.get(ref) != actual:
                _fail("PREDICATE_ATTESTATION_MISMATCH", "predicate evidence hash differs")
        record = {
            "authorization_id": state["authorization_id"],
            "graph_sha256": state["graph_sha256"],
            "predicate_id": attestation["predicate_id"],
            "status": attestation["status"],
            "evidence_refs": refs,
        }
        existing = state["predicate_attestations"].get(record["predicate_id"])
        if existing:
            if existing != record:
                _fail("PREDICATE_ATTESTATION_CONFLICT", "predicate replay differs")
            return {"status": "REPLAY", "predicate": copy.deepcopy(existing)}
        state["predicate_attestations"][record["predicate_id"]] = record
        state["evidence_sha256"].update(hashes)
        _atomic_write(path, state)
        return {"status": "ATTESTED", "predicate": copy.deepcopy(record)}


def export_snapshot(state_path):
    with _locked(state_path) as path:
        state = _load(path)
        snapshot = copy.deepcopy(state)
        host = _host_records(state)
        ledger = _replay(state, state["events"], state["evidence_sha256"])
        snapshot["host_execution_records"] = host
        snapshot["run_event_ledger_result"] = ledger
        return snapshot
