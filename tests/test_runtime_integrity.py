#!/usr/bin/env python3
"""Strict runtime contract: compiled graphs cannot opt out of verification.

Host boundary: process(graph, request, host_records=None) receives records from
the host, not the request. Completion receives the same store through the
host-only --host-records PATH argument. The fixture models that trusted input;
it does NOT claim that a local YAML file or a hash is a platform signature.
Production adapters must keep this input outside executor/request control.

host_execution_records binds run/authorization/graph identities, exact events,
and predicate results with content hashes for their evidence_refs. Missing or
nonmatching records must fail closed. Authorization owns required_predicate_ids.
The compatibility calls below expose existing vulnerabilities before the new
injection API exists; they never skip a test or manufacture a successful result.
"""

import copy
import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude/skills/idc-team-config/scripts"


def load_runtime(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load_runtime("compile_run_graph")
LEDGER = load_runtime("run_event_ledger")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode()


class RuntimeIntegrityTests(unittest.TestCase):
    def put(self, name, payload):
        path = self.temp / name
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return str(path)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)
        self.unit = "placeholder-integrity-unit"
        self.run_id = "placeholder-run"
        self.auth_id = "placeholder-authorization"
        self.skill = str(ROOT / ".claude/skills/idc-gc-sop-adapter/SKILL.md")
        self.domain_skill = str(ROOT / ".claude/skills/idc-general-coding/SKILL.md")
        steps = [{"id": "placeholder-step", "stage": "implementation",
                  "skill_ids": ["placeholder-coding"], "trigger_signals": []}]
        config = {"lane": {"profiles": {"lite": {
            "orchestration": {"mode": "ordered", "steps": steps}}}}}
        source = self.put("placeholder-config.yaml", config)
        effective = dict(config, source_ref=source,
                         source_sha256=digest(Path(source).read_bytes()),
                         domains={"modules": {"general": {}}},
                         available_capabilities=[{
                             "id": "placeholder-coding", "skill_ref": self.skill,
                             "allowed_stages": ["implementation"],
                             "eligible_lanes": ["lite"], "capability_keys": [],
                             "trigger_signals": []}])
        effective_ref = self.put("effective.yaml", effective)
        demand_ref = self.put("demand.yaml", {"selected_domain": "general",
            "selected_lane": "lite", "selected_stage": "implementation",
            "lane_applicability": "applicable", "observed_signals": [],
            "execution_unit_ref": self.unit})
        selected = subprocess.run([sys.executable, "-B",
            str(SCRIPTS / "select_capabilities.py"), "--effective", effective_ref,
            "--demand", demand_ref], capture_output=True, text=True)
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.selection = yaml.safe_load(selected.stdout)["capability_selection_result"]
        self.graph = COMPILER.compile_graph(effective, self.selection, {
            "selected_domain": "general", "selected_lane": "lite",
            "observed_signals": []})
        self.assertEqual(self.graph["status"], "READY", self.graph)
        body = {k: v for k, v in self.graph.items()
                if k not in ("graph_id", "graph_sha256")}
        self.assertEqual(self.graph["graph_sha256"], digest(canonical(body)))
        self.graph_ref = self.put("graph.yaml", {"run_graph": self.graph})
        self.selection_ref = self.put("selection.yaml", {
            "capability_selection_result": self.selection})
        evidence = self.temp / "placeholder-verification.json"
        evidence.write_text('{"status":"PASS","check":"placeholder"}\n')
        self.evidence_ref = str(evidence)
        self.evidence_hash = digest(evidence.read_bytes())
        self.events = []
        for node in self.graph["nodes"]:
            for kind in ("NODE_DISPATCHED", "NODE_SUCCEEDED"):
                self.events.append({"idempotency_key": node["node_id"] + kind,
                    "node_id": node["node_id"], "event_type": kind,
                    "dispatch_tool_call_ref": "placeholder-host-dispatch",
                    "executor_session_ref": "placeholder-host-session",
                    "evidence_refs": [self.evidence_ref] if kind == "NODE_SUCCEEDED" else []})
        self.predicate = {"predicate_id": "placeholder-required", "required": True,
                          "status": "PASS", "evidence_refs": [self.evidence_ref]}
        self.host = {"run_id": self.run_id, "authorization_id": self.auth_id,
                     "graph_sha256": self.graph["graph_sha256"],
                     "events": copy.deepcopy(self.events),
                     "predicate_results": [copy.deepcopy(self.predicate)],
                     "evidence_sha256": {self.evidence_ref: self.evidence_hash}}
        self.host_ref = self.put("host-records.yaml", {"host_execution_records": self.host})
        self.ledger_request = {"run_id": self.run_id,
            "authorization_id": self.auth_id, "graph_sha256": self.graph["graph_sha256"],
            "events": copy.deepcopy(self.events)}
        self.knowledge_ref = self.put("knowledge.yaml", {"knowledge_consumption_result": {
            "status": "VERIFIED", "knowledge_plan_id": "placeholder-knowledge",
            "execution_unit_ref": self.unit}})
        self.authorization = {"status": "AUTHORIZED", "authorization_id": self.auth_id,
            "execution_unit_ref": self.unit, "selected_domain": "general",
            "selected_lane": "lite", "executor_kind": "subagent",
            "domain_execution_skill_ref": self.domain_skill,
            "capability_selection_ref": self.selection_ref,
            "capability_config_identity": self.selection["config_identity"],
            "authorized_stage_skills": self.selection["ordered_execution"],
            "selected_atomic_skill_refs": [self.skill],
            "knowledge_plan_id": "placeholder-knowledge", "run_graph_ref": self.graph_ref,
            "graph_sha256": self.graph["graph_sha256"],
            "required_predicate_ids": ["placeholder-required"],
            "allowed_paths": ["src/placeholder"]}
        self.authorization_ref = self.put("authorization.yaml", {
            "execution_authorization_result": self.authorization})
        self.receipt = {"run_id": self.run_id, "authorization_id": self.auth_id,
            "graph_sha256": self.graph["graph_sha256"],
            "dispatch_tool_call_ref": "placeholder-host-dispatch",
            "executor_session_ref": "placeholder-host-session", "executor_kind": "subagent",
            "loaded_domain_execution_skill_ref": self.domain_skill,
            "capability_selection_ref": self.selection_ref,
            "executed_stage_skills": [dict(item, status="succeeded",
                evidence_refs=[self.evidence_ref]) for item in self.selection["ordered_execution"]],
            "executed_atomic_skill_refs": [self.skill],
            "knowledge_plan_id": "placeholder-knowledge",
            "knowledge_consumption_result_ref": self.knowledge_ref,
            "changed_paths": ["src/placeholder"], "executed_nodes": self.graph["nodes"],
            "evidence_refs": [self.evidence_ref]}
        self.request = {"execution_unit_ref": self.unit, "selected_domain": "general",
            "selected_lane": "lite", "authorization_result_ref": self.authorization_ref,
            "run_graph_ref": self.graph_ref, "knowledge_consumption_result_ref": self.knowledge_ref,
            "execution_receipt": self.receipt, "predicate_results": [self.predicate],
            "evidence": {key: self.evidence_ref for key in (
                "task_contract_ref", "acceptance_criteria_ref", "focused_plan_ref",
                "relevant_context_refs", "verification_evidence_refs", "completion_summary_ref")}}

    def replay(self, request=None, host=True, graph=None):
        kwargs = {}
        if "host_records" in inspect.signature(LEDGER.process).parameters:
            kwargs["host_records"] = self.host if host else None
        return LEDGER.process(graph or self.graph, request or self.ledger_request, **kwargs)

    def complete(self, ledger=None, include_ledger=True, host=True):
        if include_ledger:
            result = self.replay() if ledger is None else ledger
            self.request["event_ledger_result_ref"] = self.put("ledger.yaml", {
                "run_event_ledger_result": result})
        else:
            self.request.pop("event_ledger_result_ref", None)
        self.put("graph.yaml", {"run_graph": self.graph})
        request_ref = self.put("request.yaml", {"completion_verification_request": self.request})
        command = [sys.executable, "-B", str(SCRIPTS / "verify_completion.py")]
        help_result = subprocess.run(command + ["--help"], capture_output=True, text=True)
        command += ["--request", request_ref]
        if host and "--host-records" in help_result.stdout:
            command += ["--host-records", self.host_ref]
        result = subprocess.run(command, capture_output=True, text=True)
        document = yaml.safe_load(result.stdout) or {}
        body = document.get("completion_result") or document.get("completion_verification_result")
        self.assertIsInstance(body, dict, result.stderr)
        return result.returncode, body

    def assert_blocked(self, result, diagnostic):
        code, body = result
        self.assertNotEqual(code, 0, "forged input was accepted: " + str(body))
        self.assertNotEqual(body["status"], "DONE")
        self.assertIn(diagnostic, str(body.get("errors", [])).upper())

    def assert_invalid_ledger(self, result, diagnostic):
        self.assertEqual(result["status"], "INVALID", result)
        self.assertIn(diagnostic, str(result["errors"]).upper())

    def test_real_compile_ledger_completion_positive(self):
        ledger = self.replay()
        self.assertEqual(ledger["status"], "COMPLETE", ledger)
        code, result = self.complete(ledger)
        self.assertEqual((code, result["status"]), (0, "DONE"), result)

    def test_graph_content_hash_tamper_rejected_by_ledger(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"][0]["skill_ref"] = "<POST_AUTH_CHANGED_SKILL_REF>"
        self.assert_invalid_ledger(self.replay(graph=graph), "GRAPH")

    def test_graph_content_hash_tamper_rejected_by_completion(self):
        ledger = self.replay()
        self.graph["nodes"][0]["required"] = False
        self.assert_blocked(self.complete(ledger), "GRAPH")

    def test_compiled_graph_cannot_omit_ledger_or_disable_strictness(self):
        self.request.update({"strict": False, "verify_ledger": False})
        self.assert_blocked(self.complete(include_ledger=False), "LEDGER")

    def test_empty_events_cannot_forge_complete(self):
        ledger = self.replay()
        ledger.update(events=[], applied_event_count=0)
        ledger["proof"]["event_count"] = 0
        self.assert_blocked(self.complete(ledger), "LEDGER")

    def test_unresolved_ledger_errors_block_completion(self):
        ledger = self.replay()
        ledger["errors"] = [{"code": "PLACEHOLDER_UNRESOLVED_FAILURE"}]
        self.assert_blocked(self.complete(ledger), "LEDGER")

    def test_completion_recomputes_proof_hash(self):
        ledger = self.replay()
        ledger["proof"]["state_sha256"] = "0" * 64
        self.assert_blocked(self.complete(ledger), "HASH")

    def test_completion_replays_persisted_event_chain(self):
        ledger = self.replay()
        ledger["events"][0]["executor_session_ref"] = "placeholder-tampered-session"
        self.assert_blocked(self.complete(ledger), "HASH")

    def test_success_must_bind_original_dispatch_session(self):
        request = copy.deepcopy(self.ledger_request)
        request["events"][1]["executor_session_ref"] = "placeholder-other-session"
        self.assert_invalid_ledger(self.replay(request), "ATTESTATION")

    def test_request_strings_cannot_replace_trusted_host_records(self):
        request = copy.deepcopy(self.ledger_request)
        request["host_records"] = self.host
        request["host_records_ref"] = self.host_ref
        self.assert_invalid_ledger(self.replay(request, host=False), "ATTESTATION")

    def test_completion_requires_independent_host_records(self):
        self.request["host_records_ref"] = self.host_ref
        self.assert_blocked(self.complete(host=False), "ATTESTATION")

    def test_authorized_required_predicate_cannot_be_omitted(self):
        self.request["required_predicate_ids"] = []
        self.request["predicate_results"] = []
        self.assert_blocked(self.complete(), "PREDICATE")

    def test_authorized_required_predicate_cannot_be_downgraded(self):
        self.predicate.update(required=False, status="SKIPPED", evidence_refs=[])
        self.assert_blocked(self.complete(), "PREDICATE")

    def test_pass_without_predicate_evidence_is_rejected(self):
        self.predicate.update(required=False, evidence_refs=[])
        self.request["required_predicate_ids"] = ["placeholder-required"]
        self.assert_blocked(self.complete(), "PREDICATE")

    def test_changed_evidence_bytes_cannot_keep_predicate_pass(self):
        ledger = self.replay()
        Path(self.evidence_ref).write_text('{"status":"FAIL","check":"placeholder"}\n')
        self.assert_blocked(self.complete(ledger), "EVIDENCE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
