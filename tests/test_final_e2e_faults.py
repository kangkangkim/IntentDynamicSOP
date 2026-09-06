#!/usr/bin/env python3
"""Final RED contracts joining real v2 configuration to host-owned completion."""
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
AUTHORIZER = ROOT / ".claude/skills/idc-workflow/scripts/authorize_execution.py"
sys.path.insert(0, str(ROOT / "tests"))
import test_harness as harness  # noqa: E402


def load_dispatch(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "dispatch_state.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DISPATCH = load_dispatch("final_e2e_dispatch")


def concurrent_claim(arguments):
    state, claim = arguments
    return load_dispatch("final_e2e_worker").acquire_dispatch(state, claim)["status"]


def put(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def host_control(temp, graph, runtime, selection_ref, request):
    body = request["execution_authorization_request"]
    def bound(path):
        return {"ref": str(Path(path).resolve()), "sha256": digest(path)}
    confirmation = body["technical_plan_confirmation"]["confirmation_ref"]
    record = {
        "task_id": body["task_id"], "execution_unit_ref": body["execution_unit_ref"],
        "selected_domain": body["selected_domain"], "selected_lane": body["selected_lane"],
        "graph_sha256": graph["graph_sha256"],
        "effective_source": {**bound(runtime["source_ref"]),
                             "runtime_dependency_sha256": runtime["runtime_dependency_sha256"]},
        "capability_selection": bound(selection_ref),
        "knowledge_load_plan": {**bound(body["knowledge_load_plan_ref"]),
                                  "knowledge_plan_id": body["knowledge_plan_id"]},
        "technical_plan_confirmation": bound(confirmation),
        "approved_alignment": bound(body["approved_alignment_ref"]),
        "delegation": bound(body["delegation_contract_ref"]),
        "executor": copy.deepcopy(body["executor"]),
        "allowed_paths": list(body["allowed_paths"]),
        "expected_outputs": list(body["expected_outputs"]),
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    record["control_id"] = hashlib.sha256(b"host-control-record:" + canonical).hexdigest()
    record["control_sha256"] = hashlib.sha256(canonical).hexdigest()
    return put(temp / "host-control.yaml", {"host_control_record": record})


class FinalE2EFaultTests(unittest.TestCase):
    maxDiff = None

    def command(self, *args):
        return subprocess.run([sys.executable, "-B", *map(str, args)], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)

    def custom_chain(self, temp, lane):
        config, _, assets, _ = harness.write_v2_policy_chain_fixture(temp)
        resolved, runtime = harness.run_team_config_resolver(temp, "chain", config)
        effective = temp / "chain-effective.yaml"
        selected, selection, selection_ref = harness.run_v2_policy_selection(temp, lane, effective, lane)
        compiled, graph = harness.run_v2_policy_graph(temp, lane, effective, selection_ref, lane)
        self.assertEqual((resolved.returncode, selected.returncode, compiled.returncode), (0, 0, 0))
        unit = selection["execution_unit_ref"]
        knowledge_body = {"status": "READY", "execution_unit_ref": unit,
                          "selected_domain": "placeholder_ops"}
        knowledge_id = hashlib.sha256(json.dumps(
            knowledge_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        knowledge_plan = put(temp / "knowledge-plan.yaml", {"knowledge_load_plan": {
            **knowledge_body, "knowledge_plan_id": knowledge_id}})
        confirmation = temp / "confirmed-plan.md"
        confirmation.write_text("<PLACEHOLDER_CONFIRMED_PLAN>\n", encoding="utf-8")
        alignment = temp / "approved-alignment.md"
        alignment.write_text("<PLACEHOLDER_APPROVED_ALIGNMENT>\n", encoding="utf-8")
        delegation = temp / "delegation-contract.md"
        delegation.write_text("<PLACEHOLDER_DELEGATION>\n", encoding="utf-8")
        request = {"execution_authorization_request": {
            "task_id": "final-custom-e2e", "workflow_id": "placeholder_domain_execution",
            "selected_domain": "placeholder_ops", "selected_lane": lane,
            "human_alignment_status": "approved", "approved_alignment_ref": str(alignment),
            "execution_unit_ref": unit, "context_packet_ref": "<CONTEXT_REF>",
            "capability_selection_ref": str(selection_ref), "capability_selection_status": "READY",
            "effective_config_ref": str(effective), "run_graph_ref": str(temp / f"{lane}-graph.yaml"),
            "knowledge_load_plan_ref": str(knowledge_plan), "knowledge_load_plan_status": "READY",
            "knowledge_plan_id": knowledge_id,
            "domain_execution_skill_ref": str(assets["domain_execution_skill_ref"]),
            "delegation_contract_ref": str(delegation), "main_agent_role": "planning_and_delegation_only",
            "technical_plan_confirmation": {"required": True, "trigger_reason": "lane=" + lane,
                "status": "confirmed", "confirmation_ref": str(confirmation)},
            "executor": {"kind": "subagent", "agent_id": "placeholder-executor"},
            "allowed_paths": ["src/placeholder"], "expected_outputs": ["<RECEIPT_REF>"],
        }}
        auth_ref = temp / "authorization.yaml"
        auth_request = put(temp / "authorization-request.yaml", request)
        control = host_control(temp, graph, runtime, selection_ref, request)
        authorized = self.command(AUTHORIZER, "--request", auth_request, "--output", auth_ref,
                                  "--host-control-record", control)
        auth = (yaml.safe_load(auth_ref.read_text()) or {}).get("execution_authorization_result", {})
        self.assertEqual(authorized.returncode, 0,
                         authorized.stdout + authorized.stderr + yaml.safe_dump(auth))
        return runtime, selection_ref, graph, auth_ref, auth, knowledge_id, assets

    def finish(self, temp, lane, selection_ref, graph, auth_ref, auth, knowledge_id, assets):
        evidence = temp / "verification.json"
        evidence.write_text('{"status":"PASS","check":"placeholder"}\n', encoding="utf-8")
        evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
        state = temp / "dispatch-state.yaml"
        snapshot = DISPATCH.initialize_state(state, graph, auth, "final-" + lane)
        for node in graph["nodes"]:
            claim = {"authorization_id": auth["authorization_id"],
                "graph_sha256": graph["graph_sha256"], "node_id": node["node_id"],
                "predecessor_state_sha256": snapshot["state_sha256"],
                "dispatch_tool_call_ref": "placeholder-host-dispatch",
                "executor_session_ref": "placeholder-host-session",
                "idempotency_key": node["node_id"] + "-claim", "downstream_idempotency_supported": True}
            ticket = DISPATCH.acquire_dispatch(state, claim)["ticket"]
            DISPATCH.record_success(state, {"ticket_id": ticket["ticket_id"],
                "dispatch_tool_call_ref": ticket["dispatch_tool_call_ref"],
                "executor_session_ref": ticket["executor_session_ref"], "evidence_refs": [str(evidence)],
                "evidence_sha256": {str(evidence): evidence_hash}})
            snapshot = DISPATCH.export_snapshot(state)
        knowledge_ref = put(temp / "knowledge-result.yaml", {"knowledge_consumption_result": {
            "status": "VERIFIED", "knowledge_plan_id": knowledge_id,
            "execution_unit_ref": auth["execution_unit_ref"]}})
        predicate = {"predicate_id": "placeholder-required-predicate", "required": True,
                     "status": "PASS", "evidence_refs": [str(evidence)]}
        DISPATCH.record_predicate(state, {
            "authorization_id": auth["authorization_id"],
            "graph_sha256": graph["graph_sha256"],
            "predicate_id": predicate["predicate_id"], "status": "PASS",
            "evidence_refs": [str(evidence)],
            "evidence_sha256": {str(evidence): evidence_hash},
        })
        receipt = {"run_id": "final-" + lane, "authorization_id": auth["authorization_id"],
            "graph_sha256": graph["graph_sha256"], "dispatch_tool_call_ref": "placeholder-host-dispatch",
            "executor_session_ref": "placeholder-host-session", "executor_kind": "subagent",
            "loaded_domain_execution_skill_ref": str(assets["domain_execution_skill_ref"]),
            "capability_selection_ref": str(selection_ref),
            "executed_stage_skills": [dict(row, status="succeeded", evidence_refs=[str(evidence)])
                                      for row in auth["authorized_stage_skills"]],
            "executed_atomic_skill_refs": auth["selected_atomic_skill_refs"],
            "knowledge_plan_id": knowledge_id, "knowledge_consumption_result_ref": str(knowledge_ref),
            "changed_paths": ["src/placeholder"], "executed_nodes": graph["nodes"],
            "evidence_refs": [str(evidence)]}
        body = {"execution_unit_ref": auth["execution_unit_ref"], "selected_domain": "placeholder_ops",
            "selected_lane": lane, "authorization_result_ref": str(auth_ref),
            "run_graph_ref": str(temp / f"{lane}-graph.yaml"),
            "knowledge_consumption_result_ref": str(knowledge_ref), "execution_receipt": receipt,
            "predicate_results": [predicate], "evidence": {key: str(evidence) for key in (
                "task_contract_ref", "acceptance_criteria_ref", "focused_plan_ref", "detailed_plan_ref",
                "verification_contract_ref", "relevant_context_refs", "verification_evidence_refs",
                "completion_summary_ref", "task_summary_ref", "changed_files_review_ref",
                "evidence_plan_ref", "audit_or_review_ref")}}
        request_ref = put(temp / "completion.yaml", {"completion_verification_request": body})
        completed = self.command(SCRIPTS / "verify_completion.py", "--request", request_ref,
                                 "--dispatch-state", state)
        return completed, body, state

    def test_custom_domain_three_lanes_reach_done_and_tampering_blocks(self):
        for lane in ("fast", "lite", "complex"):
            with self.subTest(lane=lane), tempfile.TemporaryDirectory() as directory:
                temp = Path(directory)
                _, selection, graph, auth_ref, auth, knowledge, assets = self.custom_chain(temp, lane)
                completed, body, state = self.finish(temp, lane, selection, graph, auth_ref,
                                                     auth, knowledge, assets)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertIn("status: DONE", completed.stdout)
                reordered = copy.deepcopy(body["execution_receipt"]["executed_stage_skills"])
                reordered[0]["execution_order"] = 99
                variants = (body["execution_receipt"]["executed_stage_skills"][:-1], reordered)
                for case, rows in zip(("missing", "reordered"), variants):
                    forged = copy.deepcopy(body)
                    forged["execution_receipt"]["executed_stage_skills"] = rows
                    ref = put(temp / (case + ".yaml"), {"completion_verification_request": forged})
                    rejected = self.command(SCRIPTS / "verify_completion.py", "--request", ref,
                                            "--dispatch-state", state)
                    self.assertNotEqual(rejected.returncode, 0, case + " accepted")

    def test_real_graph_concurrency_and_non_idempotent_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            _, _, graph, _, auth, _, _ = self.custom_chain(temp, "lite")
            state = temp / "concurrent.yaml"
            initial = DISPATCH.initialize_state(state, graph, auth, "concurrent-run")
            claim = {"authorization_id": auth["authorization_id"], "graph_sha256": graph["graph_sha256"],
                "node_id": graph["nodes"][0]["node_id"], "predecessor_state_sha256": initial["state_sha256"],
                "dispatch_tool_call_ref": "placeholder-dispatch", "executor_session_ref": "placeholder-session",
                "idempotency_key": "placeholder-concurrent-key", "downstream_idempotency_supported": True}
            with multiprocessing.get_context("fork").Pool(6) as pool:
                statuses = pool.map(concurrent_claim, [(str(state), claim)] * 6)
            self.assertEqual((statuses.count("ISSUED"), statuses.count("REPLAY")), (1, 5), statuses)
            crash_state = temp / "crash.yaml"
            initial = DISPATCH.initialize_state(crash_state, graph, auth, "crash-run")
            unsafe = dict(claim, predecessor_state_sha256=initial["state_sha256"],
                          downstream_idempotency_supported=False)
            self.assertEqual(DISPATCH.acquire_dispatch(crash_state, unsafe)["status"], "ISSUED")
            self.assertEqual(load_dispatch("after_crash").acquire_dispatch(crash_state, unsafe)["status"],
                             "RECOVERY_REQUIRED")

    def test_official_d3a_team_dt_and_tran_build_gate_reach_done(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            tests = put(temp / "team-dt.yaml", {"test_domains": [
                {"id": name, "knowledge_ref": str(ROOT / "docs/architecture.md")}
                for name in ("TEAM_DT_A", "TEAM_DT_B")]})
            pack = ROOT / ".claude/skills/idc-workflow/references/domains/d3a/domain-pack.yaml"
            config = harness.write_v2_domain_config(temp, ["d3a"], "d3a", {"d3a": {
                "pack_ref": str(pack), "registries": {"test_domains_ref": str(tests)}}}, "d3a.yaml")
            resolved, runtime = harness.run_team_config_resolver(temp, "d3a", config)
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            module = runtime["domains"]["modules"]["d3a"]
            ids = [row["predicate_id"] for row in module["completion_predicates"]]
            self.assertEqual(ids, ["TEAM_DT_A_green", "TEAM_DT_B_green", "tran_build_pass"],
                "D3A_E2E_GAP: materialized completion must bind each effective team DT plus tran_build")

    def test_unknown_v2_config_domain_and_pack_fields_fail_closed(self):
        for case in ("config", "domains", "pack"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                temp = Path(directory)
                config, pack, _, _ = harness.write_v2_policy_chain_fixture(temp)
                document = yaml.safe_load(config.read_text())
                if case == "config":
                    document["future_placeholder"] = {"keep": True}
                elif case == "domains":
                    document["domains"]["future_placeholder"] = {"keep": True}
                else:
                    pack_doc = yaml.safe_load(pack.read_text())
                    pack_doc["domain_pack"]["future_placeholder"] = {"keep": True}
                    put(pack, pack_doc)
                put(config, document)
                completed, runtime = harness.run_team_config_resolver(temp, case, config)
                text = (completed.stdout + completed.stderr + yaml.safe_dump(runtime)).upper()
                self.assertNotEqual(completed.returncode, 0, case + " unknown field was ignored")
                self.assertIn("UNSUPPORTED", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
