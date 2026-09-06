#!/usr/bin/env python3
"""RED contract for host-owned, persistent dispatch claims.

The future store is a host adapter boundary, not a signature service. Hashes
prove consistency only relative to a state path protected from executors. A
replayed claim may be retried automatically only when the downstream accepts
the same idempotency key; otherwise it must return RECOVERY_REQUIRED.
"""

import copy
import hashlib
import importlib.util
import json
import multiprocessing
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude/skills/idc-team-config/scripts"
MODULE_PATH = SCRIPTS / "dispatch_state.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DISPATCH = None
IMPORT_ERROR = None
if MODULE_PATH.is_file():
    try:
        DISPATCH = load_module(MODULE_PATH, "dispatch_state_contract")
    except Exception as error:  # A broken module is a controlled RED, not collection failure.
        IMPORT_ERROR = error


def canonical_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def concurrent_acquire(arguments):
    state_path, claim = arguments
    module = load_module(MODULE_PATH, "dispatch_state_worker")
    try:
        return module.acquire_dispatch(state_path, claim)["status"]
    except Exception as error:
        return "ERROR:" + str(error)


class DispatchStateAvailabilityTests(unittest.TestCase):
    def test_dispatch_state_module_and_api_exist(self):
        self.assertTrue(MODULE_PATH.is_file(),
                        "DISPATCH_STATE_MISSING: host-owned state module is required")
        self.assertIsNone(IMPORT_ERROR, "DISPATCH_STATE_IMPORT_FAILED: " + str(IMPORT_ERROR))
        for name in ["initialize_state", "acquire_dispatch", "record_success",
                     "export_snapshot"]:
            self.assertTrue(callable(getattr(DISPATCH, name, None)),
                            "DISPATCH_STATE_API_MISSING: " + name)


