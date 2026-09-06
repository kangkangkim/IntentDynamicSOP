#!/usr/bin/env python3
"""RED contract for host authorization bound to a canonical v2 Run Graph.

The fixture deliberately exercises the public resolver -> selector -> compiler
path.  It never synthesizes an effective configuration, selection, or graph.
"""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import test_harness as harness  # noqa: E402


AUTHORIZER = ROOT / ".claude/skills/idc-workflow/scripts/authorize_execution.py"


def sha256_bytes(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ExecutionBindingContractTest(unittest.TestCase):
    maxDiff = None

    def build_chain(self, temp):
        config, _pack, assets, rows = harness.write_v2_policy_chain_fixture(temp)
        resolved, runtime = harness.run_team_config_resolver(temp, "binding", config)
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        effective = temp / "binding-effective.yaml"
        selected, selection, selection_path = harness.run_v2_policy_selection(
            temp, "binding", effective, "lite"
        )
        self.assertEqual(selected.returncode, 0, selected.stderr)
        compiled, graph = harness.run_v2_policy_graph(
            temp, "binding", effective, selection_path, "lite"
        )
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        self.assertEqual(graph.get("status"), "READY")
        return {
            "config": config,
            "assets": assets,
            "rows": rows,
            "runtime": runtime,
            "effective": effective,
            "selection": selection,
            "selection_path": selection_path,
            "graph": graph,
            "graph_path": temp / "binding-graph.yaml",
        }

    def write_knowledge_plan(self, temp, unit, domain):
        body = {
            "status": "READY",
            "execution_unit_ref": unit,
            "selected_domain": domain,
        }
        plan_id = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        path = temp / "knowledge-plan.yaml"
        path.write_text(
            yaml.safe_dump({"knowledge_load_plan": {**body, "knowledge_plan_id": plan_id}}),
            encoding="utf-8",
        )
        return path, plan_id

    def request_for(self, temp, chain):
        # The helper's real selector owns this unit identity; the request must
        # consume it rather than construct a parallel selection identity.
        unit = chain["selection"]["execution_unit_ref"]
        knowledge_path, knowledge_id = self.write_knowledge_plan(
            temp, unit, "placeholder_ops"
        )
        confirmation = temp / "confirmed-plan.md"
        confirmation.write_text("<PLACEHOLDER_CONFIRMED_PLAN>\n", encoding="utf-8")
        alignment = temp / "approved-alignment.md"
        alignment.write_text("<PLACEHOLDER_APPROVED_ALIGNMENT>\n", encoding="utf-8")
        delegation = temp / "delegation-contract.md"
        delegation.write_text("<PLACEHOLDER_DELEGATION>\n", encoding="utf-8")
        return {
            "execution_authorization_request": {
                "task_id": "execution-binding-contract",
                "workflow_id": "placeholder_domain_execution",
                "selected_domain": "placeholder_ops",
                "selected_lane": "lite",
                "human_alignment_status": "approved",
                "approved_alignment_ref": str(alignment),
                "execution_unit_ref": unit,
                "context_packet_ref": "<CONTEXT_PACKET_REF>",
                "capability_selection_ref": str(chain["selection_path"]),
                "capability_selection_status": "READY",
                "effective_config_ref": str(chain["effective"]),
                "run_graph_ref": str(chain["graph_path"]),
                "knowledge_load_plan_ref": str(knowledge_path),
                "knowledge_load_plan_status": "READY",
                "knowledge_plan_id": knowledge_id,
                "domain_execution_skill_ref": str(
                    chain["assets"]["domain_execution_skill_ref"]
                ),
                "delegation_contract_ref": str(delegation),
                "main_agent_role": "planning_and_delegation_only",
                "technical_plan_confirmation": {
                    "required": True,
                    "trigger_reason": "lane=lite",
                    "status": "confirmed",
                    "confirmation_ref": str(confirmation),
                },
                "executor": {"kind": "subagent", "agent_id": "binding-executor"},
                "allowed_paths": ["src/placeholder"],
                "expected_outputs": ["<EXECUTION_RECEIPT_REF>"],
            }
        }

    def host_control_for(self, temp, chain, request, name="host-control"):
        body = request["execution_authorization_request"]
        confirmation = Path(body["technical_plan_confirmation"]["confirmation_ref"])
        def bound(path):
            return {"ref": str(Path(path).resolve()), "sha256": sha256_bytes(path)}
        record = {
            "task_id": body["task_id"], "execution_unit_ref": body["execution_unit_ref"],
            "selected_domain": body["selected_domain"], "selected_lane": body["selected_lane"],
            "graph_sha256": chain["graph"]["graph_sha256"],
            "effective_source": {
                **bound(chain["runtime"]["source_ref"]),
                "runtime_dependency_sha256": chain["runtime"]["runtime_dependency_sha256"],
            },
            "capability_selection": bound(chain["selection_path"]),
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
        path = temp / (name + ".yaml")
        path.write_text(yaml.safe_dump({"host_control_record": record}, sort_keys=False), encoding="utf-8")
        return path

    def authorize(self, temp, name, request, control=None):
        request_path = temp / f"{name}-request.yaml"
        output_path = temp / f"{name}-result.yaml"
        request_path.write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")
        command = ["python3", str(AUTHORIZER), "--request", str(request_path), "--output", str(output_path)]
        if control is not None:
            command += ["--host-control-record", str(control)]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        document = yaml.safe_load(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
        return completed, (document or {}).get("execution_authorization_result") or {}

    def test_success_derives_full_graph_identity_nodes_and_required_predicates(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain = self.build_chain(temp)
            request = self.request_for(temp, chain)
            completed, result = self.authorize(temp, "canonical", request, self.host_control_for(temp, chain, request))
            graph = chain["graph"]
            expected_nodes = graph["nodes"]
            expected_skills = [node["skill_ref"] for node in expected_nodes]
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(result.get("status"), "AUTHORIZED")
            self.assertEqual(result.get("run_graph_ref"), str(chain["graph_path"]))
            self.assertEqual(result.get("graph_sha256"), graph["graph_sha256"])
            self.assertEqual(
                result.get("runtime_dependency_sha256"),
                chain["runtime"]["runtime_dependency_sha256"],
            )
            self.assertEqual(result.get("authorized_graph_nodes"), expected_nodes)
            self.assertEqual(result.get("authorized_atomic_skill_refs"), expected_skills)
            self.assertEqual(result.get("required_predicate_ids"), ["placeholder-required-predicate"])
            self.assertIs(result.get("proof_required"), True)

    def test_missing_or_tampered_run_graph_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain = self.build_chain(temp)
            cases = {}
            missing = self.request_for(temp, chain)
            control = self.host_control_for(temp, chain, missing)
            del missing["execution_authorization_request"]["run_graph_ref"]
            cases["missing"] = (missing, control)
            tampered = self.request_for(temp, chain)
            tampered_control = self.host_control_for(temp, chain, tampered, "tampered-control")
            graph_document = yaml.safe_load(chain["graph_path"].read_text(encoding="utf-8"))
            graph_document["run_graph"]["nodes"][0]["skill_id"] = "forged-placeholder-skill"
            chain["graph_path"].write_text(yaml.safe_dump(graph_document), encoding="utf-8")
            cases["tampered"] = (tampered, tampered_control)
            rejected = {}
            for name, (request, control) in cases.items():
                completed, result = self.authorize(temp, name, request, control)
                rejected[name] = {"returncode": completed.returncode, "result": result}
            self.assertTrue(
                all(item["returncode"] != 0 and item["result"].get("status") != "AUTHORIZED"
                    for item in rejected.values()),
                f"Run Graph must be mandatory and canonical: {rejected}",
            )

    def test_old_effective_or_graph_is_rejected_when_source_or_runtime_dependency_drifts(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain = self.build_chain(temp)
            request = self.request_for(temp, chain)
            control = self.host_control_for(temp, chain, request)
            cases = {}
            for name, target in {
                "team-config": chain["config"],
                "capability-policy": chain["assets"]["capability_policy_ref"],
                "skill": Path(chain["rows"][1]["skill_ref"]),
            }.items():
                target.write_text(
                    target.read_text(encoding="utf-8") + "\n# drift-placeholder\n",
                    encoding="utf-8",
                )
                completed, result = self.authorize(temp, name, request, control)
                cases[name] = {"returncode": completed.returncode, "result": result}
            self.assertTrue(
                all(item["returncode"] != 0 and item["result"].get("status") != "AUTHORIZED"
                    for item in cases.values()),
                "authorizer must reject old effective/graph after team source, policy, or Skill byte drift; "
                f"observed={cases}",
            )

    def test_request_cannot_change_lane_or_selected_skill_claims_away_from_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain = self.build_chain(temp)
            lane_drift = self.request_for(temp, chain)
            lane_control = self.host_control_for(temp, chain, lane_drift)
            lane_drift["execution_authorization_request"]["selected_lane"] = "fast"
            lane_completed, lane_result = self.authorize(temp, "lane", lane_drift, lane_control)

            skills_drift = self.request_for(temp, chain)
            skills_control = self.host_control_for(temp, chain, skills_drift, "skills-control")
            selection_document = yaml.safe_load(chain["selection_path"].read_text(encoding="utf-8"))
            selected = selection_document["capability_selection_result"]["selected"]
            selected[0]["capability_id"] = chain["rows"][0]["id"]
            selected[0]["skill_ref"] = chain["rows"][0]["skill_ref"]
            ordered = selection_document["capability_selection_result"]["ordered_execution"]
            ordered[0]["capability_id"] = chain["rows"][0]["id"]
            ordered[0]["skill_ref"] = chain["rows"][0]["skill_ref"]
            chain["selection_path"].write_text(yaml.safe_dump(selection_document), encoding="utf-8")
            skills_completed, skills_result = self.authorize(temp, "skills", skills_drift, skills_control)
            rejected = {
                "lane": {"returncode": lane_completed.returncode, "result": lane_result},
                "skills": {"returncode": skills_completed.returncode, "result": skills_result},
            }
            self.assertTrue(
                all(item["returncode"] != 0 and item["result"].get("status") != "AUTHORIZED"
                    for item in rejected.values()),
                "request lane and selection Skills must exactly match the canonical graph: "
                f"observed={rejected}",
            )

    def test_request_cannot_remove_module_predicates_or_disable_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain = self.build_chain(temp)
            request = self.request_for(temp, chain)
            control = self.host_control_for(temp, chain, request)
            request["execution_authorization_request"].update({
                # These are adversarial claims, never authorization inputs. A
                # caller must not weaken the module's completion contract.
                "required_predicate_ids": [],
                "proof_required": False,
            })
            completed, result = self.authorize(temp, "predicate-downgrade", request, control)
            self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertNotEqual(result.get("status"), "AUTHORIZED")
            self.assertTrue(
                any("PREDICATE" in str(error).upper() or "PROOF" in str(error).upper()
                    for error in result.get("errors") or []),
                f"predicate/proof downgrade must be identified: {result}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
