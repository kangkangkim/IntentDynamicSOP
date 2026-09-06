"""Preview-only v1 migration acceptance contract; no production writes allowed."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude/skills/idc-team-config/scripts"
MIGRATOR = SCRIPTS / "migrate_team_config.py"
RESOLVER = SCRIPTS / "resolve_team_config.py"


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            path.is_dir(), path.stat().st_mtime_ns,
            digest(path.read_bytes()) if path.is_file() else None,
        )
        for path in root.rglob("*")
    }


class TeamConfigMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="idc-migration-test-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def write_config(self, config):
        path = self.work / "source.yaml"
        path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        return path

    def run_tool(self, script, *args):
        return subprocess.run(
            [sys.executable, str(script), *map(str, args)], cwd=ROOT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            capture_output=True, text=True, timeout=60,
        )

    def preview(self, path, expected="READY"):
        self.assertTrue(
            MIGRATOR.is_file(),
            "RED: preview-only migrate_team_config.py capability is missing",
        )
        result = self.run_tool(MIGRATOR, "--config", path, "--preview")
        self.assertIn(result.returncode, (0, 1, 2, 3), result.stderr)
        document = yaml.safe_load(result.stdout)
        self.assertIsInstance(document, dict, result.stderr)
        preview = document["migration_preview"]
        self.assertEqual(preview["status"], expected, result.stdout)
        self.assertEqual(preview["source_version"], 1)
        self.assertEqual(preview["target_version"], 2)
        self.assertEqual(preview["source_sha256"], digest(path.read_bytes()))
        # source_config is lossless archival data, never a runtime owner.
        self.assertEqual(preview["source_config"], load(path))
        for key in ("dependency_sha256", "bundle_sha256"):
            self.assertRegex(preview[key], r"^[0-9a-f]{64}$")
        self.assertIsInstance(preview["field_dispositions"], list)
        self.assertIsInstance(preview["diagnostics"], list)
        if expected == "READY":
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(preview["validation"]["resolver"], "PASS")
            self.assertEqual(preview["validation"]["semantic_parity"], "PASS")
            self.assertNotIn("domain", preview["candidate_config"])
            self.assertNotIn("source_config", preview["candidate_config"])
        else:
            self.assertNotEqual(result.returncode, 0)
        return preview, result.stdout

    def resolve(self, config_path, name):
        output = self.work / (name + "-effective.yaml")
        result = self.run_tool(RESOLVER, "--config", config_path, "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        effective = load(output)
        self.assertEqual(effective.get("status", effective["readiness"]["status"]), "READY")
        return effective

    def materialize_and_resolve(self, preview):
        bundle = self.work / "candidate-bundle"
        bundle.mkdir()
        seen = set()
        for asset in preview["assets"]:
            path = Path(asset["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertNotIn(str(path), seen)
            seen.add(str(path))
            self.assertEqual(asset["sha256"], digest(asset["content"].encode("utf-8")))
            target = bundle / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(asset["content"], encoding="utf-8")
        config_path = bundle / "team-config.yaml"
        self.assertNotIn("team-config.yaml", seen)
        config_path.write_text(
            yaml.safe_dump(preview["candidate_config"], sort_keys=False), encoding="utf-8",
        )
        return self.resolve(config_path, "candidate")

    def registry_rows(self, module, kind):
        for key in ({"layers": ("coding_layers", "components"),
                     "tests": ("test_domains",)}[kind]):
            if key in module:
                return module[key]
        ref_key = "coding_layers_ref" if kind == "layers" else "test_domains_ref"
        registry = load(module["registries"][ref_key])
        keys = ("layers", "coding_layers", "components") if kind == "layers" else (
            "domains", "test_domains",
        )
        for key in keys:
            if key in registry:
                rows = copy.deepcopy(registry[key])
                for row in rows:
                    ref = row.get("knowledge_ref") or row.get("knowledge_file")
                    if ref and not Path(ref).is_absolute():
                        # Assets must preserve the actual original knowledge target.
                        row["knowledge_ref"] = str((Path(module["registries"][ref_key]).parent / ref).resolve())
                    row.pop("knowledge_file", None)
                return rows
        self.fail("Candidate registry has no supported row collection")

    def assert_common_semantics(self, before, after):
        for key in ("bindings", "adapter_extensions", "alignment", "lane", "knowledge",
                    "capability_selection", "self_optimization"):
            self.assertEqual(after[key], before[key], "Effective semantic drift: " + key)
        # Compare behavior-bearing columns, not incidental v1/v2 audit metadata.
        keys = ("id", "capability_id", "capability_keys", "allowed_stages", "eligible_lanes",
                "execution_profiles", "trigger_signals", "skill_ref", "requires",
                "blocks_when", "composes_with", "supersedes", "evidence_required")
        list_keys = set(keys) - {"id", "capability_id", "skill_ref", "evidence_required"}
        def capabilities(effective):
            return sorted(
                [{key: (row.get(key) or [] if key in list_keys else row.get(key)) for key in keys}
                 for row in effective["available_capabilities"]],
                key=lambda row: json.dumps(row, sort_keys=True),
            )
        self.assertEqual(capabilities(after), capabilities(before))

    def test_preview_is_deterministic_and_has_no_source_directory_side_effects(self):
        source = self.write_config(load(ROOT / "examples/team-config.minimal.yaml"))
        before = snapshot(self.work)
        preview, first = self.preview(source)
        _, second = self.preview(source)
        self.assertEqual(first, second)
        self.assertEqual(snapshot(self.work), before)
        self.assertEqual(preview["candidate_config"]["config_version"], 2)
        self.assertEqual(preview["candidate_config"]["domains"]["enabled"], ["general"])
        self.materialize_and_resolve(preview)

    def test_root_dual_domain_overrides_and_execution_policy_keep_runtime_semantics(self):
        root_path = ROOT / "team-config.yaml"
        original_bytes, original_mtime = root_path.read_bytes(), root_path.stat().st_mtime_ns
        config = load(root_path)
        self.assertEqual(config["config_version"], 1)
        # Exercise explicit alignment as well as the real root policy fields.
        config["alignment"] = load(ROOT / "team-config.yaml.template")["alignment"]
        source = self.write_config(config)
        preview, _ = self.preview(source)
        old = self.resolve(source, "legacy")
        new = self.materialize_and_resolve(preview)
        self.assertEqual(new["domains"]["enabled"], ["d3a", "general"])
        self.assertEqual(new["domains"]["default"], "d3a")
        self.assert_common_semantics(old, new)
        old_rows = self.registry_rows(old["domains"]["modules"]["d3a"], "tests")
        new_rows = self.registry_rows(new["domains"]["modules"]["d3a"], "tests")
        self.assertEqual(new_rows, old_rows)
        self.assertEqual([row["id"] for row in new_rows], ["TEAM_DT_A", "TEAM_DT_B"])
        self.assertEqual(root_path.read_bytes(), original_bytes)
        self.assertEqual(root_path.stat().st_mtime_ns, original_mtime)

    def test_custom_domain_identity_contracts_registries_and_skill_refs_survive(self):
        config = load(ROOT / "examples/team-config.custom-domain.yaml")
        config["domain"]["custom"]["lane_policy"] = {"mode": "fixed", "selected_lane": "lite"}
        source = self.write_config(config)
        preview, _ = self.preview(source)
        old = self.resolve(source, "legacy")
        new = self.materialize_and_resolve(preview)
        custom = config["domain"]["custom"]
        self.assertEqual(new["domains"]["enabled"], [custom["id"]])
        self.assertEqual(new["domains"]["default"], custom["id"])
        module = new["domains"]["modules"][custom["id"]]
        self.assertEqual(module["trigger_rules"], custom["trigger_rules"])
        self.assertEqual(module["lane_policy"], custom["lane_policy"])
        before = old["domain"]
        for kind in ("layers", "tests"):
            self.assertEqual(self.registry_rows(module, kind), self.registry_rows(before, kind))
        self.assertEqual(module["required_contracts"], before["required_contracts"])
        for key in ("workflow_skill_ref", "planner_skill_ref", "completion_skill_ref"):
            self.assertEqual(module[key], before[key])

    def test_unknown_nested_field_is_preserved_and_explicitly_blocks(self):
        config = load(ROOT / "examples/team-config.minimal.yaml")
        config["knowledge"] = {"repo_context": {"future_policy": {"keep": [1, 2]}}}
        source = self.write_config(config)
        preview, _ = self.preview(source, "BLOCKED")
        unsupported = [row for row in preview["field_dispositions"] if row["status"] == "UNSUPPORTED"]
        self.assertTrue(any(row["source_path"].startswith("knowledge.repo_context.future_policy")
                            for row in unsupported), preview)
        self.assertNotEqual(preview["validation"]["semantic_parity"], "PASS")

    def test_referenced_dependency_bytes_change_identity_without_source_change(self):
        dependency = self.work / "knowledge.md"
        dependency.write_text("# Public knowledge placeholder A\n", encoding="utf-8")
        config = load(ROOT / "examples/team-config.minimal.yaml")
        config["knowledge"] = {"architecture_doc_ref": str(dependency)}
        source = self.write_config(config)
        before, _ = self.preview(source)
        dependency.write_text("# Public knowledge placeholder B\n", encoding="utf-8")
        after, _ = self.preview(source)
        self.assertEqual(before["source_sha256"], after["source_sha256"])
        self.assertNotEqual(before["dependency_sha256"], after["dependency_sha256"])
        self.assertNotEqual(before["bundle_sha256"], after["bundle_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
