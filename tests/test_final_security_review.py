#!/usr/bin/env python3
"""RED security contracts from the independent final architecture review."""

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
import test_execution_binding as binding  # noqa: E402


AUTHORIZER = ROOT / ".claude/skills/idc-workflow/scripts/authorize_execution.py"
MIGRATOR = ROOT / ".claude/skills/idc-team-config/scripts/migrate_team_config.py"
RESOLVER = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.py"
LAYERS = ["TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_yaml(path, data):
    Path(path).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def seal_control(document):
    record = document["host_control_record"]
    record.pop("control_id", None)
    record.pop("control_sha256", None)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    record["control_id"] = hashlib.sha256(b"host-control-record:" + canonical).hexdigest()
    record["control_sha256"] = hashlib.sha256(canonical).hexdigest()


class FinalSecurityReviewTests(unittest.TestCase):
    maxDiff = None

    def build_chain(self, temp):
        # Reuse the public resolver -> selector -> compiler fixture; none of its
        # intermediate effective/selection/graph artifacts are synthesized here.
        helper = binding.ExecutionBindingContractTest()
        chain = helper.build_chain(temp)
        request = helper.request_for(temp, chain)
        body = request["execution_authorization_request"]
        for key, text in {
            "approved_alignment_ref": "<PLACEHOLDER_APPROVED_ALIGNMENT>\n",
            "delegation_contract_ref": "<PLACEHOLDER_DELEGATION>\n",
        }.items():
            path = temp / (key + ".txt")
            path.write_text(text, encoding="utf-8")
            body[key] = str(path)
        return chain, request

    def host_control(self, temp, chain, request):
        body = request["execution_authorization_request"]
        confirmation = Path(body["technical_plan_confirmation"]["confirmation_ref"])
        alignment, delegation = Path(body["approved_alignment_ref"]), Path(body["delegation_contract_ref"])
        record = {
            "host_control_record": {
                "task_id": body["task_id"],
                "execution_unit_ref": body["execution_unit_ref"],
                "selected_domain": body["selected_domain"],
                "selected_lane": body["selected_lane"],
                "graph_sha256": chain["graph"]["graph_sha256"],
                "effective_source": {
                    "ref": chain["runtime"]["source_ref"],
                    "sha256": chain["runtime"]["source_sha256"],
                    "runtime_dependency_sha256": chain["runtime"]["runtime_dependency_sha256"],
                },
                "capability_selection": {
                    "ref": str(chain["selection_path"]), "sha256": digest(chain["selection_path"]),
                },
                "knowledge_load_plan": {
                    "ref": str(Path(body["knowledge_load_plan_ref"]).resolve()),
                    "sha256": digest(body["knowledge_load_plan_ref"]),
                    "knowledge_plan_id": body["knowledge_plan_id"],
                },
                "technical_plan_confirmation": {"ref": str(confirmation), "sha256": digest(confirmation)},
                "approved_alignment": {"ref": str(alignment), "sha256": digest(alignment)},
                "delegation": {"ref": str(delegation), "sha256": digest(delegation)},
                "executor": copy.deepcopy(body["executor"]),
                "allowed_paths": list(body["allowed_paths"]),
                "expected_outputs": list(body["expected_outputs"]),
            }
        }
        seal_control(record)
        path = temp / "host-control.yaml"
        write_yaml(path, record)
        return path, record

    def authorize(self, temp, name, request, control=None):
        request_path, output_path = temp / (name + "-request.yaml"), temp / (name + "-result.yaml")
        write_yaml(request_path, request)
        command = ["python3", str(AUTHORIZER), "--request", str(request_path), "--output", str(output_path)]
        if control is not None:
            command += ["--host-control-record", str(control)]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        document = yaml.safe_load(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
        return completed, (document or {}).get("execution_authorization_result") or {}

    def test_root_v1_d3a_preview_materializes_fixed_pack_and_team_predicates(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "root-v1.yaml"
            source.write_bytes((ROOT / "team-config.yaml").read_bytes())
            preview = subprocess.run(
                ["python3", str(MIGRATOR), "--config", str(source), "--preview"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            document = yaml.safe_load(preview.stdout)["migration_preview"]
            bundle = temp / "candidate"
            for asset in document["assets"]:
                target = bundle / asset["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(asset["content"], encoding="utf-8")
            candidate = bundle / "team-config.yaml"
            write_yaml(candidate, document["candidate_config"])
            output = temp / "effective.yaml"
            resolved = subprocess.run(
                ["python3", str(RESOLVER), "--config", str(candidate), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            resolved_document = yaml.safe_load(output.read_text(encoding="utf-8")) or {}
            runtime = resolved_document.get("effective_runtime") or resolved_document
            module = runtime["domains"]["modules"]["d3a"]
            fixed = module.get("fixed_architecture") or {}
            self.assertEqual(fixed.get("coding_layer_ids"), LAYERS)
            self.assertEqual(fixed.get("lane_mode"), "not_applicable")
            self.assertEqual(
                [item["predicate_id"] for item in module.get("completion_predicates") or []],
                ["TEAM_DT_A_green", "TEAM_DT_B_green", "tran_build_pass"],
            )

    def test_real_graph_cannot_self_authorize_without_host_control(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain, request = self.build_chain(temp)
            request["execution_authorization_request"]["host_control"] = {
                "status": "approved", "graph_sha256": chain["graph"]["graph_sha256"],
            }
            completed, result = self.authorize(temp, "forged-self-control", request)
            self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertNotEqual(result.get("status"), "AUTHORIZED", result)
            self.assertIn("HOST_CONTROL", " ".join(result.get("errors") or []).upper())

    def test_host_control_binds_real_graph_and_rejects_missing_tampered_or_expanded_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain, request = self.build_chain(temp)
            control_path, control = self.host_control(temp, chain, request)
            valid, valid_result = self.authorize(temp, "valid", request, control_path)
            with self.subTest("valid independent host control"):
                self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
                self.assertEqual(valid_result.get("status"), "AUTHORIZED", valid_result)

            bad_controls = {"missing": copy.deepcopy(control), "tampered": copy.deepcopy(control)}
            del bad_controls["missing"]["host_control_record"]["knowledge_load_plan"]["knowledge_plan_id"]
            bad_controls["tampered"]["host_control_record"]["effective_source"]["sha256"] = "0" * 64
            for name, record in bad_controls.items():
                seal_control(record)
                path = temp / (name + "-host-control.yaml")
                write_yaml(path, record)
                completed, result = self.authorize(temp, name, request, path)
                with self.subTest(name):
                    self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                    self.assertNotEqual(result.get("status"), "AUTHORIZED", result)

            expanded = copy.deepcopy(request)
            expanded["execution_authorization_request"]["allowed_paths"].append("src/expanded-placeholder")
            completed, result = self.authorize(temp, "expanded", expanded, control_path)
            with self.subTest("request cannot expand host-approved paths"):
                self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertNotEqual(result.get("status"), "AUTHORIZED", result)

    def test_v2_team_nested_unknown_field_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            config, _pack, _assets, _rows = harness.write_v2_policy_chain_fixture(temp)
            document = yaml.safe_load(config.read_text(encoding="utf-8"))
            document["team"]["future_nested_placeholder"] = {"enabled": True}
            write_yaml(config, document)
            completed, runtime = harness.run_team_config_resolver(temp, "nested-unknown", config)
            self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(runtime.get("status"), "INVALID", runtime)
            self.assertIn("UNSUPPORTED", completed.stdout.upper() + completed.stderr.upper())

    def test_recursive_canonicalization_ignores_nested_mapping_order_under_same_host_control(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            chain, first = self.build_chain(temp)
            second = copy.deepcopy(first)
            original = second["execution_authorization_request"]["technical_plan_confirmation"]
            second["execution_authorization_request"]["technical_plan_confirmation"] = {
                key: original[key] for key in reversed(list(original))
            }
            control_path, _control = self.host_control(temp, chain, first)
            one, one_result = self.authorize(temp, "first-order", first, control_path)
            two, two_result = self.authorize(temp, "second-order", second, control_path)
            self.assertEqual(one.returncode, 0, one.stdout + one.stderr)
            self.assertEqual(two.returncode, 0, two.stdout + two.stderr)
            self.assertEqual(one_result.get("status"), "AUTHORIZED", one_result)
            self.assertEqual(two_result.get("status"), "AUTHORIZED", two_result)
            self.assertEqual(one_result.get("authorization_id"), two_result.get("authorization_id"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
