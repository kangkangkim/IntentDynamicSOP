"""Executable RED contracts for config-version 2 team policy ownership."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude/skills/idc-team-config/scripts"
RESOLVER = SCRIPTS / "resolve_team_config.py"
sys.path.insert(0, str(SCRIPTS))
from domain_policy_runtime import policy_view  # noqa: E402

SKILL_A = ROOT / ".claude/skills/idc-gc-sop-adapter/SKILL.md"
SKILL_B = ROOT / ".claude/skills/idc-dt-writer/SKILL.md"
COMPONENT_KNOWLEDGE = ROOT / ".claude/skills/idc-workflow/references/knowledge/general/components/GENERAL_COMPONENT_PLACEHOLDER.md"
TEST_KNOWLEDGE = ROOT / ".claude/skills/idc-workflow/references/knowledge/general/tests/GENERAL_TEST_PLACEHOLDER.md"


def write_yaml(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


class V2ConfigOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="idc-v2-ownership-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def profile(self, marker, capability="coding_standard"):
        return {
            "skills": {"allow": [capability], "deny": [], "required": [capability]},
            "orchestration": {
                "mode": "ordered",
                "steps": [{"id": marker, "stage": "planning", "skill_ids": [capability],
                           "trigger_signals": []}],
            },
        }

    def capability(self, **updates):
        row = {
            "id": "coding_standard",
            "skill_ref": str(SKILL_A),
            "allowed_stages": ["planning", "implementation"],
            "eligible_lanes": ["fast", "lite", "complex"],
            "capability_keys": ["implementation_constraints"],
            "trigger_signals": [],
            "execution_profiles": ["lane_driven"],
            "supersedes": [],
        }
        row.update(updates)
        return row

    def build_domain(self, domain_id="sample", lane_policy=None, capabilities=None,
                     workflow_extra=None, policy_extra=None):
        domain = self.work / domain_id
        layers = domain / "layers.yaml"
        tests = domain / "tests.yaml"
        workflow = domain / "workflow.yaml"
        policy = domain / "policy.yaml"
        completion = domain / "completion.yaml"
        pack = domain / "pack.yaml"
        write_yaml(layers, {"layers": [{"id": "COMPONENT_A", "knowledge_ref": str(COMPONENT_KNOWLEDGE)}]})
        write_yaml(tests, {"test_domains": [{"id": "TEST_A", "knowledge_ref": str(TEST_KNOWLEDGE)}]})
        workflow_body = {
            "id": domain_id + "-workflow",
            "execution_profile": "lane_driven",
            "domain_execution_skill_ref": str(SKILL_A),
            "phase_refs": {},
            "lane_profiles": {
                "fast": self.profile("pack-fast"),
                "lite": self.profile("pack-lite"),
                "complex": self.profile("pack-complex"),
            },
        }
        workflow_body.update(workflow_extra or {})
        policy_body = {
            "id": domain_id + "-policy",
            "execution_profile": "lane_driven",
            "lane_applicability": "dynamic",
            "required_contracts": ["task_contract", "verification_contract"],
            "capabilities": capabilities or [self.capability()],
        }
        policy_body.update(policy_extra or {})
        write_yaml(workflow, {"workflow_profile": workflow_body})
        write_yaml(policy, {"capability_policy": policy_body})
        write_yaml(completion, {"completion_predicates": [], "completion_rule": {"operator": "all"}})
        write_yaml(pack, {"domain_pack": {
            "id": domain_id,
            "trigger_rules": [{"field": "selected_domain", "equals": domain_id}],
            "lane_policy": lane_policy or {"mode": "dynamic", "selected_lane": None},
            "workflow_profile_ref": "workflow.yaml",
            "capability_policy_ref": "policy.yaml",
            "completion_predicate_ref": "completion.yaml",
            "registries": {"coding_layers_ref": "layers.yaml", "test_domains_ref": "tests.yaml"},
            "knowledge_root_ref": ".",
        }})
        return pack

    def config(self, domain_id, pack, **sections):
        value = {
            "config_version": 2,
            "team": {"id": "public-v2-ownership", "repo_path": str(ROOT)},
            "domains": {"enabled": [domain_id], "default": domain_id,
                        "definitions": {domain_id: {"pack_ref": str(pack)}}},
        }
        value.update(sections)
        return value

    def resolve(self, config, label="effective"):
        config_path = self.work / (label + "-config.yaml")
        output_path = self.work / (label + ".yaml")
        write_yaml(config_path, config)
        result = subprocess.run(
            [sys.executable, str(RESOLVER), "--config", str(config_path), "--output", str(output_path)],
            cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        effective = yaml.safe_load(output_path.read_text(encoding="utf-8"))
        self.assertEqual(effective["status"], "READY")
        return effective

    def test_explicit_team_lane_profiles_override_only_declared_lanes(self):
        pack = self.build_domain()
        team_fast = self.profile("team-fast")
        effective = self.resolve(self.config(
            "sample", pack,
            lane={"default": "fast", "profiles": {"fast": team_fast}},
        ))
        profiles = effective["domains"]["modules"]["sample"]["lane_profiles"]
        self.assertEqual(profiles["fast"], team_fast)
        self.assertEqual(profiles["lite"]["orchestration"]["steps"][0]["id"], "pack-lite")
        self.assertEqual(profiles["complex"]["orchestration"]["steps"][0]["id"], "pack-complex")

    def test_binding_overrides_executable_capability_and_is_audited(self):
        effective = self.resolve(self.config(
            "sample", self.build_domain(),
            bindings={"coding_standard": {"skill_ref": str(SKILL_B)}},
        ))
        capability = next(row for row in effective["available_capabilities"]
                          if row["id"] == "coding_standard")
        self.assertEqual(capability["skill_ref"], str(SKILL_B))
        audit = effective["registration_audit"]
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(any(row.get("capability_id") == "coding_standard"
                            for row in audit["declared_overrides"]), audit)

    def test_adapter_extensions_are_registered_without_losing_policy(self):
        extension = {
            "id": "idc-public-review", "execution_role": "verification_capability",
            "capability_keys": ["code_review"], "allowed_stages": ["review"],
            "eligible_lanes": ["lite", "complex"], "execution_profiles": ["lane_driven"],
            "trigger_signals": ["review_required"], "skill_ref": str(SKILL_B),
            "input_contract_ref": None, "output_contract_ref": None,
            "evidence_required": True, "requires": ["task_contract"], "blocks_when": [],
            "composes_with": ["coding_standard"], "supersedes": [],
        }
        effective = self.resolve(self.config("sample", self.build_domain(), adapter_extensions=[extension]))
        self.assertEqual(effective["adapter_extensions"], [extension])
        registered = next(row for row in effective["available_capabilities"]
                          if row["id"] == extension["id"])
        for key, value in extension.items():
            self.assertEqual(registered.get(key), value, key)

    def test_explicit_alignment_is_resolved_instead_of_replaced_by_framework_default(self):
        alignment = copy.deepcopy(yaml.safe_load((ROOT / "team-config.yaml.template").read_text())["alignment"])
        alignment["bindings"]["brainstorming"]["skill_ref"] = str(SKILL_A)
        effective = self.resolve(self.config("sample", self.build_domain(), alignment=alignment))
        self.assertEqual(effective["alignment"]["bindings"]["brainstorming"]["skill_ref"], str(SKILL_A))
        self.assertEqual(effective["alignment"]["orchestration"], alignment["orchestration"])

    def test_explicit_alignment_must_cover_maturity_signals_in_clarification_stage(self):
        pack = self.build_domain()
        baseline = copy.deepcopy(
            yaml.safe_load((ROOT / "team-config.yaml.template").read_text())["alignment"]
        )
        for mandatory_signal in ["structured_requirement_input", "tr3_input"]:
            alignment = copy.deepcopy(baseline)
            for step in alignment["orchestration"]["steps"]:
                step["trigger_signals"] = [
                    signal
                    for signal in step["trigger_signals"]
                    if signal != mandatory_signal
                ]
            config_path = self.work / (mandatory_signal + "-missing-config.yaml")
            output_path = self.work / (mandatory_signal + "-missing-effective.yaml")
            write_yaml(config_path, self.config("sample", pack, alignment=alignment))
            result = subprocess.run(
                [sys.executable, str(RESOLVER), "--config", str(config_path), "--output", str(output_path)],
                cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                capture_output=True, text=True, timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(mandatory_signal, result.stderr)
            self.assertIn("clarification", result.stderr)
            self.assertIn("NEEDS_TEAM_CONFIG", result.stderr)

    def test_capability_metadata_survives_policy_materialization(self):
        metadata = {
            "execution_role": "atomic_capability", "evidence_required": True,
            "requires": ["api_contract"], "blocks_when": ["contract_missing"],
            "composes_with": ["idc-public-helper"],
        }
        effective = self.resolve(self.config(
            "sample", self.build_domain(capabilities=[self.capability(**metadata)]),
        ))
        capability = effective["available_capabilities"][0]
        for key, value in metadata.items():
            self.assertEqual(capability.get(key), value, key)

    def test_d3a_test_registry_replaces_defaults_but_coding_layers_remain_fixed(self):
        replacement = self.work / "d3a-tests.yaml"
        write_yaml(replacement, {"test_domains": [
            {"id": "TEAM_DT_A", "knowledge_ref": str(TEST_KNOWLEDGE)},
            {"id": "TEAM_DT_B", "knowledge_ref": str(COMPONENT_KNOWLEDGE)},
        ]})
        config = self.config(
            "d3a", ROOT / ".claude/skills/idc-workflow/references/domains/d3a/domain-pack.yaml",
        )
        config["domains"]["definitions"]["d3a"]["registries"] = {
            "test_domains_ref": str(replacement),
        }
        effective = self.resolve(config)
        module = effective["domains"]["modules"]["d3a"]
        layer_rows = yaml.safe_load(Path(module["registries"]["coding_layers_ref"]).read_text())["layers"]
        test_doc = yaml.safe_load(Path(module["registries"]["test_domains_ref"]).read_text())
        test_rows = test_doc.get("test_domains", test_doc.get("domains"))
        self.assertEqual([row["id"] for row in layer_rows],
                         ["TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV"])
        self.assertEqual([row["id"] for row in test_rows], ["TEAM_DT_A", "TEAM_DT_B"])

    def test_custom_contract_and_skill_projection_is_complete(self):
        workflow_extra = {"planner_skill_ref": str(SKILL_B)}
        policy_extra = {"required_contracts": ["task_contract", "verification_contract", "api_contract"]}
        pack = self.build_domain("payments", workflow_extra=workflow_extra, policy_extra=policy_extra)
        completion = self.work / "payments/completion.yaml"
        write_yaml(completion, {
            "completion_skill_ref": str(SKILL_B),
            "completion_predicates": [], "completion_rule": {"operator": "all"},
        })
        effective = self.resolve(self.config("payments", pack))
        module = effective["domains"]["modules"]["payments"]
        self.assertEqual(module["required_contracts"], policy_extra["required_contracts"])
        self.assertEqual(module["workflow_skill_ref"], str(SKILL_A))
        self.assertEqual(module["planner_skill_ref"], str(SKILL_B))
        self.assertEqual(module["completion_skill_ref"], str(SKILL_B))

    def test_dynamic_and_fixed_lane_policies_are_enforced(self):
        dynamic = self.resolve(self.config("dynamic_sample", self.build_domain("dynamic_sample")), "dynamic")
        self.assertEqual(policy_view(dynamic, "dynamic_sample", "lite")["lane"]["default"], "lite")
        with self.assertRaisesRegex(ValueError, "LANE_MISMATCH"):
            policy_view(dynamic, "dynamic_sample", None)

        fixed_pack = self.build_domain(
            "fixed_sample", {"mode": "fixed", "selected_lane": "lite"},
            policy_extra={"lane_applicability": "fixed"},
        )
        fixed = self.resolve(self.config("fixed_sample", fixed_pack), "fixed")
        policy_view(fixed, "fixed_sample", "lite")
        with self.assertRaisesRegex(ValueError, "LANE_MISMATCH"):
            policy_view(fixed, "fixed_sample", "complex")


if __name__ == "__main__":
    unittest.main(verbosity=2)