@unittest.skipUnless(DISPATCH is not None, "dispatch_state.py not implemented (expected RED)")
class DispatchStateContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)
        nodes = [
            {"node_id": "0001-placeholder-plan", "execution_order": 1,
             "stage": "planning", "skill_id": "placeholder-plan",
             "skill_ref": "<SKILL_REF>", "required": True, "trigger_signals": []},
            {"node_id": "0002-placeholder-code", "execution_order": 2,
             "stage": "implementation", "skill_id": "placeholder-code",
             "skill_ref": "<SKILL_REF>", "required": True, "trigger_signals": []},
        ]
        body = {"status": "READY", "config_sha256": "placeholder-config-sha256",
                "selected_domain": "general", "selected_lane": "lite", "nodes": nodes,
                "edges": [{"from": nodes[0]["node_id"], "to": nodes[1]["node_id"]}],
                "errors": []}
        graph_hash = canonical_hash(body)
        self.graph = dict(body, graph_id="graph-" + graph_hash[:16],
                          graph_sha256=graph_hash)
        self.authorization = {
            "status": "AUTHORIZED", "authorization_id": "placeholder-authorization",
            "graph_sha256": graph_hash, "run_graph_ref": "<RUN_GRAPH_REF>",
            "selected_domain": "general", "selected_lane": "lite",
            "required_predicate_ids": [],
        }
        self.run_id = "placeholder-run"
        self.state_path = self.temp / "host-owned-dispatch-state.yaml"
        self.initial = DISPATCH.initialize_state(
            self.state_path, self.graph, self.authorization, self.run_id)
        self.first_node, self.second_node = [row["node_id"] for row in nodes]
        self.claim = {
            "authorization_id": self.authorization["authorization_id"],
            "graph_sha256": graph_hash,
            "node_id": self.first_node,
            "predecessor_state_sha256": self.initial["state_sha256"],
            "dispatch_tool_call_ref": "placeholder-host-dispatch",
            "executor_session_ref": "placeholder-host-session",
            "idempotency_key": "placeholder-dispatch-key",
            "downstream_idempotency_supported": True,
        }
        self.evidence = self.temp / "placeholder-evidence.json"
        self.evidence.write_text('{"status":"PASS"}\n', encoding="utf-8")
        self.evidence_hash = hashlib.sha256(self.evidence.read_bytes()).hexdigest()

    def claim_once(self, state_path=None, claim=None):
        return DISPATCH.acquire_dispatch(state_path or self.state_path,
                                         claim or self.claim)

    def success_for(self, ticket, **overrides):
        success = {
            "ticket_id": ticket["ticket_id"],
            "dispatch_tool_call_ref": ticket["dispatch_tool_call_ref"],
            "executor_session_ref": ticket["executor_session_ref"],
            "evidence_refs": [str(self.evidence)],
            "evidence_sha256": {str(self.evidence): self.evidence_hash},
        }
        success.update(overrides)
        return success

    def assert_error(self, code, operation):
        with self.assertRaises(Exception) as raised:
            operation()
        self.assertIn(code, str(raised.exception).upper())

    def test_initialize_binds_run_authorization_and_graph(self):
        snapshot = DISPATCH.export_snapshot(self.state_path)
        self.assertEqual(snapshot["run_id"], self.run_id)
        self.assertEqual(snapshot["authorization_id"], self.authorization["authorization_id"])
        self.assertEqual(snapshot["graph_sha256"], self.graph["graph_sha256"])
        self.assertEqual([row["status"] for row in snapshot["nodes"]],
                         ["PENDING", "PENDING"])

    def test_first_node_gets_one_ticket_bound_to_all_claim_fields(self):
        result = self.claim_once()
        self.assertEqual(result["status"], "ISSUED")
        ticket = result["ticket"]
        for field in ["authorization_id", "graph_sha256", "node_id",
                      "predecessor_state_sha256", "dispatch_tool_call_ref",
                      "executor_session_ref", "idempotency_key"]:
            self.assertEqual(ticket[field], self.claim[field])
        self.assertRegex(ticket["ticket_id"], r"^[0-9a-f]{64}$")

    def test_same_claim_replays_same_ticket_in_memory_and_after_reload(self):
        first = self.claim_once()
        second = self.claim_once()
        reloaded = load_module(MODULE_PATH, "dispatch_state_reloaded")
        third = reloaded.acquire_dispatch(self.state_path, self.claim)
        self.assertEqual([first["status"], second["status"], third["status"]],
                         ["ISSUED", "REPLAY", "REPLAY"])
        self.assertEqual(first["ticket"], second["ticket"])
        self.assertEqual(first["ticket"], third["ticket"])
        events = DISPATCH.export_snapshot(self.state_path)["events"]
        self.assertEqual(sum(row["event_type"] == "NODE_DISPATCHED" for row in events), 1)

    def test_claim_binding_conflicts_fail_closed(self):
        # A list preserves both attestation-conflict cases despite their common code.
        variants = [
            ("IDEMPOTENCY_CONFLICT", {"idempotency_key": "placeholder-other-key"}),
            ("DISPATCH_ALREADY_CLAIMED", {"dispatch_tool_call_ref": "placeholder-other-dispatch"}),
            ("DISPATCH_ALREADY_CLAIMED", {"executor_session_ref": "placeholder-other-session"}),
        ]
        for index, (code, changed) in enumerate(variants):
            with self.subTest(changed=changed):
                path = self.temp / f"conflict-{index}.yaml"
                initial = DISPATCH.initialize_state(path, self.graph, self.authorization, self.run_id)
                baseline = dict(self.claim, predecessor_state_sha256=initial["state_sha256"])
                self.claim_once(path, baseline)
                conflicting = dict(baseline, **changed)
                self.assert_error(code, lambda: self.claim_once(path, conflicting))

    def test_successor_before_predecessor_success_is_rejected(self):
        successor = dict(self.claim, node_id=self.second_node,
                         idempotency_key="placeholder-successor-key")
        self.assert_error("ORDER_VIOLATION", lambda: self.claim_once(claim=successor))

    def test_concurrent_claims_issue_at_most_one_ticket(self):
        arguments = [(str(self.state_path), self.claim) for _ in range(6)]
        with multiprocessing.get_context("fork").Pool(6) as pool:
            statuses = pool.map(concurrent_acquire, arguments)
        self.assertEqual(statuses.count("ISSUED"), 1, statuses)
        self.assertEqual(statuses.count("REPLAY"), 5, statuses)
        snapshot = DISPATCH.export_snapshot(self.state_path)
        self.assertEqual(sum(row["event_type"] == "NODE_DISPATCHED"
                             for row in snapshot["events"]), 1)

    def test_success_replay_is_idempotent_and_conflicts_are_rejected(self):
        ticket = self.claim_once()["ticket"]
        success = self.success_for(ticket)
        first = DISPATCH.record_success(self.state_path, success)
        second = DISPATCH.record_success(self.state_path, success)
        self.assertEqual([first["status"], second["status"]], ["SUCCEEDED", "REPLAY"])
        changed_evidence = self.success_for(
            ticket, evidence_sha256={str(self.evidence): "0" * 64})
        self.assert_error("SUCCESS_CONFLICT", lambda: DISPATCH.record_success(
            self.state_path, changed_evidence))
        changed_session = self.success_for(ticket,
                                           executor_session_ref="placeholder-other-session")
        self.assert_error("SUCCESS_CONFLICT", lambda: DISPATCH.record_success(
            self.state_path, changed_session))

    def test_identity_and_predecessor_drift_are_rejected(self):
        variants = [
            ("AUTHORIZATION_MISMATCH", {"authorization_id": "placeholder-other-auth"}),
            ("GRAPH_MISMATCH", {"graph_sha256": "0" * 64}),
            ("PREDECESSOR_STATE_MISMATCH", {"predecessor_state_sha256": "0" * 64}),
        ]
        for code, changed in variants:
            with self.subTest(code=code):
                self.assert_error(code, lambda: self.claim_once(
                    claim=dict(self.claim, **changed)))

    def test_non_idempotent_downstream_crash_replay_requires_recovery(self):
        claim = dict(self.claim, downstream_idempotency_supported=False)
        first = self.claim_once(claim=claim)
        reloaded = load_module(MODULE_PATH, "dispatch_state_non_idempotent_reloaded")
        second = reloaded.acquire_dispatch(self.state_path, claim)
        self.assertEqual(first["status"], "ISSUED")
        self.assertEqual(second["status"], "RECOVERY_REQUIRED")
        self.assertEqual(first["ticket"], second["ticket"])
        self.assertEqual(len(DISPATCH.export_snapshot(self.state_path)["events"]), 1)

    def completion_fixture(self, complete):
        runtime_tests = load_module(ROOT / "tests/test_runtime_integrity.py",
                                    "runtime_integrity_completion_fixture")
        case = runtime_tests.RuntimeIntegrityTests(methodName="test_real_compile_ledger_completion_positive")
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.authorization["required_predicate_ids"] = []
        Path(case.authorization_ref).write_text(yaml.safe_dump(
            {"execution_authorization_result": case.authorization}, sort_keys=False), encoding="utf-8")
        case.request["predicate_results"] = []
        state_path = Path(case.temp) / "protected-dispatch-state.yaml"
        initial = DISPATCH.initialize_state(state_path, case.graph, case.authorization, case.run_id)
        claim = dict(self.claim, graph_sha256=case.graph["graph_sha256"],
                     node_id=case.graph["nodes"][0]["node_id"],
                     predecessor_state_sha256=initial["state_sha256"])
        ticket = DISPATCH.acquire_dispatch(state_path, claim)["ticket"]
        if complete:
            DISPATCH.record_success(state_path, {
                "ticket_id": ticket["ticket_id"],
                "dispatch_tool_call_ref": ticket["dispatch_tool_call_ref"],
                "executor_session_ref": ticket["executor_session_ref"],
                "evidence_refs": [case.evidence_ref],
                "evidence_sha256": {case.evidence_ref: case.evidence_hash},
            })
        case.request.pop("event_ledger_result_ref", None)
        return case, state_path, ticket

    def run_completion(self, case, state_path=None, embed=None):
        request = copy.deepcopy(case.request)
        if embed:
            request.update(embed)
        request_path = Path(case.temp) / "dispatch-completion-request.yaml"
        request_path.write_text(yaml.safe_dump(
            {"completion_verification_request": request}, sort_keys=False), encoding="utf-8")
        command = [sys.executable, "-B", str(SCRIPTS / "verify_completion.py"),
                   "--request", str(request_path)]
        if state_path is not None:
            command += ["--dispatch-state", str(state_path)]
        result = subprocess.run(command, capture_output=True, text=True)
        return result, (result.stdout + result.stderr).upper()

    def test_request_embedded_records_ticket_or_snapshot_cannot_self_prove(self):
        case, state_path, ticket = self.completion_fixture(complete=True)
        snapshot = DISPATCH.export_snapshot(state_path)
        completed, output = self.run_completion(case, embed={
            "host_records": snapshot["host_execution_records"],
            "dispatch_ticket": ticket,
            "dispatch_state_snapshot": snapshot,
        })
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("DISPATCH_STATE_REQUIRED", output)

    def test_completion_rejects_incomplete_state_and_ticket_event_mismatch(self):
        incomplete_case, incomplete_state, _ = self.completion_fixture(complete=False)
        incomplete, incomplete_output = self.run_completion(incomplete_case, incomplete_state)
        self.assertNotEqual(incomplete.returncode, 0)
        self.assertIn("DISPATCH_STATE_INCOMPLETE", incomplete_output)

        case, state_path, _ = self.completion_fixture(complete=True)
        case.request["execution_receipt"]["dispatch_tool_call_ref"] = "placeholder-forged-dispatch"
        mismatched, mismatch_output = self.run_completion(case, state_path)
        self.assertNotEqual(mismatched.returncode, 0)
        self.assertIn("DISPATCH_TICKET_MISMATCH", mismatch_output)

    def test_complete_state_exports_host_records_ledger_and_completes(self):
        case, state_path, _ = self.completion_fixture(complete=True)
        snapshot = DISPATCH.export_snapshot(state_path)
        self.assertEqual(snapshot["status"], "COMPLETE")
        self.assertEqual(snapshot["run_event_ledger_result"]["status"], "COMPLETE")
        self.assertEqual(snapshot["host_execution_records"]["events"], snapshot["events"])
        completed, output = self.run_completion(case, state_path)
        self.assertEqual(completed.returncode, 0, output)
        self.assertIn("STATUS: DONE", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
