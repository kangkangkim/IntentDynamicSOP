#!/usr/bin/env python3
"""RED contracts for a v2 Core that consumes Domain Packs generically."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEAM_SCRIPTS = ROOT / ".claude/skills/idc-team-config/scripts"
RESOLVER = TEAM_SCRIPTS / "resolve_team_config.py"
CONTEXT = TEAM_SCRIPTS / "plan_context.py"
KNOWLEDGE = TEAM_SCRIPTS / "plan_knowledge.py"
sys.path.insert(0, str(ROOT / "tests"))
import test_harness as harness  # noqa: E402


class V2CoreIsolationTest(unittest.TestCase):
    def command_run(self, command, directory):
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)

    def test_custom_v2_pipeline_never_uses_d3a_behavior_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            config, _, _, _ = harness.write_v2_policy_chain_fixture(temp)
            resolved, runtime = harness.run_team_config_resolver(temp, "isolation", config)
            effective = temp / "isolation-effective.yaml"
            selected, selection, selection_path = harness.run_v2_policy_selection(
                temp, "isolation", effective, "lite"
            )
            compiled, graph = harness.run_v2_policy_graph(
                temp, "isolation", effective, selection_path, "lite"
            )
            knowledge_demand = temp / "knowledge-demand.yaml"
            knowledge_demand.write_text(yaml.safe_dump({"knowledge_demand": {
                "execution_unit_ref": selection["execution_unit_ref"],
                "selected_domain": "placeholder_ops", "selected_lane": "lite",
                "selected_layer": "PLACEHOLDER_LAYER", "selected_components": [],
                "selected_test_domains": ["PLACEHOLDER_TEST"], "repo_context_required": False,
            }}), encoding="utf-8")
            knowledge_path = temp / "knowledge.yaml"
            knowledge = self.command_run([
                sys.executable, str(KNOWLEDGE), "--effective", str(effective),
                "--demand", str(knowledge_demand), "--output", str(knowledge_path),
            ], temp)
            context = self.command_run([
                sys.executable, str(CONTEXT), "--effective", str(effective),
                "--phase", "execution", "--domain", "placeholder_ops", "--lane", "lite",
                "--selection", str(selection_path), "--knowledge-plan", str(knowledge_path),
            ], temp)
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            self.assertEqual(selected.returncode, 0, selected.stderr)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(knowledge.returncode, 0, knowledge.stderr)
            self.assertIn("status: READY", context.stdout)
            self.assertEqual(graph.get("status"), "READY")
            self.assertEqual(
                harness.find_d3a_runtime_asset_leaks(runtime), [],
                "custom v2 runtime must not materialize or reference D3A assets",
            )

    def test_disabled_missing_d3a_pack_is_ready_and_digest_text_is_not_a_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            pack, _, _ = harness.write_placeholder_domain_pack(temp, "placeholder_ops")
            absent = temp / "d3a-pack-absent.yaml"
            config = harness.write_v2_domain_config(
                temp, ["placeholder_ops"], "placeholder_ops",
                {"placeholder_ops": {"pack_ref": str(pack)}, "d3a": {"pack_ref": str(absent)}},
                "disabled-d3a.yaml",
            )
            completed, runtime = harness.run_team_config_resolver(temp, "disabled-d3a", config)
            # Hash metadata may contain the byte sequence d3a. Only behavior refs
            # and materialized modules count as a D3A runtime leak.
            runtime["runtime_dependency_sha256"] = "00d3a00"
            runtime["runtime_dependency_files"] = {"/placeholder/general.yaml": "11d3a11"}
            leaks = harness.find_d3a_runtime_asset_leaks(runtime)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(runtime.get("status"), "READY")
            self.assertEqual(leaks, [], leaks)

    def test_fixed_architecture_is_a_pack_contract_not_the_literal_d3a_name(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            original = yaml.safe_load((ROOT / ".claude/skills/idc-workflow/references/domains/d3a/domain-pack.yaml").read_text())
            pack = original["domain_pack"]
            pack["id"] = "fixed_placeholder"
            pack["trigger_rules"] = [{"field": "selected_domain", "equals": "fixed_placeholder"}]
            pack["workflow_profile_ref"] = str(ROOT / ".claude/skills/idc-workflow/references/domains/d3a/workflow-profile.yaml")
            pack["capability_policy_ref"] = str(ROOT / ".claude/skills/idc-workflow/references/domains/d3a/capability-policy.yaml")
            pack["completion_predicate_ref"] = str(ROOT / ".claude/skills/idc-workflow/references/domains/d3a/completion-predicate.yaml")
            bad_layers = temp / "bad-layers.yaml"
            bad_layers.write_text(yaml.safe_dump({"layers": [{
                "id": "NOT_FIXED",
                "knowledge_ref": str(ROOT / ".claude/skills/idc-workflow/references/knowledge/general/components/GENERAL_COMPONENT_PLACEHOLDER.md"),
            }]}), encoding="utf-8")
            pack["registries"] = {
                "coding_layers_ref": str(bad_layers),
                "test_domains_ref": str(ROOT / ".claude/skills/idc-workflow/references/registries/dt-domains.yaml"),
            }
            pack["knowledge_root_ref"] = str(ROOT / ".claude/skills/idc-workflow/references/knowledge/d3a")
            pack_path = temp / "fixed-placeholder-pack.yaml"
            pack_path.write_text(yaml.safe_dump({"domain_pack": pack}, sort_keys=False), encoding="utf-8")
            config = harness.write_v2_domain_config(
                temp, ["fixed_placeholder"], "fixed_placeholder",
                {"fixed_placeholder": {"pack_ref": str(pack_path)}}, "fixed-placeholder.yaml",
            )
            completed, runtime = harness.run_team_config_resolver(temp, "fixed-placeholder", config)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "fixed architecture",
                (completed.stderr + yaml.safe_dump(runtime)).lower(),
                "the rejection must come from a generic Pack fixed-architecture validator",
            )

    def test_enabled_missing_d3a_pack_fails_without_loading_its_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            absent = temp / "d3a-pack-absent.yaml"
            config = harness.write_v2_domain_config(
                temp, ["d3a"], "d3a", {"d3a": {"pack_ref": str(absent)}},
                "enabled-missing-d3a.yaml",
            )
            completed, runtime = harness.run_team_config_resolver(temp, "enabled-missing-d3a", config)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(runtime.get("status"), "INVALID")
            self.assertIn("DOMAIN_PACK_MISSING", yaml.safe_dump(runtime))

    def test_official_d3a_pack_keeps_its_fixed_layers_team_tests_and_tran_build(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            team_tests = temp / "team-dt.yaml"
            team_tests.write_text(yaml.safe_dump({"test_domains": [{
                "id": "TEAM_REQUIRED_DT",
                "knowledge_ref": str(ROOT / ".claude/skills/idc-workflow/references/knowledge/general/tests/GENERAL_TEST_PLACEHOLDER.md"),
            }]}), encoding="utf-8")
            pack = ROOT / ".claude/skills/idc-workflow/references/domains/d3a/domain-pack.yaml"
            config = harness.write_v2_domain_config(
                temp, ["d3a"], "d3a", {"d3a": {
                    "pack_ref": str(pack),
                    "registries": {"test_domains_ref": str(team_tests)},
                }}, "official-d3a.yaml",
            )
            completed, runtime = harness.run_team_config_resolver(temp, "official-d3a", config)
            module = runtime.get("domains", {}).get("modules", {}).get("d3a", {})
            layer_rows = yaml.safe_load(Path(module["registries"]["coding_layers_ref"]).read_text())
            completion = yaml.safe_load(Path(module["completion_predicate_ref"]).read_text())
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual([row["id"] for row in layer_rows["layers"]], [
                "TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV",
            ])
            self.assertEqual(
                yaml.safe_load(Path(module["registries"]["test_domains_ref"]).read_text())["test_domains"][0]["id"],
                "TEAM_REQUIRED_DT",
            )
            self.assertIn("tran_build", yaml.safe_dump(completion))

    def test_v2_core_must_not_have_d3a_name_branches_or_request_d3a_completion(self):
        sources = {
            "resolver": (TEAM_SCRIPTS / "resolve_team_config.py").read_text(),
            "context": (TEAM_SCRIPTS / "plan_context.py").read_text(),
            "knowledge": (TEAM_SCRIPTS / "plan_knowledge.py").read_text(),
            "selector": (TEAM_SCRIPTS / "select_capabilities.py").read_text(),
            "authorizer": (ROOT / ".claude/skills/idc-workflow/scripts/authorize_execution.py").read_text(),
            "completion": (TEAM_SCRIPTS / "verify_completion.py").read_text(),
        }
        violations = {
            name: [needle for needle in ['== "d3a"', 'request.get("d3a")', 'd3a_profile'] if needle in text]
            for name, text in sources.items()
        }
        violations = {name: value for name, value in violations.items() if value}
        self.assertEqual(violations, {}, f"v2 Core must derive policy from Pack metadata: {violations}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
