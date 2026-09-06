#!/usr/bin/env python3
"""RED contracts for a publishable, one-file v2 team-config surface."""

import hashlib
import importlib.util
import inspect
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEAM_SCRIPTS = ROOT / ".claude/skills/idc-team-config/scripts"
WORKFLOW_SCRIPTS = ROOT / ".claude/skills/idc-workflow/scripts"
GENERAL = ROOT / ".claude/skills/idc-workflow/references/domains/general"
TEMPLATE_DOMAIN = ROOT / ".claude/skills/idc-workflow/references/domains/template-domain"
TEMPLATE = ROOT / "team-config.yaml.template"
MINIMAL = ROOT / "examples/team-config.v2-minimal.yaml"
CUSTOM = ROOT / "examples/team-config.v2-custom-domain.yaml"
V1_EXAMPLES = [
    ROOT / "examples/team-config.minimal.yaml",
    ROOT / "examples/team-config.custom-domain.yaml",
    ROOT / "examples/team-config.d3a-team-dt.yaml",
    ROOT / "examples/team-config.full-bindings.yaml",
]


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def run(script, *args):
    return subprocess.run(
        [sys.executable, "-B", str(script), *map(str, args)],
        cwd=ROOT,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True,
        text=True,
        timeout=60,
    )


def payload(path, wrapper=None):
    document = load(path) if Path(path).is_file() else {}
    return document.get(wrapper) or document


def resolve_ref(ref, base, team_root=ROOT):
    if ref.startswith("harness://"):
        return ROOT / ref[len("harness://"):]
    if ref.startswith("team://"):
        return team_root / ref[len("team://"):]
    path = Path(ref)
    return path if path.is_absolute() else base / path


def resolve_binding_ref(ref, team_root):
    if ref.startswith("harness://"):
        return ROOT / ref[len("harness://"):]
    if ref.startswith("team://"):
        return team_root / ref[len("team://"):]
    path = Path(ref)
    if path.is_absolute():
        return path
    team_candidate = team_root / path
    return team_candidate if team_candidate.exists() else ROOT / path


def pack_dependencies(pack_path):
    pack = load(pack_path).get("domain_pack") or {}
    refs = [pack.get(key) for key in (
        "workflow_profile_ref", "capability_policy_ref",
        "completion_predicate_ref", "knowledge_root_ref",
    )]
    refs += list((pack.get("registries") or {}).values())
    return pack, [resolve_ref(ref, pack_path.parent) for ref in refs if isinstance(ref, str)]


class TeamConfigSurfaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="idc-team-config-surface-")
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)

    def prepare(self, config, label):
        output = self.temp / (label + "-effective.yaml")
        completed = run(
            TEAM_SCRIPTS / "prepare_runtime.py",
            "--config", config,
            "--output", output,
        )
        return completed, payload(output, "effective_runtime"), output

    def test_required_v2_surface_assets_are_independently_available(self):
        required = [
            GENERAL / "domain-pack.yaml",
            GENERAL / "workflow-profile.yaml",
            GENERAL / "capability-policy.yaml",
            GENERAL / "completion-predicate.yaml",
            TEMPLATE_DOMAIN / "domain-pack.yaml",
            TEMPLATE_DOMAIN / "workflow-profile.yaml",
            TEMPLATE_DOMAIN / "capability-policy.yaml",
            TEMPLATE_DOMAIN / "completion-predicate.yaml",
            MINIMAL,
            CUSTOM,
            ROOT / ".claude/skills/idc-team-config/references/team-config-v2.md",
            ROOT / ".claude/skills/idc-team-config/references/runtime-lifecycle.md",
        ]
        for path in required:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file(), "V2_SURFACE_ASSET_MISSING: " + str(path))

    def test_official_general_pack_has_resolvable_policy_profile_predicate_and_registries(self):
        if not (GENERAL / "domain-pack.yaml").is_file():
            self.skipTest("official General v2 Pack is not available yet")
        pack, dependencies = pack_dependencies(GENERAL / "domain-pack.yaml")
        self.assertEqual(pack.get("id"), "general")
        self.assertEqual((pack.get("lane_policy") or {}).get("mode"), "dynamic")
        self.assertTrue(dependencies)
        for path in dependencies:
            with self.subTest(path=path):
                self.assertTrue(path.exists(), "GENERAL_PACK_REF_MISSING: " + str(path))

    def test_v2_template_and_minimal_example_prepare_ready(self):
        for config in (TEMPLATE, MINIMAL):
            with self.subTest(config=config.name):
                if not config.is_file():
                    self.fail("V2_CONFIG_MISSING: " + str(config))
                document = load(config)
                self.assertEqual(document.get("config_version"), 2)
                domains = document.get("domains") or {}
                self.assertTrue(domains.get("enabled"))
                self.assertIn(domains.get("default"), domains.get("enabled") or [])
                self.assertIsInstance(domains.get("definitions"), dict)
                result, effective, _ = self.prepare(config, config.stem)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(effective.get("status"), "READY", effective)

    def test_v2_custom_example_resolves_selects_and_compiles_declared_order(self):
        if not CUSTOM.is_file():
            self.skipTest("v2 custom example is not available yet")
        config = load(CUSTOM)
        domain_id = (config.get("domains") or {}).get("default")
        result, effective, effective_path = self.prepare(CUSTOM, "custom")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        module = effective["domains"]["modules"][domain_id]
        lane = (config.get("lane") or {}).get("default") or "lite"
        profile = (module.get("lane_profiles") or {}).get(lane) or {}
        orchestration = profile.get("orchestration") or {}
        self.assertEqual(orchestration.get("mode"), "ordered")
        expected = [
            (step["stage"], skill, step["id"])
            for step in orchestration.get("steps") or []
            for skill in step.get("skill_ids") or []
        ]
        self.assertTrue(expected, "CUSTOM_ORDERED_STEPS_MISSING")
        first_stage = expected[0][0]
        demand = self.temp / "custom-demand.yaml"
        demand.write_text(yaml.safe_dump({"capability_demand": {
            "execution_unit_ref": "placeholder-surface-unit",
            "selected_domain": domain_id,
            "selected_stage": first_stage,
            "selected_lane": lane,
            "lane_applicability": "applicable",
            "execution_profile": module.get("execution_profile"),
            "required_capability_keys": [],
            "optional_capability_keys": [],
            "observed_signals": [],
        }}), encoding="utf-8")
        selection_path = self.temp / "custom-selection.yaml"
        selected = run(
            TEAM_SCRIPTS / "select_capabilities.py",
            "--effective", effective_path,
            "--demand", demand,
            "--output", selection_path,
        )
        self.assertEqual(selected.returncode, 0, selected.stdout + selected.stderr)
        request = self.temp / "custom-graph-request.yaml"
        request.write_text(yaml.safe_dump({"run_graph_compile_request": {
            "selected_domain": domain_id,
            "selected_lane": lane,
            "observed_signals": [],
        }}), encoding="utf-8")
        graph_path = self.temp / "custom-graph.yaml"
        compiled = run(
            TEAM_SCRIPTS / "compile_run_graph.py",
            "--effective", effective_path,
            "--selection", selection_path,
            "--request", request,
            "--output", graph_path,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        graph = payload(graph_path, "run_graph")
        observed = [(node.get("stage"), node.get("skill_id"), node.get("step_id"))
                    for node in graph.get("nodes") or []]
        self.assertEqual(observed, expected)

        bindings = config.get("bindings") or {}
        extensions = config.get("adapter_extensions") or []
        self.assertTrue(bindings, "CUSTOM_EXAMPLE_BINDING_REQUIRED")
        self.assertTrue(extensions, "CUSTOM_EXAMPLE_EXTENSION_REQUIRED")
        capabilities = {row["id"]: row for row in effective.get("available_capabilities") or []}
        configured_team_root = Path((config.get("team") or {}).get("repo_path") or ".")
        if not configured_team_root.is_absolute():
            configured_team_root = CUSTOM.parent / configured_team_root
        for capability_id, binding in bindings.items():
            with self.subTest(binding=capability_id):
                self.assertIn(capability_id, capabilities)
                expected_ref = resolve_binding_ref(binding["skill_ref"], configured_team_root)
                self.assertEqual(Path(capabilities[capability_id]["skill_ref"]).resolve(),
                                 expected_ref.resolve())
        for extension in extensions:
            with self.subTest(extension=extension.get("id")):
                self.assertIn(extension.get("id"), capabilities)

    def test_disabled_d3a_is_not_loaded(self):
        general_pack = GENERAL / "domain-pack.yaml"
        if not general_pack.is_file():
            self.skipTest("official General v2 Pack is not available yet")
        absent = self.temp / "absent-d3a-pack.yaml"
        config = self.temp / "disabled-d3a.yaml"
        config.write_text(yaml.safe_dump({
            "config_version": 2,
            "team": {"id": "placeholder-surface", "repo_path": str(ROOT)},
            "domains": {"enabled": ["general"], "default": "general", "definitions": {
                "general": {"pack_ref": str(general_pack)},
                "d3a": {"pack_ref": str(absent)},
            }},
            "bindings": {},
        }, sort_keys=False), encoding="utf-8")
        result, effective, _ = self.prepare(config, "disabled-d3a")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("d3a", (effective.get("domains") or {}).get("modules") or {})
        behavior_paths = list((effective.get("runtime_dependency_files") or {}).keys())
        self.assertFalse(any("/domains/d3a/" in path.replace("\\", "/")
                             for path in behavior_paths), behavior_paths)

    def test_enabled_missing_d3a_pack_is_a_bounded_failure(self):
        absent = self.temp / "absent-d3a-pack.yaml"
        enabled = self.temp / "enabled-missing-d3a.yaml"
        enabled.write_text(yaml.safe_dump({
            "config_version": 2,
            "team": {"id": "placeholder-surface", "repo_path": str(ROOT)},
            "domains": {"enabled": ["d3a"], "default": "d3a",
                        "definitions": {"d3a": {"pack_ref": str(absent)}}},
            "bindings": {},
        }), encoding="utf-8")
        failed, body, _ = self.prepare(enabled, "enabled-missing-d3a")
        diagnostic = failed.stdout + failed.stderr + yaml.safe_dump(body)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("NEEDS_TEAM_CONFIG", diagnostic)
        self.assertIn("DOMAIN_PACK_MISSING", diagnostic)
        self.assertNotIn("Traceback", diagnostic)

    def test_preview_migration_is_side_effect_free_and_candidate_resolves(self):
        source = self.temp / "legacy.yaml"
        source.write_bytes(V1_EXAMPLES[0].read_bytes())
        before = (source.read_bytes(), source.stat().st_mtime_ns,
                  sorted(str(path.relative_to(self.temp)) for path in self.temp.rglob("*")))
        migrated = run(TEAM_SCRIPTS / "migrate_team_config.py",
                       "--config", source, "--preview")
        self.assertEqual(migrated.returncode, 0, migrated.stderr)
        preview = (yaml.safe_load(migrated.stdout) or {}).get("migration_preview") or {}
        self.assertEqual(preview.get("status"), "READY", preview)
        self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns,
                          sorted(str(path.relative_to(self.temp)) for path in self.temp.rglob("*"))),
                         before)
        bundle = self.temp / "bundle"
        bundle.mkdir()
        for asset in preview.get("assets") or []:
            target = bundle / asset["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            content = asset["content"]
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), asset["sha256"])
            target.write_text(content, encoding="utf-8")
        candidate = bundle / "team-config.yaml"
        candidate.write_text(yaml.safe_dump(preview["candidate_config"], sort_keys=False),
                             encoding="utf-8")
        result, effective, _ = self.prepare(candidate, "migrated")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(effective.get("status"), "READY")

    def test_schema_defines_the_real_v2_domains_contract(self):
        schema = load(ROOT / ".claude/skills/idc-workflow/references/schemas/team-config.schema.yaml")
        contract = schema.get("team_config") or {}
        domains = contract.get("domains") or {}
        self.assertIn("2", str(contract.get("config_version")))
        self.assertIsInstance(domains, dict, "SCHEMA_V2_DOMAINS_MISSING")
        for field in ("enabled", "default", "definitions"):
            with self.subTest(field=field):
                self.assertIn(field, domains, "SCHEMA_V2_FIELD_MISSING: domains." + field)
        definition_text = yaml.safe_dump(domains.get("definitions") or {})
        self.assertIn("pack_ref", definition_text)

    def test_documentation_uses_resolvable_local_links_for_canonical_references(self):
        team_skill = ROOT / ".claude/skills/idc-team-config/SKILL.md"
        canonical = {
            "references/team-config-v2.md",
            "references/runtime-lifecycle.md",
        }
        links = set(re.findall(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)",
                               team_skill.read_text(encoding="utf-8")))
        self.assertTrue(canonical.issubset(links),
                        "TEAM_CONFIG_CANONICAL_LINKS_MISSING: " + str(canonical - links))
        docs = [team_skill, ROOT / ".claude/skills/idc-workflow/SKILL.md",
                ROOT / "README.md", ROOT / "QUICKSTART.md",
                ROOT / "docs/adoption-guide.md", ROOT / "docs/team-rollout-playbook.md",
                ROOT / "docs/confidential-migration-checklist.md"]
        for document in docs:
            for link in re.findall(r"\[[^]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                target = link.split("#", 1)[0]
                if not target or "://" in target or target.startswith("#"):
                    continue
                candidate = document.parent / target
                if not candidate.exists():
                    candidate = ROOT / target.lstrip("/")
                with self.subTest(document=document.relative_to(ROOT), target=target):
                    self.assertTrue(candidate.exists(), "BROKEN_DOCUMENT_REF: " + target)

    def test_cli_and_host_api_surfaces_are_real(self):
        cli = {
            TEAM_SCRIPTS / "prepare_runtime.py": {"--config", "--output"},
            TEAM_SCRIPTS / "compile_run_graph.py": {
                "--effective", "--selection", "--request", "--output"},
            WORKFLOW_SCRIPTS / "authorize_execution.py": {
                "--request", "--output", "--host-control-record"},
            TEAM_SCRIPTS / "run_event_ledger.py": {
                "--graph", "--request", "--output", "--host-records"},
            TEAM_SCRIPTS / "verify_completion.py": {
                "--request", "--output", "--dispatch-state"},
        }
        for script, flags in cli.items():
            with self.subTest(script=script.name):
                result = run(script, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                for flag in flags:
                    self.assertIn(flag, result.stdout)

        dispatch_path = TEAM_SCRIPTS / "dispatch_state.py"
        spec = importlib.util.spec_from_file_location("dispatch_state_surface", dispatch_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = {
            "initialize_state": ["state_path", "graph", "authorization", "run_id"],
            "acquire_dispatch": ["state_path", "claim"],
            "record_success": ["state_path", "success"],
            "export_snapshot": ["state_path"],
        }
        for name, parameters in expected.items():
            with self.subTest(api=name):
                self.assertTrue(callable(getattr(module, name, None)))
                self.assertEqual(list(inspect.signature(getattr(module, name)).parameters),
                                 parameters)

    def test_legacy_v1_examples_remain_available_for_migration(self):
        for path in V1_EXAMPLES:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertEqual(load(path).get("config_version"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
