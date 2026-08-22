#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ".claude/skills/idc-workflow/references"
LAYER_REGISTRY = {"TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV"}
DT_REGISTRY = {"TPRINT", "FW", "DPF"}
GENERAL_COMPONENT_REGISTRY = {
    "GENERAL_COMPONENT_PLACEHOLDER",
    "GENERAL_COMPONENT_SECONDARY_PLACEHOLDER",
    "GENERAL_COMPONENT_SUPPORT_PLACEHOLDER",
}
GENERAL_TEST_REGISTRY = {
    "GENERAL_TEST_PLACEHOLDER",
    "GENERAL_TEST_SECONDARY_PLACEHOLDER",
    "GENERAL_CHECK_PLACEHOLDER",
}
PLACEHOLDER_PATTERNS = [
    "<ENTERPRISE_PLACEHOLDER>",
    "<ENTERPRISE_API_CONTRACT>",
    "<ENTERPRISE_REPO_PATH>",
    "<ENTERPRISE_DT_BUILD_COMMAND>",
    "<ENTERPRISE_DT_RUN_COMMAND>",
    "<ENTERPRISE_TRAN_BUILD_COMMAND>",
]
COMPLEX_HARD_TRIGGERS = {
    "critical_ambiguity",
    "high_risk",
    "cross_module_or_layer_impact",
    "api_semantic_change",
    "state_machine_or_concurrency_or_security_or_performance",
    "data_migration",
    "needs_dependency_dag",
    "needs_multiple_subagents",
    "multiple_test_domains",
    "high_failure_impact",
}
FAST_REQUIRED_CONDITIONS = {
    "goal_clear",
    "tiny_scope",
    "low_risk",
    "no_behavior_contract_change",
    "no_core_logic_change",
    "no_cross_module_impact",
    "no_new_test_required",
    "existing_verification_available",
    "simple_verification",
    "localized_change",
    "fast_scope_evidence_present",
}
LITE_FLOOR_TRIGGERS = {
    "new_capability",
    "behavior_contract_change",
    "new_or_changed_test_required",
    "multi_file_or_multi_component_change",
    "focused_design_required",
    "broad_repo_exploration_required",
    "affected_scope_unknown",
}


def read_text(path):
    return (ROOT / path).read_text()


def runtime_path(path):
    if path.startswith(".claude/"):
        return path
    if path.startswith("agents/"):
        return f".claude/{path}"
    if path.startswith("skills/"):
        return f".claude/{path}"
    if path.startswith("examples/"):
        return path
    return f"{RUNTIME}/{path}"


def parse_inline_list(value):
    value = value.strip()
    assert_true(value.startswith("[") and value.endswith("]"), f"期望 inline list，但得到：{value}")
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip("'\"") for item in inner.split(",")]


def extract_registry_ids(path):
    return set(re.findall(r"^\s*-\s+id:\s+([A-Z_]+)\s*$", read_text(path), flags=re.MULTILINE))


def extract_registry_knowledge_files(path):
    return re.findall(r"^\s+knowledge_file:\s+(.+)\s*$", read_text(path), flags=re.MULTILINE)


def extract_domain_module_files():
    return re.findall(r"^\s+module_file:\s+(.+)\s*$", read_text(".claude/skills/idc-workflow/references/domains/registry.yaml"), flags=re.MULTILINE)


def extract_domain_module_ids():
    return set(re.findall(r"^\s+-\s+id:\s+([a-z0-9-]+)\s*$", read_text(".claude/skills/idc-workflow/references/domains/registry.yaml"), flags=re.MULTILINE))


def extract_lane_files():
    return re.findall(r"^\s+file:\s+(.+)\s*$", read_text(".claude/skills/idc-workflow/references/lanes/registry.yaml"), flags=re.MULTILINE)


def extract_lane_ids():
    return set(re.findall(r"^\s+-\s+id:\s+([a-z0-9-]+)\s*$", read_text(".claude/skills/idc-workflow/references/lanes/registry.yaml"), flags=re.MULTILINE))


def extract_module_string_value(path, key):
    match = re.search(rf"^\s+{re.escape(key)}:\s+(.+)\s*$", read_text(path), flags=re.MULTILINE)
    assert_true(match is not None, f"{path} 缺少字段：{key}")
    return match.group(1).strip()


def extract_module_asset_paths(path):
    text = read_text(path)
    candidates = []
    for key in ["coding_layers", "test_domains", "entrypoint", "requirement_assessor", "planner_schema", "tdd_state_machine", "root"]:
        candidates += re.findall(rf"^\s+{re.escape(key)}:\s+([A-Za-z0-9_./-]+)\s*$", text, flags=re.MULTILINE)
    candidates += re.findall(r"^\s+-\s+([A-Za-z0-9_./-]+(?:/SKILL\.md)?)\s*$", text, flags=re.MULTILINE)
    return [item for item in candidates if "/" in item and not item.startswith("domains/template-domain")]


def extract_inline_list_after_key(path, key):
    match = re.search(rf"^\s*{re.escape(key)}:\s*(\[.*\])\s*$", read_text(path), flags=re.MULTILINE)
    assert_true(match is not None, f"缺少 inline list key：{key}")
    return parse_inline_list(match.group(1))


def extract_plan_edges(path):
    text = read_text(path)
    return [
        {"from": source, "to": target}
        for source, target in re.findall(r"^\s*-\s+from:\s+([A-Z_]+)\n\s+to:\s+([A-Z_]+)\s*$", text, flags=re.MULTILINE)
    ]


def extract_verification_mapping(path):
    text = read_text(path)
    mapping = {}
    section = text.split("verification_mapping:", 1)[1].split("execution_strategy:", 1)[0]
    for layer, domains in re.findall(r"^\s{4}([A-Z_]+):\n\s{6}required_dt_domains:\s*(\[.*\])\s*$", section, flags=re.MULTILINE):
        mapping[layer] = {"required_dt_domains": parse_inline_list(domains)}
    return mapping


def extract_context_layer(path):
    match = re.search(r"^\s{2}layer:\s+([A-Z_]+)\s*$", read_text(path), flags=re.MULTILINE)
    assert_true(match is not None, f"{path} 缺少 context layer")
    return match.group(1)


def extract_lane_fixture_blocks():
    text = read_text("examples/lane-fixtures.yaml")
    blocks = re.split(r"\n\s{2}- id: ", "\n" + text.split("fixtures:", 1)[1])
    return [block.strip() for block in blocks if block.strip()]


def extract_tr3_fixture_blocks():
    text = read_text("examples/tr3-fixtures.yaml")
    blocks = re.split(r"\n\s{2}- id: ", "\n" + text.split("fixtures:", 1)[1])
    return [block.strip() for block in blocks if block.strip()]


def parse_bool_value(value):
    return value.strip().lower() == "true"


def parse_lane_fixture(block):
    lines = block.splitlines()
    fixture_id = lines[0].strip()
    input_values = {}
    for key, value in re.findall(r"^\s+([a-z0-9_]+):\s+(true|false)\s*$", block, flags=re.MULTILINE):
        input_values[key] = parse_bool_value(value)
    expected_lane = re.search(r"^\s{4}expected_lane:\s+([a-z]+)\s*$", block, flags=re.MULTILINE).group(1)
    expected_rule = re.search(r"^\s{4}expected_rule:\s+([a-z_]+)\s*$", block, flags=re.MULTILINE).group(1)
    return fixture_id, input_values, expected_lane, expected_rule


def parse_tr3_fixture(block):
    lines = block.splitlines()
    fixture_id = lines[0].strip()
    expected_domain_match = re.search(r"^\s{4}expected_domain_candidates:\s+\[(.*)\]\s*$", block, flags=re.MULTILINE)
    expected_domains = []
    if expected_domain_match and expected_domain_match.group(1).strip():
        expected_domains = [item.strip() for item in expected_domain_match.group(1).split(",")]
    expected_change_type = re.search(r"^\s{4}expected_change_type:\s+([a-z_]+)\s*$", block, flags=re.MULTILINE).group(1)
    expected_change_shape = re.search(r"^\s{4}expected_change_shape:\s+([a-z_]+)\s*$", block, flags=re.MULTILINE).group(1)
    signals_section = block.split("expected_lane_signals:", 1)[1]
    expected_signals = {}
    for key, value in re.findall(r"^\s{6}([a-z0-9_]+):\s+(true|false)\s*$", signals_section, flags=re.MULTILINE):
        expected_signals[key] = parse_bool_value(value)
    return fixture_id, expected_domains, expected_change_type, expected_change_shape, expected_signals


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_registry_files_match_fixed_architecture():
    layers = extract_registry_ids(".claude/skills/idc-workflow/references/registries/d3a-layers.yaml")
    domains = extract_registry_ids(".claude/skills/idc-workflow/references/registries/dt-domains.yaml")
    general_components = extract_registry_ids(".claude/skills/idc-workflow/references/registries/general-components.yaml")
    general_tests = extract_registry_ids(".claude/skills/idc-workflow/references/registries/general-test-domains.yaml")
    d3a_workflow = read_text(".claude/skills/idc-workflow/references/workflows/d3a-workflow.md")
    d3a_skill = read_text(".claude/skills/idc-d3a-coding/SKILL.md")
    architecture = read_text("docs/architecture.md")
    readme = read_text("README.md")
    assert_true(layers == LAYER_REGISTRY, "D3A layer registry 发生漂移。")
    assert_true(domains == DT_REGISTRY, "DT domain registry 发生漂移。")
    assert_true(general_components == GENERAL_COMPONENT_REGISTRY, "General component registry 发生漂移。")
    assert_true(general_tests == GENERAL_TEST_REGISTRY, "General test registry 发生漂移。")
    for label, text in [
        ("d3a workflow", d3a_workflow),
        ("d3a skill", d3a_skill),
        ("architecture", architecture),
        ("README", readme),
    ]:
        assert_true("harness 固定" in text, f"{label} 必须声明 D3A 是 harness 固定的流程。")


def test_registry_knowledge_templates_exist():
    files = extract_registry_knowledge_files(".claude/skills/idc-workflow/references/registries/d3a-layers.yaml")
    files += extract_registry_knowledge_files(".claude/skills/idc-workflow/references/registries/dt-domains.yaml")
    files += extract_registry_knowledge_files(".claude/skills/idc-workflow/references/registries/general-components.yaml")
    files += extract_registry_knowledge_files(".claude/skills/idc-workflow/references/registries/general-test-domains.yaml")
    for file_name in files:
        path = ROOT / file_name
        assert_true(path.exists(), f"Registry 指向的 knowledge 模板不存在：{file_name}")
        assert_true("<ENTERPRISE_" in path.read_text(), f"Knowledge 模板缺少 enterprise placeholder：{file_name}")


def test_domain_module_registry_files_exist():
    module_ids = extract_domain_module_ids()
    assert_true("d3a" in module_ids, "Domain Module registry 缺少 d3a module。")
    assert_true("general" in module_ids, "Domain Module registry 缺少 general module。")
    for module_file in extract_domain_module_files():
        assert_true((ROOT / runtime_path(module_file)).exists(), f"Domain Module 文件不存在：{module_file}")


def test_framework_supports_dynamic_scenarios_and_skill_adapters():
    scenario_router = read_text(".claude/skills/idc-workflow/references/workflows/scenario-router.md")
    domain_router = read_text(".claude/skills/idc-workflow/references/workflows/domain-module-router.md")
    skill_router = read_text(".claude/skills/idc-workflow/references/workflows/skill-adapter-router.md")
    adapter_schema = read_text(".claude/skills/idc-workflow/references/schemas/skill-adapter.schema.yaml")
    adapter_registry = read_text(".claude/skills/idc-workflow/references/registries/skill-adapters.yaml")
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    context_planner = read_text(".claude/skills/idc-team-config/scripts/plan_context.rb")
    architecture = read_text("docs/architecture.md")
    README = read_text("README.md")
    team_config = read_text("team-config.yaml.template")
    quickstart = read_text("QUICKSTART.md")
    team_config_generator = read_text("docs/team-config-generator.html")
    gitignore = read_text(".gitignore")

    for fragment in [
        "DYNAMIC_SCENARIO",
        "不属于固定 Domain Module",
        "简单普通 coding 任务才进入 `GENERAL_CODING` fallback",
        "D3A 只是一个 active Domain Module，不是 Core 特例。",
    ]:
        assert_true(fragment in scenario_router, f"Scenario Router 缺少动态分流规则：{fragment}")

    assert_true("DYNAMIC_SCENARIO or GENERAL_CODING fallback" in domain_router, "Domain Module Router 必须支持 dynamic scenario fallback。")
    assert_true("D3A 是自定义 domain module，不是 Core 特例。" in domain_router, "Domain Module Router 必须声明 D3A 不是 Core 特例。")
    assert_true("Skill Adapter Router" in domain_router, "Domain Module Router 必须把 GC SOP 交给 Skill Adapter Router。")

    for fragment in [
        "Skill Adapter Router",
        "dynamic scenarios and custom domain",
        "enterprise_gc_sop_adapter",
        ".claude/skills/idc-gc-sop-adapter/SKILL.md",
        ".claude/skills/idc-dt-design/SKILL.md",
        ".claude/skills/idc-dt-writer/SKILL.md",
        ".claude/skills/idc-gc-third-skill-placeholder/SKILL.md",
        "references/registries/skill-adapters.yaml",
        "Adapter selection is registry-driven, not name-driven.",
        "capability_keys",
        "allowed_stages",
        "NEEDS_ADAPTER_MAPPING",
        "Do not use `gc` / `dt` / `superpowers` naming as a trigger by itself.",
        "Placeholder adapters are not executable.",
        "D3A may use GC atoms only inside D3A module constraints.",
    ]:
        assert_true(fragment in skill_router, f"Skill Adapter Router 缺少：{fragment}")

    for fragment in [
        "schema: skill_adapter",
        "adapter_registry:",
        "match_inputs:",
        "team_pre_alignment_adapter",
        "team_bindable",
        "capability_keys",
        "allowed_stages",
        "no_match_result: NEEDS_ADAPTER_MAPPING",
        "Skill Adapter Router must select adapters from the adapter_registry, not by name guessing.",
        "enterprise_gc_sop",
        "original_enterprise_repo_skill",
        "evidence_ref_required: true",
        "domain_selection: false",
        "lane_selection: false",
        "contract_gate: false",
        "completion_gate: false",
        "<ENTERPRISE_GC_SOP_REF>",
        "<ENTERPRISE_ORIGINAL_REPO_SKILL_REF>",
        "<ENTERPRISE_GC_THIRD_SKILL_NAME>",
        "<ENTERPRISE_BRAINSTORMING_SKILL_REF>",
    ]:
        assert_true(fragment in adapter_schema, f"Skill Adapter schema 缺少：{fragment}")

    for fragment in [
        "skill_adapters:",
        "id: idc-brainstorming",
        "class: team_pre_alignment_adapter",
        "status: team_bindable",
        "id: idc-superpowers-adapter",
        "id: idc-gc-sop-adapter",
        "id: idc-dt-design",
        "id: idc-dt-writer",
        "id: idc-dt-build",
        "id: idc-tran-build",
        "id: idc-gc-third-skill-placeholder",
        "capability_keys:",
        "allowed_stages:",
        "capability_selection_ref",
        "confidential_original_repo_skill_ref",
        "effective_team_config_ref",
        "binding_ref: team-config.yaml.bindings.dt_design.skill_ref",
        "Team-owned brainstorming should bind to idc-brainstorming",
        "Grill Me is provided by idc-intent-grilling",
        "executable: false",
        "Adapter selection is registry-driven, not name-driven.",
        "NEEDS_ADAPTER_MAPPING",
    ]:
        assert_true(fragment in adapter_registry, f"Skill Adapter registry 缺少：{fragment}")

    assert_true(not (ROOT / ".claude/skills/idc-workflow/references/registries/team-adapter-bindings.template.yaml").exists(), "旧 Team Binding 第二入口必须删除。")

    assert_true(".claude/skills/idc-skill-adapter-router/SKILL.md" in context_planner, "Execution Context Plan 必须加载 Skill Adapter Router。")
    assert_true((ROOT / ".claude/skills/idc-workflow/references/schemas/skill-adapter.schema.yaml").exists(), "Skill Adapter schema 必须保留为 Resolver 契约。")
    assert_true((ROOT / ".claude/skills/idc-workflow/references/registries/skill-adapters.yaml").exists(), "Skill Adapter registry 必须保留为被动配置。")
    assert_true("ruby .claude/skills/idc-team-config/scripts/prepare_runtime.rb" in id_workflow, "idc-workflow 每次入口必须自动执行 Team Config preflight。")
    assert_true("Run this on every `idc-workflow` invocation" in id_workflow, "运行时不得复用陈旧 effective config。")
    assert_true("the template is never executed" in id_workflow, "生产运行不得把 template 当作配置 fallback。")
    assert_true("Dynamic Scenario Coding" in README, "README 必须把 Dynamic Scenario 作为顶层路径。")
    assert_true("## 多团队复用模型" in README, "README 必须明确多团队复用模型。")
    assert_true("IDC Core" in README and "Domain Module" in README and "Team Binding" in README, "README 必须声明 Core / Domain Module / Team Binding 三层。")
    assert_true("多团队共享 `IDC Core`" in README, "README 必须声明 Core 可被多团队共享。")
    assert_true("Skill Adapter registry" in README, "README 必须记录 Skill Adapter registry。")
    assert_true("idc-team-config" in README, "README 必须记录单配置 Resolver。")
    assert_true("team-config.yaml.template" in README, "README 必须记录统一 team config 入口。")
    assert_true("team-config.yaml" in gitignore, "真实 team-config.yaml 必须被 git ignore。")
    assert_true(".cache/" in gitignore, "工具生成的 cache/index 必须被 git ignore。")
    assert_true(".idc/runs/<task-id>/attempt-<n>/" in id_workflow, "idc-workflow 必须把 per-run 产物收进 .idc/runs/<task-id>/attempt-<n>/ 目录。")
    assert_true("capability-selection-<execution-unit>.yaml" in id_workflow, "idc-workflow 必须使用 per-EU selection 文件名。")
    team_config_skill = read_text(".claude/skills/idc-team-config/SKILL.md")
    assert_true(".idc/runs/<task-id>/attempt-<n>/" in team_config_skill, "idc-team-config 必须把 per-run 产物收进 .idc/runs/<task-id>/attempt-<n>/ 目录。")
    assert_true("capability-selection-<execution-unit>.yaml" in team_config_skill, "idc-team-config 必须声明 per-EU 产物文件名规则。")
    assert_true("decides adapter admission" in adapter_registry, "Skill Adapter registry 必须声明自己管 admission，运行时可达性由 effective config 决定。")
    for fragment in [
        "config_version: 1",
        "team:",
        "repo_path: <REPO_PATH>",
        "domain:",
        "mode: d3a",
        "dt_domains: []",
        "custom:",
        "workflow_skill_ref: null",
        "general:",
        "components: []",
        "test_domains: []",
        "bindings:",
        "brainstorming:",
        "dt_design:",
        "dt_writer:",
        "dt_build:",
        "tran_build:",
        "knowledge:",
        "layer_docs: {}",
        "adapter_extensions: []",
        "lane:",
        "default: lite",
        "profiles:",
        "skills: {allow: [], deny: [], required: []}",
        "mode: ordered # autonomous | ordered",
        "capability_selection:",
        "autonomous_minimal_sufficient",
        "self_optimization:",
    ]:
        assert_true(fragment in team_config, f"team-config.yaml.template 缺少字段：{fragment}")
    for key in ["build_command", "run_command", "pass_condition", "command:"]:
        assert_true(key not in team_config, f"team-config 绑定槽不允许出现命令键（严格 skill_ref 模型）：{key}")
    bindings_block = team_config.split("bindings:")[1].split("adapter_extensions:")[0]
    slot_names = re.findall(r"^  ([a-z_]+):$", bindings_block, flags=re.M)
    assert_true(len(slot_names) == 20, f"绑定槽必须是 20 个 skill 槽（实际 {len(slot_names)}）。")
    assert_true("skill_ref: null" in bindings_block, "绑定槽必须用 skill_ref 绑定。")
    for fragment in [
        "domain.custom.lane_policy.mode",
        "domain.custom.lane_policy.selected_lane",
        "laneProfileArea",
        "lane.\" + lane + \".allow",
        "lane.\" + lane + \".steps",
        "lane.\" + lane + \".max_optional_skills",
        "adapter.extensions",
        "adapter_extensions:",
        "execution_role:",
        "composes_with:",
        "supersedes:",
        "capability_selection:",
        "self_optimization:",
        "ext.split(/\\r?\\n/)",
    ]:
        assert_true(fragment in team_config_generator, f"team-config generator 缺少 V1 字段或多扩展能力支持：{fragment}")
    for legacy_field in ["skill_base_path", "use_d3a", "fast_skip_steps", "lite_skip_steps", "complex_skip_steps"]:
        assert_true(legacy_field not in team_config_generator, f"team-config generator 仍含旧字段：{legacy_field}")
    for fragment in [
        "Step 1: Copy The Harness",
        "Step 2: Create Team Config",
        "cp team-config.yaml.template team-config.yaml",
        "Step 3: Configure Team And Domain",
        "Step 4: Bind Skills And Resolve Ownership",
        "Step 5: Fill Knowledge Indexes",
        "Step 6: Configure Execution Profiles",
        "Step 7: Run Preflight",
        "Step 8: Run IDC Workflow",
        "Step 9: Verify One Vertical Slice",
        "composes_with",
        "supersedes",
        "registration_audit_status: PASS",
        "$idc-workflow <TASK_OR_TR3>",
        "Execution Authorization = AUTHORIZED",
        "lane_applicability = not_applicable",
    ]:
        assert_true(fragment in quickstart, f"QUICKSTART 缺少步骤：{fragment}")
    assert_true("D3A 是当前第一个自定义 active module" in README, "README 必须声明 D3A 是自定义 module。")
    assert_true("## 项目优势" in README, "README 必须总结项目优势。")
    assert_true("## v1.0 定位" in README, "README 必须明确 v1.0 定位。")
    assert_true("v1.0 是首个可用版本" in README, "README 必须声明 v1.0 是首个可用版本。")
    assert_true("Human Alignment 管检测" in README, "README 必须声明 Human Alignment 管检测。")
    assert_true("GC SOP 可配置且真正生效" in README, "README 必须声明 Lane 配置由 Capability Selector 实际执行。")
    assert_true("真实 D3A 知识地址" in README, "README 必须声明保密区绑定 D3A 知识索引地址。")
    assert_true("第一阶段目标是跑通一条最小 D3A vertical slice" in README, "README 必须声明 V0 入区后的最小 vertical slice。")
    assert_true("运行时自动生效" in README, "README 必须声明 team-config 自动 preflight。")
    rollout = read_text("docs/team-rollout-playbook.md")
    for fragment in ["最小接入", "team://", "团队验收", "多团队复制边界", "source_sha256"]:
        assert_true(fragment in rollout, f"多团队推广手册缺少：{fragment}")
    assert_true("动态分流的 Intent-Driven Coding 框架" in architecture, "architecture 必须声明动态分流框架定位。")
    assert_true("Dynamic Scenario Mode" in architecture, "architecture 必须包含 Dynamic Scenario Mode。")
    assert_true("Skill Adapter Router 不靠名字猜测" in architecture, "architecture 必须声明 adapter registry-driven。")

    team_customization = read_text(".claude/skills/idc-workflow/TEAM_CUSTOMIZATION.md")
    for fragment in [
        "## Multi-Team Reuse Model",
        "IDC Core",
        "Team Binding",
        "Generated Runtime",
        "reuse IDC Core unchanged",
        "adapter_extensions",
        "already has a Brainstorming capability",
        "does not have Grill Me",
    ]:
        assert_true(fragment in team_customization, f"TEAM_CUSTOMIZATION 必须明确多团队 DIY 边界：{fragment}")


def test_active_domain_module_declares_required_contract():
    module_file = ".claude/skills/idc-workflow/references/domains/d3a/module.yaml"
    text = read_text(module_file)
    for required in ["id:", "name:", "status:", "route:", "registries:", "workflow:", "knowledge:", "execution:"]:
        assert_true(required in text, f"d3a module 缺少 contract 区块：{required}")
    assert_true(extract_module_string_value(module_file, "id") == "d3a", "d3a module id 不正确。")
    assert_true(extract_module_string_value(module_file, "status") == "active", "d3a module 必须是 active。")
    assert_true("required_contracts:" in text, "d3a module 必须声明 required_contracts。")
    assert_true("- api_contract" in text, "d3a module 必须要求 api_contract。")
    assert_true("- verification_contract" in text, "d3a module 必须要求 verification_contract。")
    assert_true("lane_policy:" in text, "d3a module 必须声明 Lane applicability policy。")
    assert_true("mode: not_applicable" in text, "D3A 的 Lane 必须标记为不适用。")
    assert_true("selected_lane: null" in text, "D3A 不得选择 fast/lite/complex Lane。")
    assert_true("execution_profile: d3a_fixed_workflow" in text, "D3A 必须使用用户设计的固定 workflow。")
    assert_true("bypass_lane_resolver: true" in text, "d3a module 必须跳过通用 Lane Resolver。")


def test_d3a_uses_shared_execution_skeleton_with_enterprise_constraints():
    module = read_text(".claude/skills/idc-workflow/references/domains/d3a/module.yaml")
    workflow = read_text(".claude/skills/idc-workflow/references/workflows/d3a-workflow.md")
    plan_schema = read_text(".claude/skills/idc-workflow/references/schemas/d3a-plan.schema.yaml")
    skill = read_text(".claude/skills/idc-d3a-coding/SKILL.md")

    assert_true("\n  lane_policy:" in module, "D3A lane_policy 必须属于 domain_module contract。")
    for stage in ["Planner", "Knowledge Preparation", "Execution Unit Split", "TDD Execution", "Verification / Completion"]:
        assert_true(stage in workflow, f"D3A 必须包含共享执行骨架阶段：{stage}")
    for fragment in ["knowledge_requirements:", "layer_context_packets:", "每个 Layer Context Packet 只能包含一个 coding_layer", "独立 RED/GREEN evidence"]:
        assert_true(fragment in plan_schema, f"D3A plan contract 缺少逐 Layer 规划约束：{fragment}")
    assert_true("Planner -> Knowledge Preparation -> Execution Unit Split -> TDD -> Completion" in skill, "D3A skill 必须明确与 General 共用执行骨架。")


def test_active_domain_module_asset_paths_exist():
    for asset_path in extract_module_asset_paths(".claude/skills/idc-workflow/references/domains/d3a/module.yaml"):
        assert_true((ROOT / runtime_path(asset_path)).exists(), f"d3a module 引用的资产不存在：{asset_path}")
    for asset_path in extract_module_asset_paths(".claude/skills/idc-workflow/references/domains/general/module.yaml"):
        assert_true((ROOT / runtime_path(asset_path)).exists(), f"general module 引用的资产不存在：{asset_path}")


def test_general_domain_module_is_active_and_self_closing():
    module = read_text(".claude/skills/idc-workflow/references/domains/general/module.yaml")
    workflow = read_text(".claude/skills/idc-workflow/references/workflows/general-coding.md")
    plan_schema = read_text(".claude/skills/idc-workflow/references/schemas/general-plan.schema.yaml")
    skill = read_text(".claude/skills/idc-general-coding/SKILL.md")

    assert_true("id: general" in module, "general module id 不正确。")
    assert_true("status: active" in module, "general module 必须 active。")
    assert_true("route_id: GENERAL_CODING" in module, "general module route 不正确。")
    assert_true("registries/general-components.yaml" in module, "general module 必须使用 general component registry。")
    assert_true("registries/general-test-domains.yaml" in module, "general module 必须使用 general test registry。")
    assert_true("required_tests_or_builds_pass" in module, "general completion gate 必须基于测试或 build evidence。")
    assert_true("coverage_evidence_or_exemption" in module, "general completion gate 必须包含 coverage 或豁免检查点。")
    assert_true("lane_policy:" in module and "mode: dynamic" in module, "General module 必须显式使用 dynamic Lane policy。")
    assert_true("resolver: workflows/lane-resolver.md" in module, "General module 必须把 Lane 交给通用 Resolver。")
    assert_true("- task_contract" in module, "general module 必须要求 task_contract。")
    assert_true("- verification_contract" in module, "general module 必须要求 verification_contract。")
    assert_true("API Contract 不是所有 General Coding 都必须要" in workflow, "general workflow 必须说明 API Contract 非全局强制。")
    assert_true("不使用 D3A Layer / DT Domain registry" in workflow, "general workflow 不能依赖 D3A registry。")
    assert_true("不编造 General component / test domain taxonomy" in workflow, "general workflow 必须禁止编造 taxonomy。")
    assert_true("max_change_loc: 500" in plan_schema, "general plan 必须声明 500 LOC。")
    assert_true("General plan must not reference D3A Layer registry." in plan_schema, "general plan 必须禁止 D3A Layer registry。")
    assert_true("General component and test domain ids are placeholders" in plan_schema, "general plan 必须声明 placeholder taxonomy。")
    assert_true("Do not use D3A Layer or DT Domain registries." in skill, "general skill 必须禁止 D3A registry。")


def test_lane_registry_files_exist():
    registry = read_text(".claude/skills/idc-workflow/references/lanes/registry.yaml")
    assert_true(extract_lane_ids() == {"fast", "lite", "complex"}, "Lane registry 必须只包含 fast/lite/complex。")
    assert_true("allowed_lane_ids: [fast, lite, complex]" in registry, "Lane registry 必须显式声明只允许 fast/lite/complex。")
    assert_true("no_implicit_lane_ids: true" in registry, "Lane registry 必须禁止隐式 lane。")
    assert_true("default_lane: lite" in registry, "Lane registry 必须声明默认 lane 是 lite。")
    assert_true("default_is_fallback_only: true" in registry, "Lane 默认值只能作为无法分类时的 fallback。")
    for lane_file in extract_lane_files():
        assert_true((ROOT / runtime_path(lane_file)).exists(), f"Lane 文件不存在：{lane_file}")


def test_every_lane_is_self_closing():
    for lane_file in extract_lane_files():
        text = read_text(runtime_path(lane_file))
        assert_true("completion_requirements:" in text, f"{lane_file} 缺少 completion_requirements。")
        assert_true("completion_summary_exists" in text, f"{lane_file} 必须要求 completion summary。")
        has_evidence_requirement = "evidence" in text or "tests_or_builds_passed" in text
        assert_true(has_evidence_requirement, f"{lane_file} 必须要求 evidence。")

    lane_completion = read_text(".claude/skills/idc-workflow/references/workflows/lane-completion.md")
    assert_true("coverage_evidence_or_exemption_exists" in lane_completion, "Complex 闭环必须包含 coverage 或豁免检查点。")
    assert_true("两者皆缺时不能标记 DONE" in lane_completion, "test-based verification 的 completion 必须要求 coverage evidence 或显式豁免。")


def lane_resolver_decision(signals):
    hard_triggers = sorted(trigger for trigger in COMPLEX_HARD_TRIGGERS if signals.get(trigger))
    if hard_triggers:
        return {
            "selected_lane": "complex",
            "decision_rule": "hard_trigger",
            "hard_triggers": hard_triggers,
            "fast_disqualified_by": sorted(FAST_REQUIRED_CONDITIONS - {key for key, value in signals.items() if value}),
        }

    lite_floor_triggers = sorted(trigger for trigger in LITE_FLOOR_TRIGGERS if signals.get(trigger))
    if lite_floor_triggers:
        return {
            "selected_lane": "lite",
            "decision_rule": "lite_floor",
            "hard_triggers": [],
            "lite_floor_triggers": lite_floor_triggers,
            "fast_disqualified_by": sorted(FAST_REQUIRED_CONDITIONS - {key for key, value in signals.items() if value}),
        }

    met_fast_conditions = {key for key, value in signals.items() if value and key in FAST_REQUIRED_CONDITIONS}
    if FAST_REQUIRED_CONDITIONS <= met_fast_conditions:
        return {
            "selected_lane": "fast",
            "decision_rule": "fast_all_conditions_met",
            "hard_triggers": [],
            "fast_disqualified_by": [],
        }

    return {
        "selected_lane": "lite",
        "decision_rule": "default_lite",
        "hard_triggers": [],
        "fast_disqualified_by": sorted(FAST_REQUIRED_CONDITIONS - met_fast_conditions),
    }


def test_lane_resolver_fixtures_are_stable():
    resolver = read_text(".claude/skills/idc-workflow/references/workflows/lane-resolver.md")
    schema = read_text(".claude/skills/idc-workflow/references/schemas/lane.schema.yaml")

    for text, name in [
        (resolver, "Lane Resolver workflow"),
        (schema, "Lane schema"),
    ]:
        assert_true("fast" in text and "lite" in text and "complex" in text, f"{name} 必须声明三档 lane。")
        assert_true("known-domain" in text and "d3a" in text and "gc" in text and "dynamic" in text, f"{name} 必须禁止把 domain/scenario/adapter 当 lane。")

    for block in extract_lane_fixture_blocks():
        fixture_id, signals, expected_lane, expected_rule = parse_lane_fixture(block)
        decision = lane_resolver_decision(signals)
        assert_true(decision["selected_lane"] == expected_lane, f"{fixture_id} lane 判断漂移。")
        assert_true(decision["decision_rule"] == expected_rule, f"{fixture_id} decision_rule 判断漂移。")
        assert_true("hard_triggers" in decision, f"{fixture_id} 缺少 hard_triggers。")
        assert_true("fast_disqualified_by" in decision, f"{fixture_id} 缺少 fast_disqualified_by。")

    for text, name in [
        (resolver, "Lane Resolver workflow"),
        (schema, "Lane schema"),
    ]:
        assert_true("Lite floor" in text, f"{name} 必须声明 Lite floor。")
        assert_true("production code" in text, f"{name} 必须明确小型 production code 的 Lane 边界。")
        assert_true("unknown" in text, f"{name} 必须声明未知信号不能帮助进入 Fast。")

    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    assert_true("Treat Fast as an evidence-backed small-change path" in id_workflow, "idc-workflow 必须声明 Fast 小改路径。")
    assert_true("tiny localized production-code change may be Fast" in id_workflow, "极小 production code 修改必须允许进入 Fast。")
    assert_true("no new test code is needed" in id_workflow and "existing verification can close it" in id_workflow, "Fast 必须同时满足无需新增测试代码且已有验证可闭环。")


def test_tr3_fixtures_preserve_classification_signals():
    seen = set()
    for block in extract_tr3_fixture_blocks():
        fixture_id, expected_domains, expected_change_type, expected_change_shape, expected_signals = parse_tr3_fixture(block)
        seen.add(fixture_id)
        if fixture_id.startswith("tr3_d3a"):
            assert_true("d3a" in expected_domains, f"{fixture_id} 应该识别为 D3A candidate。")
        if "shotgun" in fixture_id:
            assert_true(expected_change_shape == "shotgun_change", f"{fixture_id} 应该识别为霰弹式修改。")
            assert_true(expected_signals.get("cross_module_or_layer_impact"), f"{fixture_id} 应该触发跨模块/跨层 signal。")
            assert_true(expected_signals.get("multiple_test_domains"), f"{fixture_id} 应该触发多测试域 signal。")
        if "new_capability" in fixture_id:
            assert_true(expected_change_type == "new_capability", f"{fixture_id} 应该识别为新增需求。")
            assert_true(expected_signals.get("api_semantic_change"), f"{fixture_id} 应该触发 API 语义变化 signal。")

    assert_true("tr3_d3a_new_capability" in seen, "TR3 fixture 缺少 D3A 新增需求样例。")
    assert_true("tr3_d3a_shotgun_change" in seen, "TR3 fixture 缺少 D3A 霰弹式修改样例。")
    assert_true("tr3_general_refactor" in seen, "TR3 fixture 缺少 General 重构样例。")


def test_alignment_and_escalation_contracts_exist():
    alignment_schema = read_text(".claude/skills/idc-workflow/references/schemas/alignment-pack.schema.yaml")
    escalation_schema = read_text(".claude/skills/idc-workflow/references/schemas/escalation-policy.schema.yaml")
    human_alignment = read_text(".claude/skills/idc-workflow/references/workflows/human-alignment.md")
    automated_loop = read_text(".claude/skills/idc-workflow/references/workflows/automated-closure-loop.md")

    assert_true("alignment_pack:" in alignment_schema, "缺少 alignment_pack schema。")
    assert_true("human_alignment:" in alignment_schema, "缺少 human_alignment schema。")
    assert_true("completion_gate:" in alignment_schema, "Alignment Pack 必须包含 completion_gate。")
    assert_true("scope_boundary:" in alignment_schema, "Alignment Pack 必须包含 scope_boundary。")
    assert_true("escalation_policy:" in escalation_schema, "缺少 escalation_policy schema。")
    assert_true("return_to: human_alignment" in escalation_schema, "Escalation 必须回到 human_alignment。")
    assert_true("Human Alignment 发生在 Planner 之前" in alignment_schema, "Human Alignment 必须在 Planner 之前。")
    assert_true("前置对齐" in human_alignment, "Human Alignment 文档必须声明前置对齐。")
    assert_true("默认不人工卡点" in automated_loop, "Automated Closure Loop 必须声明默认不人工卡点。")
    assert_true("tool_evidence_unavailable" in escalation_schema, "Escalation Policy 必须覆盖工具证据缺失。")


def test_execution_unit_loc_limit_is_enforced():
    execution_schema = read_text(".claude/skills/idc-workflow/references/schemas/execution-unit.schema.yaml")
    execution_policy = read_text(".claude/skills/idc-workflow/references/workflows/execution-unit-policy.md")
    automated_loop = read_text(".claude/skills/idc-workflow/references/workflows/automated-closure-loop.md")
    d3a_workflow = read_text(".claude/skills/idc-workflow/references/workflows/d3a-workflow.md")
    d3a_coder = read_text(".claude/agents/d3a-layer-coder.md")

    for path, text in [
        (".claude/skills/idc-workflow/references/schemas/execution-unit.schema.yaml", execution_schema),
        (".claude/skills/idc-workflow/references/workflows/execution-unit-policy.md", execution_policy),
        (".claude/skills/idc-workflow/references/workflows/automated-closure-loop.md", automated_loop),
        (".claude/skills/idc-workflow/references/workflows/d3a-workflow.md", d3a_workflow),
        (".claude/agents/d3a-layer-coder.md", d3a_coder),
    ]:
        assert_true("500" in text, f"{path} 必须声明 500 行限制。")

    assert_true("max_change_loc: 500" in execution_schema, "Execution Unit schema 必须声明 max_change_loc: 500。")
    assert_true("每个 execution unit 都必须有自己的 evidence" in execution_policy, "Execution Unit 必须有独立 evidence。")
    assert_true("max_layers_per_packet = 1" in d3a_workflow, "D3A 必须限制一个 packet 一个 Layer。")
    assert_true("execution_unit_too_large" in read_text(".claude/skills/idc-workflow/references/schemas/escalation-policy.schema.yaml"), "Escalation 必须覆盖 execution unit 过大。")


def test_repo_context_provider_contract_is_context_bounded():
    schema = read_text(".claude/skills/idc-workflow/references/schemas/repo-context-provider.schema.yaml")
    workflow = read_text(".claude/skills/idc-workflow/references/workflows/repo-context-providers.md")

    for provider in ["grep", "codegraph", "okl"]:
        assert_true(provider in schema.lower(), f"Repo Context Provider schema 缺少 {provider}。")
    assert_true("max_results: 10" in schema, "Repo Context Provider 必须默认 max_results: 10。")
    assert_true("max_snippet_chars: 800" in schema, "Repo Context Provider 必须默认 max_snippet_chars: 800。")
    assert_true("evidence_ref_required: true" in schema, "Repo Context Provider 必须要求 evidence_ref。")
    assert_true("OKL 文档不能替代 test/build evidence" in schema, "OKL 不能替代工具 evidence。")
    assert_true("grep / CodeGraph / OKL" in workflow, "Provider workflow 必须说明 grep / CodeGraph / OKL。")
    assert_true("max_okl_queries: 1" in schema, "Repo Context Provider 必须限制 okl-query 次数。")
    assert_true("max_grep_queries: 5" in schema, "Repo Context Provider 必须限制 grep query 次数。")
    assert_true("okl-query 是调用 OKL 的命令，不是 provider 名" in schema, "schema 必须区分 OKL provider 和 okl-query 命令。")
    assert_true("summary / refs / keywords" in schema, "调用 OKL 时必须只请求摘要、引用和关键词。")


def test_provider_selection_matrix_is_anchor_aware_and_okl_query_bounded():
    matrix = read_text(".claude/skills/idc-workflow/references/workflows/provider-selection-matrix.md")
    knowledge_gate = read_text(".claude/skills/idc-workflow/references/workflows/knowledge-gate.md")
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")

    assert_true("anchor_known = true" in matrix, "Provider matrix 必须覆盖 anchor known。")
    assert_true("bounded grep" in matrix, "Provider matrix 必须要求 bounded grep。")
    assert_true("anchor_known = false and domain_known = true" in matrix, "Provider matrix 必须覆盖无锚点但有领域语义。")
    assert_true("OKL 是已有 LLM Wiki 能力" in matrix, "Provider matrix 必须说明 OKL 是 LLM Wiki。")
    assert_true("commands:" in matrix and "OKL: okl-query" in matrix, "Provider matrix 必须声明 OKL 由 okl-query 命令调用。")
    assert_true("summary / refs / keywords" in matrix, "OKL 查询必须只返回摘要、引用和关键词。")
    assert_true("max 2 queries" in matrix, "fast lane 必须限制 grep query。")
    assert_true("max 1" in matrix, "matrix 必须限制 okl-query 次数。")
    assert_true("用 OKL 覆盖代码事实" in matrix, "matrix 必须禁止 OKL 覆盖代码事实。")
    assert_true("workflows/provider-selection-matrix.md" in knowledge_gate, "Knowledge Gate 必须引用 provider matrix。")
    assert_true("OKL 本质是 LLM Wiki" in knowledge_gate, "Knowledge Gate 必须说明 OKL 本质。")
    assert_true("references/workflows/provider-selection-matrix.md" in id_workflow, "idc-workflow 必须加载 provider matrix。")


def test_context_engineering_is_progressive_and_not_token_policy():
    path = ROOT / ".claude/skills/idc-workflow/CONTEXT_ENGINEERING.md"
    assert_true(path.exists(), "缺少 Context Engineering 文档。")
    context = path.read_text()
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    team_customization = read_text(".claude/skills/idc-workflow/TEAM_CUSTOMIZATION.md")

    for fragment in [
        "Stage 1: 输入理解",
        "Stage 2: 澄清 / Discovery",
        "Stage 3: Domain / Lane / Contract",
        "Stage 4: 执行",
        "Stage 5: 验证 / 闭环",
        "summary / refs / keywords",
        "targeted CodeGraph",
        "Layer Context Packet",
        "<= 500 LOC",
    ]:
        assert_true(fragment in context, f"Context Engineering 缺少关键设计：{fragment}")

    assert_true("CONTEXT_ENGINEERING.md" in id_workflow, "idc-workflow 必须显式加载 Context Engineering。")
    assert_true("CONTEXT_ENGINEERING.md" in team_customization, "团队定制说明必须包含 Context Engineering。")
    assert_true("Runtime State 形状" in context, "Context Engineering 必须包含 Runtime State。")
    assert_true("不得把旧会话上下文当事实来源" in context, "Context Engineering 必须禁止靠旧会话恢复。")
    assert_true("token budget" not in context.lower(), "Context Engineering 不应写成 token budget。")


def test_repo_rules_are_canonical_in_claude_md():
    agents_path = ROOT / "AGENTS.md"
    claude_path = ROOT / "CLAUDE.md"
    claude = claude_path.read_text()
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    context = read_text(".claude/skills/idc-workflow/CONTEXT_ENGINEERING.md")
    README = read_text("README.md")

    assert_true(not agents_path.exists(), "AGENTS.md 不应继续存在；repo rules 只保留 CLAUDE.md。")
    assert_true(claude_path.exists(), "CLAUDE.md 应该作为 repo rules canonical 文件保留。")
    for fragment in [
        "# Intent-Driven Coding Harness",
        "仓库内不得包含真实企业细节",
        "用户侧统一入口是 `idc-workflow` skill",
        "不维护 `.claude/commands`",
        "所有可执行 IDC 能力都必须沉淀为 `.claude/skills/idc-*/SKILL.md`",
        "名字必须以 `idc-` 开头",
        "先经过 `idc-workflow` skill",
        "Scenario Router 先动态分流",
        "D3A Layer Registry",
        "DT Domain Registry",
        "角色边界",
        "planning_and_delegation_only",
        "Execution Authorization",
        "BLOCKED_DELEGATION_REQUIRED",
        "python3 tests/test_harness.py",
    ]:
        assert_true(fragment in claude, f"CLAUDE.md 缺少 canonical repo rule：{fragment}")

    assert_true("CLAUDE.md" in id_workflow, "idc-workflow 必须读取 CLAUDE.md。")
    assert_true("AGENTS.md" not in id_workflow, "idc-workflow 不应把 AGENTS.md 当 canonical repo rules。")
    assert_true("CLAUDE.md" in context, "Context Engineering 必须读取 CLAUDE.md。")
    assert_true("AGENTS.md" not in context, "Context Engineering 不应把 AGENTS.md 当 canonical repo rules。")
    assert_true("├── CLAUDE.md" in README, "README 目录结构应列 CLAUDE.md。")
    assert_true("├── AGENTS.md" not in README, "README 目录结构不应再列 AGENTS.md。")


def test_delegation_contract_keeps_main_agent_as_planner():
    router = read_text(".claude/skills/idc-workflow/references/workflows/delegation-router.md")
    schema = read_text(".claude/skills/idc-workflow/references/schemas/delegation-contract.schema.yaml")
    skill = read_text(".claude/skills/idc-workflow/SKILL.md")
    context = read_text(".claude/skills/idc-workflow/CONTEXT_ENGINEERING.md")
    loop = read_text(".claude/skills/idc-workflow/references/workflows/automated-closure-loop.md")
    doc = read_text("docs/agent-team-architecture.md")
    html = read_text("docs/context-runtime-view.html")
    authorization_gate = read_text(".claude/skills/idc-workflow/references/workflows/execution-authorization-gate.md")
    authorization_schema = read_text(".claude/skills/idc-workflow/references/schemas/execution-authorization.schema.yaml")
    general_skill = read_text(".claude/skills/idc-general-coding/SKILL.md")
    gc_adapter = read_text(".claude/skills/idc-gc-sop-adapter/SKILL.md")
    authorizer = ROOT / ".claude/skills/idc-workflow/scripts/authorize_execution.rb"

    for text, name in [
        (router, "delegation router"),
        (schema, "delegation schema"),
        (skill, "idc-workflow skill"),
        (context, "context engineering"),
        (loop, "automated closure loop"),
        (doc, "agent team architecture"),
    ]:
        assert_true("planning_and_delegation_only" in text, f"{name} 必须约束 main agent role。")

    for fragment in [
        "Intent / Alignment Team",
        "Knowledge Team",
        "Planning Team",
        "Coding Team",
        "Verification Team",
        "Dynamic Workflow",
        "Delegation Contract",
        "Selection Decision Matrix",
        "When To Use IDC Workflow Router",
        "When To Use Official Dynamic Workflow",
        "When To Use Agent Team",
        "When To Use Subagent",
        "Lane Influence",
        "Domain Influence",
        "subagent 之间必须交流",
        "IDC Workflow Trigger Model",
        "Workflow Trigger Inputs",
        "Workflow Routing Priority",
        "Workflow Switch Conditions",
        "Workflow Output",
    ]:
        assert_true(fragment in router or fragment in doc, f"Delegation 设计缺少：{fragment}")

    for fragment in [
        "full_subagent_session",
        "full_logs",
        "full_search_results",
        "context_to_keep",
        "context_to_drop",
        "selection_layer: dynamic_workflow | agent_team | subagent",
        "workflow_reason",
        "workflow_trigger:",
        "official_dynamic_workflow:",
        "many_execution_units",
        "fanout_collect_verify",
        "repeat_until_pass",
        "latest_event:",
        "entry_condition_matched",
        "allowed_next_states",
        "agent_team_reason",
        "subagent_reason",
        "subagent_communication:",
        "handoff_edges:",
        "completion_authority: main_agent_only",
        "run_state_ref",
        "domain_execution_skill_ref",
        "capability_selection_ref",
        "selected_atomic_skill_refs",
        "execution_authorization_request_ref",
        "execution_receipt:",
        "dispatch_tool_call_ref",
        "executor_session_ref",
    ]:
        assert_true(fragment in schema, f"Delegation schema 缺少上下文边界：{fragment}")
    assert_true("必须覆盖 selected_atomic_skill_refs" in schema, "Delegation schema 必须要求 allowed_paths 覆盖原子产物落点。")

    assert_true("Main agent must not mutate repository code" in skill, "idc-workflow 必须禁止 main 在任何 Lane 直接修改仓库。")
    assert_true("BLOCKED_DELEGATION_REQUIRED" in skill, "delegation tool 不可用时必须阻断，不能 main agent 兜底。")
    assert_true("IDC workflow route -> official dynamic workflow if needed -> agent team -> subagent" in skill, "idc-workflow 必须声明 delegation 选择顺序。")
    assert_true("official dynamic workflow is only for scripted, repeatable, large-scale fan-out orchestration" in skill, "idc-workflow 必须声明 official dynamic workflow 的使用条件。")
    assert_true("multiple subagents need communication" in skill, "idc-workflow 必须声明 agent team 的核心触发条件。")
    assert_true("Delegation Contract" in html, "运行视角 HTML 必须展示 Delegation Contract。")
    for fragment in ["Skill precedence", "outer protocol: idc-general-coding", "main_agent is never a valid executor", "Execution Receipt", "BLOCKED_DELEGATION_REQUIRED"]:
        assert_true(fragment in authorization_gate or fragment in authorization_schema, f"Execution Authorization 设计缺少：{fragment}")
    assert_true("must cover every artifact destination" in authorization_gate, "Authorization Gate 必须校验 allowed_paths 覆盖原子产物落点。")
    assert_true("outer Domain execution protocol" in general_skill, "General Coding 必须声明自己是外层执行协议。")
    assert_true("Do not use GC SOP Adapter as the outer General Coding executor" in gc_adapter, "GC Adapter 不得与 General Coding 竞争外层执行权。")
    assert_true(authorizer.exists(), "缺少可执行 Execution Authorization Gate。")

    valid_request = """execution_authorization_request:
  task_id: auth-test
  workflow_id: general_execution
  selected_domain: general
  selected_lane: lite
  human_alignment_status: approved
  approved_alignment_ref: alignment-pack
  execution_unit_ref: unit-1
  context_packet_ref: context-1
  capability_selection_ref: selection-1
  capability_selection_status: READY
  knowledge_load_plan_ref: <KNOWLEDGE_PLAN_REF>
  knowledge_load_plan_status: READY
  knowledge_plan_id: <KNOWLEDGE_PLAN_ID>
  domain_execution_skill_ref: .claude/skills/idc-general-coding/SKILL.md
  selected_atomic_skill_refs: [.claude/skills/idc-gc-sop-adapter/SKILL.md]
  delegation_contract_ref: delegation-1
  main_agent_role: planning_and_delegation_only
  executor: {kind: subagent, agent_id: general-coder}
  allowed_paths: [src/example.rb]
  expected_outputs: [changed_paths, evidence_refs, execution_receipt]
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        auth_effective = Path(temp_dir) / "auth-effective.yaml"
        auth_resolved = subprocess.run(
            ["ruby", str(ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"), "--config", str(ROOT / "examples/team-config.full-bindings.yaml"), "--output", str(auth_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(auth_resolved.returncode == 0, f"Authorization 测试 Resolver 失败：{auth_resolved.stderr}")
        auth_demand = Path(temp_dir) / "auth-knowledge-demand.yaml"
        auth_demand.write_text((ROOT / "examples/knowledge-demands/fast.yaml").read_text(encoding="utf-8").replace("fast-unit", "unit-1"), encoding="utf-8")
        knowledge_plan_path = Path(temp_dir) / "knowledge-plan.yaml"
        auth_knowledge = subprocess.run(
            ["ruby", str(ROOT / ".claude/skills/idc-team-config/scripts/plan_knowledge.rb"), "--effective", str(auth_effective), "--demand", str(auth_demand), "--output", str(knowledge_plan_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(auth_knowledge.returncode == 0, f"Authorization 测试 Knowledge Plan 失败：{auth_knowledge.stderr}")
        knowledge_plan_id = re.search(r"knowledge_plan_id:\s+(\w+)", knowledge_plan_path.read_text(encoding="utf-8")).group(1)
        rendered_request = valid_request.replace("<KNOWLEDGE_PLAN_REF>", str(knowledge_plan_path)).replace("<KNOWLEDGE_PLAN_ID>", knowledge_plan_id)
        valid_path = Path(temp_dir) / "valid-auth.yaml"
        valid_path.write_text(rendered_request, encoding="utf-8")
        valid = subprocess.run(["ruby", str(authorizer), "--request", str(valid_path)], cwd=ROOT, capture_output=True, text=True)
        assert_true(valid.returncode == 0 and "status: AUTHORIZED" in valid.stdout and "authorization_id:" in valid.stdout, "合法 subagent execution 必须获得授权。")

        invalid_path = Path(temp_dir) / "invalid-main-auth.yaml"
        invalid_path.write_text(rendered_request.replace("agent_id: general-coder", "agent_id: main_agent"), encoding="utf-8")
        invalid = subprocess.run(["ruby", str(authorizer), "--request", str(invalid_path)], cwd=ROOT, capture_output=True, text=True)
        assert_true(invalid.returncode == 3 and "BLOCKED_DELEGATION_REQUIRED" in invalid.stdout and "main_agent cannot be execution owner" in invalid.stdout, "Main agent 作为 executor 必须被机器 Gate 拒绝。")


def test_resume_policy_supports_interruption_recovery():
    resume_policy_path = ROOT / ".claude/skills/idc-workflow/references/workflows/resume-policy.md"
    runtime_schema_path = ROOT / ".claude/skills/idc-workflow/references/schemas/runtime-state.schema.yaml"
    assert_true(resume_policy_path.exists(), "缺少 Resume Policy。")
    assert_true(runtime_schema_path.exists(), "缺少 Runtime State schema。")

    policy = resume_policy_path.read_text()
    schema = runtime_schema_path.read_text()
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    context_planner = read_text(".claude/skills/idc-team-config/scripts/plan_context.rb")
    delegation = read_text(".claude/skills/idc-workflow/references/workflows/delegation-router.md")
    README = read_text("README.md")

    for fragment in [
        "不靠会话记忆恢复",
        "checkpoint / contract / evidence ref",
        "latest_event: interrupted",
        "latest_event = resumed",
        "重新运行 verification",
        "resumeFromRunId",
        "baseline",
        "Resume View",
        "不是 DONE evidence",
    ]:
        assert_true(fragment in policy, f"Resume Policy 缺少关键规则：{fragment}")

    for fragment in [
        "schema: runtime_state",
        "run_id: string",
        "resume_token: string",
        "workflow_snapshot:",
        "approved_alignment_ref: string",
        "delegation_contract_ref: string",
        "context_packet_ref: string",
        "evidence_ledger:",
        "Do not use main agent conversation memory as the source of truth.",
    ]:
        assert_true(fragment in schema, f"Runtime State schema 缺少字段：{fragment}")

    assert_true("resume-policy.md" in context_planner, "Resume Context Plan 必须加载 resume policy。")
    assert_true("runtime-state.schema.yaml" in context_planner, "Resume Context Plan 必须加载 runtime state schema。")
    assert_true("Interruption resume must use `runtime_state` checkpoint refs" in id_workflow, "idc-workflow 必须要求 checkpoint 恢复。")
    assert_true("run_state_ref" in delegation, "Delegation Router 必须要求 run_state_ref。")
    assert_true("禁止从 main agent 记忆中推断 subagent 是否完成" in delegation, "Delegation Router 必须禁止靠记忆判断 subagent 完成。")
    assert_true("Runtime State / Resume Policy" in README, "README 必须记录中断恢复能力。")


def test_confidential_vertical_slice_readiness_gate_exists():
    schema = read_text(".claude/skills/idc-workflow/references/schemas/vertical-slice-readiness.schema.yaml")
    workflow = read_text(".claude/skills/idc-workflow/references/workflows/vertical-slice-readiness-gate.md")
    checklist = read_text("docs/confidential-migration-checklist.md")
    skill = read_text(".claude/skills/idc-workflow/SKILL.md")
    context_planner = read_text(".claude/skills/idc-team-config/scripts/plan_context.rb")
    example = read_text("examples/confidential-vertical-slice-readiness.yaml")

    for fragment in [
        "schema: vertical_slice_readiness",
        "selected_domain: d3a",
        "lane_applicability: not_applicable",
        "selected_lane: null",
        "execution_profile: d3a_fixed_workflow",
        "max_layers: 2",
        "max_dt_domains: 1",
        "max_change_loc_per_execution_unit: 500",
        "verification_mapping_ref",
        "dt_build_skill_ref: <ENTERPRISE_DT_BUILD_SKILL_REF>",
        "tran_build_skill_ref: <ENTERPRISE_TRAN_BUILD_SKILL_REF>",
        "evidence_ref_required: true",
        "placeholder_hygiene_preserved",
        "Do not mark READY_FOR_EXECUTION while any required readiness check is FAIL.",
        "Do not run Lane Resolver or select any Lane for a D3A slice.",
        "Do not treat TR3 DT design as RED or GREEN evidence.",
        "Do not treat OKL or docs as test/build evidence.",
        "DONE still requires D3A RED evidence",
    ]:
        assert_true(fragment in schema, f"Vertical Slice Readiness schema 缺少：{fragment}")

    for fragment in [
        "Vertical Slice Readiness Gate",
        "first team-config onboarding vertical slice selected",
        "All required checks must PASS",
        "Each check must include an `evidence_ref`",
        "Readiness evidence cannot replace",
        "RED evidence",
        "`tran_build` PASS evidence",
        "Return `BLOCKED`",
    ]:
        assert_true(fragment in workflow, f"Vertical Slice Readiness workflow 缺少：{fragment}")

    assert_true("vertical-slice-readiness-gate.md" in context_planner, "带 readiness signal 的 Context Plan 必须加载 Vertical Slice Readiness Gate。")
    assert_true("vertical-slice-readiness.schema.yaml" in context_planner, "带 readiness signal 的 Context Plan 必须加载 Vertical Slice Readiness schema。")
    assert_true("Before the first D3A execution after team-config onboarding" in skill, "idc-workflow 必须要求首条 team-config D3A 执行前跑 readiness gate。")
    assert_true("Vertical Slice Readiness Gate" in checklist, "保密区 checklist 必须引用 readiness gate。")
    assert_true("不能替代" in checklist and "`tran_build` PASS evidence" in checklist, "保密区 checklist 必须声明 readiness 不能替代完成证据。")
    assert_true("status: NOT_READY" in example, "readiness example 必须默认 NOT_READY。")
    assert_true("lane_applicability: not_applicable" in example, "D3A readiness example 必须声明 Lane 不适用。")
    assert_true("selected_lane: null" in example, "D3A readiness example 不得选择 Lane。")
    assert_true("<ENTERPRISE_REPO_PATH>" in example, "readiness example 必须保留 repo placeholder。")


def test_progressive_constraint_loading_files_exist():
    stages = {
        "decision": ".claude/skills/idc-workflow/references/constraints/decision",
        "planning": ".claude/skills/idc-workflow/references/constraints/planning",
        "execution": ".claude/skills/idc-workflow/references/constraints/execution",
    }
    for stage, directory in stages.items():
        files = sorted((ROOT / directory).glob("*.yaml"))
        assert_true(files, f"{stage} constraints 不能为空。")
        for file_path in files:
            text = file_path.read_text()
            assert_true(f"stage: {stage}" in text, f"{file_path} stage 不正确。")
            assert_true("constraints:" in text, f"{file_path} 缺少 constraints。")
            assert_true("forbidden_actions:" in text, f"{file_path} 缺少 forbidden_actions。")

    workflow = read_text(".claude/skills/idc-workflow/references/workflows/progressive-constraint-loading.md")
    assert_true("Decision Constraints" in workflow, "约束加载文档缺少 Decision。")
    assert_true("Planning Constraints" in workflow, "约束加载文档缺少 Planning。")
    assert_true("Execution Constraints" in workflow, "约束加载文档缺少 Execution。")

    execution_constraints = read_text(".claude/skills/idc-workflow/references/constraints/execution/core-execution-constraints.yaml")
    assert_true("tool_side_effects_are_not_evidence" in execution_constraints, "执行约束必须分类工具副作用：非 mutation、非 evidence、不得提交。")


def test_e2e_tr3_d3a_demo_is_complete():
    required_files = [
        "examples/e2e-tr3-d3a/input-tr3.md",
        "examples/e2e-tr3-d3a/normalized-request.yaml",
        "examples/e2e-tr3-d3a/domain-lane-decision.yaml",
        "examples/e2e-tr3-d3a/alignment-pack.yaml",
        "examples/e2e-tr3-d3a/execution-plan.yaml",
        "examples/e2e-tr3-d3a/context-packet-summary.yaml",
        "examples/e2e-tr3-d3a/evidence-summary.yaml",
        "examples/e2e-tr3-d3a/completion-summary.md",
    ]
    for file_name in required_files:
        assert_true((ROOT / file_name).exists(), f"E2E demo 缺少文件：{file_name}")

    normalized = read_text("examples/e2e-tr3-d3a/normalized-request.yaml")
    decision = read_text("examples/e2e-tr3-d3a/domain-lane-decision.yaml")
    plan = read_text("examples/e2e-tr3-d3a/execution-plan.yaml")
    evidence = read_text("examples/e2e-tr3-d3a/evidence-summary.yaml")
    completion = read_text("examples/e2e-tr3-d3a/completion-summary.md")

    assert_true("input_type: tr3_design_doc" in normalized, "E2E demo 必须从 TR3 输入开始。")
    assert_true("selected_domain: d3a" in decision, "E2E demo 必须选择 d3a domain。")
    assert_true("applicability: not_applicable" in decision, "E2E D3A 必须声明 Lane 不适用。")
    assert_true("selected_lane: null" in decision, "E2E D3A 不得选择 Lane。")
    assert_true("execution_profile: d3a_fixed_workflow" in decision, "E2E D3A 必须进入固定 workflow。")
    assert_true("policy_mode: not_applicable" in decision, "E2E D3A 必须来自 module applicability policy。")
    assert_true("lane_resolver_bypassed: true" in decision, "E2E D3A 必须跳过 Lane Resolver。")
    assert_true("decision_rule: domain_workflow_owns_execution" in decision, "E2E D3A 必须由 domain workflow 接管执行。")
    assert_true("max_change_loc: 500" in plan, "E2E demo execution unit 必须声明 500 LOC。")
    assert_true("tran-build-pass" in evidence, "E2E demo 必须包含 tran_build evidence。")
    assert_true("DONE" in completion, "E2E demo 必须包含 completion summary。")


def test_e2e_general_demo_is_complete():
    required_files = [
        "examples/e2e-general-task/input.md",
        "examples/e2e-general-task/normalized-request.yaml",
        "examples/e2e-general-task/domain-lane-decision.yaml",
        "examples/e2e-general-task/alignment-pack.yaml",
        "examples/e2e-general-task/general-plan.yaml",
        "examples/e2e-general-task/evidence-summary.yaml",
        "examples/e2e-general-task/evidence/general-test-red.yaml",
        "examples/e2e-general-task/evidence/general-test-green.yaml",
        "examples/e2e-general-task/evidence/general-check-pass.yaml",
        "examples/e2e-general-task/evidence/general-coverage.yaml",
        "examples/e2e-general-task/completion-summary.md",
    ]
    for file_name in required_files:
        assert_true((ROOT / file_name).exists(), f"General E2E demo 缺少文件：{file_name}")

    normalized = read_text("examples/e2e-general-task/normalized-request.yaml")
    decision = read_text("examples/e2e-general-task/domain-lane-decision.yaml")
    plan = read_text("examples/e2e-general-task/general-plan.yaml")
    evidence = read_text("examples/e2e-general-task/evidence-summary.yaml")
    completion = read_text("examples/e2e-general-task/completion-summary.md")

    assert_true("domain_candidates: [general]" in normalized, "General E2E demo 必须选择 general candidate。")
    assert_true("selected_domain: general" in decision, "General E2E demo 必须选择 general domain。")
    assert_true("selected_components: [GENERAL_COMPONENT_PLACEHOLDER]" in plan, "General E2E demo 必须使用 placeholder component。")
    assert_true("required_test_domains: [GENERAL_TEST_PLACEHOLDER]" in plan, "General E2E demo 必须使用 placeholder test domain。")
    assert_true("max_change_loc: 500" in plan, "General E2E execution unit 必须声明 500 LOC。")
    assert_true("general-test-red" in evidence, "General E2E demo 必须包含 RED evidence。")
    assert_true("general-test-green" in evidence, "General E2E demo 必须包含 GREEN evidence。")
    assert_true("general-coverage" in evidence, "General E2E demo 必须包含 coverage evidence。")
    assert_true("coverage_evidence_or_exemption: true" in completion, "General E2E completion 必须闭合 coverage 闸门。")
    assert_true("DONE" in completion, "General E2E demo 必须包含 completion summary。")


def test_manual_test_scenarios_exist_for_user_experience():
    required_files = [
        "test/README.md",
        "test/01-rough-general.md",
        "test/02-structured-general.md",
        "test/03-tr3-d3a.md",
        "test/04-approved-general-execution.md",
        "test/05-build-failure-fix.md",
        "test/06-large-fanout-dynamic-workflow.md",
    ]
    for file_name in required_files:
        assert_true((ROOT / file_name).exists(), f"缺少手动体验场景：{file_name}")

    expectations = {
        "test/01-rough-general.md": ["idc-intent-discovery", "Brainstorming View", "不应该直接进入 `idc-general-coding`"],
        "test/02-structured-general.md": ["structured_requirement", "Clarification View", "不应该默认 Brainstorming", "不应该把待定细节或开放问题塞进 Alignment View"],
        "test/03-tr3-d3a.md": ["tr3_design_doc", "Domain = d3a", "不应该把 TR3 DT design 当 RED/GREEN evidence"],
        "test/04-approved-general-execution.md": ["general_execution", "Delegation Contract", "general-coder"],
        "test/05-build-failure-fix.md": ["build_failed", "build-error-analyzer", "targeted fix"],
        "test/06-large-fanout-dynamic-workflow.md": ["official_dynamic_workflow.required = true", "fanout_collect_verify", "repeat_until_pass"],
        "test/07-lane-fast.md": ["fast_required_conditions", "fast_scope_evidence_present", "不应该跳过验证", "不应该因为"],
        "test/08-lane-lite-new-capability.md": ["new_or_changed_test_required", "selected_lane = lite", "coverage_evidence_or_exemption", "不应该进 fast"],
        "test/09-lane-anti-fast-one-liner.md": ["fast_disqualified_by", "behavior_contract_change", "unknown", "不应该因为"],
        "test/10-lane-complex-hard-trigger.md": ["cross_module_or_layer_impact", "multiple_test_domains", "needs_dependency_dag", "decision_rule = hard_trigger"],
        "test/11-lane-api-contract-change.md": ["api_semantic_change", "selected_lane = complex", "不应该因"],
    }
    for file_name, fragments in expectations.items():
        text = read_text(file_name)
        assert_true("Prompt to paste" in text, f"{file_name} 必须包含可复制 prompt。")
        for fragment in fragments:
            assert_true(fragment in text, f"{file_name} 缺少体验断言：{fragment}")


def test_adoption_and_deep_dive_docs_exist():
    assert_true((ROOT / "docs/adoption-guide.md").exists(), "缺少 adoption guide。")
    html = read_text("docs/flow-d3a-general.html")
    context_html = read_text("docs/context-runtime-view.html")
    intake_html = read_text("docs/intake-discovery-trigger-flow.html")
    input_routing_html = read_text("docs/user-input-routing-overview.html")
    for fragment in [
        "Intent Dynamic Code Workflow",
        "D3A Path",
        "General Path",
        "Brainstorming View",
        "Alignment View",
        "GENERAL_COMPONENT_PLACEHOLDER",
        "TRAN_CFG",
        "OKL",
        "targeted CodeGraph",
    ]:
        assert_true(fragment in html, f"D3A / General HTML 图缺少关键节点：{fragment}")
    for fragment in [
        "IDC Context Runtime View",
        "Main Agent Session",
        "Subagent Session",
        "TR3 需求输入",
        "一句话需求输入",
        "Brainstorming",
        "Grill Me",
        "OKL",
        "bounded grep",
        "targeted",
        "Layer Context Packet",
        "summary / refs / keywords",
        "IDC Workflow Router",
        "Official Dynamic Workflow",
        "Agent Team",
        "many_execution_units",
        "fanout_collect_verify",
        "repeat_until_pass",
    ]:
        assert_true(fragment in context_html, f"Context Runtime HTML 图缺少关键节点：{fragment}")
    for fragment in [
        "IDC Discovery to Human Alignment Gate",
        "Discovery 是第一个显性能力节点",
        "Human Alignment Check 负责检测 readiness",
        "Discovery",
        "Human Alignment Check",
        "Brainstorming",
        "Grill Me",
        "Grill With Docs",
        "Human Alignment",
        "Execution",
        "raw / vague / incomplete",
        "readiness detection",
        "critical gap detection",
        "NEEDS_BRAINSTORMING",
        "NEEDS_CLARIFICATION",
        "READY_FOR_ALIGNMENT",
        "APPROVED_TO_EXECUTE",
        "needs alternatives",
        "critical gap",
        "docs needed",
        "critical gaps closed",
        "user approved",
        "approval ref is validated",
        "Company Brainstorming triggers through Team Binding",
        "Provider choice is a Human Alignment Gate decision",
        "Execution is not part of Discovery",
    ]:
        assert_true(fragment in intake_html, f"Intake Trigger HTML 图缺少关键节点或触发条件：{fragment}")
    for fragment in [
        "IDC Discovery and Human Alignment Routing Map",
        "Raw Idea",
        "Structured Request",
        "TR3 Design Doc",
        "Approved Pack / Resume",
        "Discovery Owns",
        "Human Alignment Owns",
        "Human Alignment Gate",
        "Human Alignment Check",
        "intake / normalize",
        "maturity signal, not readiness decision",
        "alignment readiness detection",
        "critical gap detection",
        "approval / stale approval gate",
        "Discovery",
        "Brainstorming",
        "Grill Me",
        "Grill With Docs",
        "Scenario Router",
        "Domain Module Router",
        "Lane Resolver",
        "Contract Gate",
        "General Coding",
        "D3A Coding",
        "Team Domain",
        "Adapter Router",
        "D3A fixed user-designed workflow",
        "approved fixed D3A workflow",
        "fixed layer registry only",
        "valid checkpoint",
        "Team Binding for real enterprise commands",
        "Completion / Escalation",
        "Required DT GREEN + tran_build PASS",
    ]:
        assert_true(fragment in input_routing_html, f"User Input Routing HTML 图缺少关键节点或触发条件：{fragment}")
    for file_name in [
        "docs/deep-dive/repo-context-providers.md",
        "docs/deep-dive/progressive-constraint-loading.md",
        "docs/deep-dive/lane-and-completion.md",
        "docs/deep-dive/tr3-input.md",
    ]:
        assert_true((ROOT / file_name).exists(), f"缺少 deep dive 文档：{file_name}")


def test_id_workflow_skill_exists_and_has_triggers():
    skill_path = ROOT / ".claude/skills/idc-workflow/SKILL.md"
    assert_true(skill_path.exists(), "缺少 ID workflow skill。")
    text = skill_path.read_text()
    context_planner = read_text(".claude/skills/idc-team-config/scripts/plan_context.rb")
    routed_resources = text + context_planner
    commands_dir = ROOT / ".claude/commands"
    command_files = sorted(commands_dir.glob("**/*")) if commands_dir.exists() else []
    assert_true(not command_files, f"不应保留 .claude/commands 文件：{command_files}。")
    assert_true("name: idc-workflow" in text, "ID workflow skill 缺少 name。")
    assert_true("description:" in text, "ID workflow skill 缺少 description。")
    assert_true("This is the orchestration skill" in text, "ID workflow 必须声明自己是编排 skill。")
    assert_true("Alignment Pack" in text, "ID workflow skill 必须支持 Alignment Pack。")
    assert_true("TR3" in text, "ID workflow skill 必须支持 TR3。")
    assert_true("Domain = general" in text, "ID workflow skill 必须支持 general domain。")
    assert_true("references/domains/general/module.yaml" in routed_resources, "Decision Context Plan 必须加载 general module。")
    assert_true("500 LOC" in text, "ID workflow skill 必须声明 500 LOC 限制。")
    assert_true("Human Alignment approval" in text, "ID workflow skill 必须要求 Human Alignment approval。")
    assert_true("Human View" in text, "ID workflow skill 必须声明用户可读视图。")
    assert_true("$idc-workflow <task>" in text, "ID workflow skill trigger 必须包含显式 skill 调用示例。")
    assert_true("natural language" in text, "ID workflow skill 必须支持自然语言自动匹配。")
    assert_true("Do not add `.claude/commands` aliases" in text, "ID workflow skill 必须禁止 command alias 层。")
    assert_true("references/human-views/alignment-view.md" in text, "ID workflow skill 必须加载 Alignment View。")
    assert_true("references/human-views/clarification-view.md" in routed_resources, "Clarification signal 必须加载 Clarification View。")
    assert_true("grill-me-method" in text, "ID workflow skill 必须声明 Grill Me method。")
    assert_true("upstream-superpowers-brainstorming" in text, "ID workflow skill 必须声明 upstream Superpowers brainstorming。")
    assert_true("idc-brainstorming-overlay" in text, "ID workflow skill 必须声明 IDC idc-brainstorming overlay。")
    assert_true("references/human-views/brainstorming-view.md" in routed_resources, "Raw idea signal 必须加载 Brainstorming View。")
    assert_true("rough" in text and "Domain = general" in text and "run `idc-intent-discovery` first" in text, "ID workflow skill 必须在 skill 层声明 rough general 先进入 discovery。")
    for skill_name in ["idc-brainstorming", "idc-intent-discovery", "idc-intent-grilling", "idc-intent-alignment"]:
        assert_true(f".claude/skills/{skill_name}/SKILL.md" in routed_resources, f"Context Plan 必须按需编排 {skill_name}。")
    assert_true(".claude/skills/idc-intent-grilling-with-docs/SKILL.md" in routed_resources, "Context Plan 必须按需编排 idc-intent-grilling-with-docs。")
    assert_true("grill-with-docs-method.md" in routed_resources, "Docs clarification signal 必须加载 Grill With Docs method。")

def test_framework_behaviors_are_skillized_with_boundaries():
    for skill_dir in (ROOT / ".claude/skills").iterdir():
        if skill_dir.is_dir():
            assert_true(skill_dir.name.startswith("idc-"), f"所有本仓库 skill 都必须使用 idc- 前缀：{skill_dir.name}。")

    retained_skill_names = [
        "idc-workflow",
        "idc-brainstorming",
        "idc-d3a-coding",
        "idc-dt-build",
        "idc-dt-design",
        "idc-dt-writer",
        "idc-gc-sop-adapter",
        "idc-gc-third-skill-placeholder",
        "idc-general-coding",
        "idc-intent-alignment",
        "idc-intent-discovery",
        "idc-intent-grilling",
        "idc-intent-grilling-with-docs",
        "idc-self-optimization",
        "idc-skill-adapter-router",
        "idc-superpowers-adapter",
        "idc-team-config",
        "idc-tran-build",
    ]
    degraded_reference_nodes = {
        "idc-input-adapter": "references/workflows/input-adapter.md",
        "idc-scenario-router": "references/workflows/scenario-router.md",
        "idc-domain-module-router": "references/workflows/domain-module-router.md",
        "idc-lane-resolver": "references/workflows/lane-resolver.md",
        "idc-contract-gate": "references/workflows/contract-gate.md",
        "idc-requirement-assessor": "references/workflows/requirement-assessor.md",
        "idc-output-surface-router": "references/human-views/",
        "idc-automated-closure": "references/workflows/automated-closure-loop.md",
        "idc-execution-unit-planner": "references/workflows/execution-unit-policy.md",
        "idc-progressive-constraint-loader": "references/workflows/progressive-constraint-loading.md",
        "idc-delegation-router": "references/workflows/delegation-router.md",
        "idc-execution-authorization": "references/workflows/execution-authorization-gate.md",
        "idc-knowledge-gate": "references/workflows/knowledge-gate.md",
        "idc-provider-selection": "references/workflows/provider-selection-matrix.md",
        "idc-repo-context-provider": "references/workflows/repo-context-providers.md",
        "idc-tdd-state-machine": "references/workflows/tdd-state-machine.md",
        "idc-lane-completion": "references/workflows/lane-completion.md",
        "idc-evidence-gate": "references/schemas/verification-contract.schema.yaml",
        "idc-vertical-slice-readiness": "references/workflows/vertical-slice-readiness-gate.md",
        "idc-resume-run": "references/workflows/resume-policy.md",
    }
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    atomic_doc = read_text("docs/atomic-skills.md")
    boundary_doc = read_text("docs/skillization-boundary.md")
    assets_doc = read_text(".claude/skills/idc-workflow/assets/README.md")
    README = read_text("README.md")
    team_customization = read_text(".claude/skills/idc-workflow/TEAM_CUSTOMIZATION.md")

    actual_skill_names = {
        skill_dir.name
        for skill_dir in (ROOT / ".claude/skills").iterdir()
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists()
    }
    assert_true(actual_skill_names == set(retained_skill_names), f"保留 skill 集合漂移：{sorted(actual_skill_names)}。")

    for skill_name in retained_skill_names:
        path = f".claude/skills/{skill_name}/SKILL.md"
        skill = read_text(path)
        assert_true(skill_name.startswith("idc-"), f"IDC core skill 必须使用 idc- 前缀：{skill_name}。")
        assert_true(skill.startswith("---\n"), f"{skill_name} 必须有 skill frontmatter。")
        assert_true(f"name: {skill_name}" in skill, f"{skill_name} 缺少 name。")
        assert_true("## When To Use" in skill, f"{skill_name} 必须声明 When To Use。")
        assert_true("## Output" in skill, f"{skill_name} 必须声明 Output。")
        assert_true("## Hard Rules" in skill, f"{skill_name} 必须声明 Hard Rules。")
        assert_true(skill_name in atomic_doc, f"atomic-skills 文档必须列出 {skill_name}。")

    for skill_name, reference_path in degraded_reference_nodes.items():
        assert_true(not (ROOT / ".claude/skills" / skill_name / "SKILL.md").exists(), f"{skill_name} 应降级为 references，不应继续作为 skill。")
        if not reference_path.endswith("/"):
            assert_true((ROOT / ".claude/skills/idc-workflow" / reference_path).exists(), f"{skill_name} 对应 reference 不存在：{reference_path}。")

    for legacy_skill_name in [
        "id-workflow",
        "input-adapter",
        "scenario-router",
        "domain-module-router",
        "lane-resolver",
        "contract-gate",
        "requirement-assessor",
        "output-surface-router",
        "automated-closure",
        "execution-unit-planner",
        "progressive-constraint-loader",
        "delegation-router",
        "skill-adapter-router",
        "knowledge-gate",
        "provider-selection",
        "repo-context-provider",
        "tdd-state-machine",
        "lane-completion",
        "evidence-gate",
        "vertical-slice-readiness",
        "resume-run",
        "intent-discovery",
        "intent-grilling",
        "intent-alignment",
    ]:
        assert_true(not (ROOT / ".claude/skills" / legacy_skill_name).exists(), f"IDC legacy skill 不能继续存在：{legacy_skill_name}。")

    for fragment in [
        "references/workflows/input-adapter.md",
        "references/workflows/scenario-router.md",
        "references/workflows/domain-module-router.md if DOMAIN_MODULE",
        ".claude/skills/idc-skill-adapter-router/SKILL.md for selected lower-level adapters",
        "references/workflows/automated-closure-loop.md",
        "references/workflows/execution-unit-policy.md",
        "references/workflows/progressive-constraint-loading.md",
        "references/workflows/provider-selection-matrix.md",
        "references/workflows/repo-context-providers.md",
        "references/workflows/tdd-state-machine.md",
        "references/workflows/lane-completion.md",
        "references/schemas/verification-contract.schema.yaml",
        "references/human-views/",
    ]:
        assert_true(fragment in id_workflow, f"idc-workflow skill 必须使用 consolidated flow：{fragment}")

    assert_true("idc-workflow` skill" in README and "不维护 `.claude/commands`" in README, "README 必须声明 idc-workflow 是统一 skill 入口且不保留 commands。")

    for fragment in [
        "Should Be Skills",
        "Should Become Assets / References",
        "schemas",
        "registries",
        "human-view templates",
        "knowledge templates",
        "References vs Assets",
        "$idc-workflow",
        "adapter skills",
    ]:
        assert_true(fragment in boundary_doc, f"skillization boundary 缺少：{fragment}")

    for fragment in [
        "IDC Assets",
        "Assets are static resources used by skills.",
        "Official Skill Directory Shape",
        ".claude/skills/<name>/SKILL.md",
        ".claude/skills/<name>/references/",
        ".claude/skills/<name>/assets/",
        "What Belongs In Assets",
        "What Belongs In References",
        "Do not create a skill for passive data.",
        "Do not put active routing logic in `assets/`.",
        "Enterprise-specific assets must use explicit placeholders",
    ]:
        assert_true(fragment in assets_doc, f"assets README 缺少：{fragment}")

    assert_true("Do not skillize passive assets" in id_workflow and "official skill directory shape" in id_workflow, "idc-workflow 必须声明 passive assets 按官方目录语义沉淀。")
    assert_true("docs/skillization-boundary.md" in README, "README 必须引用 skillization boundary。")
    assert_true("assets/README.md" in README, "README 必须引用 assets boundary。")
    assert_true("Skills vs Assets" in team_customization, "TEAM_CUSTOMIZATION 必须说明 skills vs assets。")
    assert_true("Do not turn schemas, registries, examples, evidence files, or knowledge templates" in team_customization, "TEAM_CUSTOMIZATION 必须禁止 passive data skill 化。")


def test_atomic_pre_alignment_skills_exist_and_are_reusable():
    expected = {
        "idc-brainstorming": [
            "name: idc-brainstorming",
            "raw idea",
            "2-3 concrete approaches",
            "Use only when",
            "Do not use this skill merely because the request is short",
            "upstream Superpowers brainstorming",
            "references/superpowers-brainstorming-method.md",
            "Spike / Bounded / Architectural",
            "never downgrade mid-run",
            "one material discovery question at a time",
            "self-review placeholders, consistency, scope, and ambiguity",
            "team brainstorming binding if available",
            "Company-owned brainstorming should be reused through Team Binding",
            "AskUserTool",
            "BLOCKED_NEEDS_ASK_USER_TOOL",
            "../idc-workflow/references/workflows/discovery-provider.md",
            "../idc-workflow/references/human-views/brainstorming-view.md",
            "Do not write implementation code.",
        ],
        "idc-intent-discovery": [
            "name: idc-intent-discovery",
            "raw_idea",
            "IDC wrapper around the reusable `idc-brainstorming` skill",
            ".claude/skills/idc-brainstorming/SKILL.md",
            "Do not use idc-brainstorming merely because the request is short",
            "rough / vague / sketchy general coding request",
            "`general + rough` still uses this skill",
            "AskUserTool",
            "BLOCKED_NEEDS_ASK_USER_TOOL",
            "../idc-workflow/references/workflows/discovery-provider.md",
            "../idc-workflow/references/human-views/brainstorming-view.md",
            "Do not write implementation code.",
        ],
        "idc-intent-grilling": [
            "name: idc-intent-grilling",
            "GitHub-carried IDC implementation",
            "frontier",
            "Do not require a team binding for Grill Me",
            "../idc-workflow/references/workflows/clarification-provider.md",
            "../idc-workflow/references/human-views/clarification-view.md",
            "AskUserTool",
            "BLOCKED_NEEDS_ASK_USER_TOOL",
            "Do not decide Domain or Lane.",
        ],
        "idc-intent-grilling-with-docs": [
            "name: idc-intent-grilling-with-docs",
            "Grill With Docs",
            "references/grill-with-docs-method.md",
            "updated_doc_refs",
            "Do not edit source files",
            "AskUserTool",
            "BLOCKED_NEEDS_ASK_USER_TOOL",
            "Documentation created here is not RED evidence",
        ],
        "idc-intent-alignment": [
            "name: idc-intent-alignment",
            "Alignment View",
            "../idc-workflow/references/workflows/human-alignment.md",
            "../idc-workflow/references/schemas/alignment-pack.schema.yaml",
            "AskUserTool",
            "BLOCKED_NEEDS_ASK_USER_TOOL",
            "Do not show raw YAML as the primary user interface.",
        ],
    }
    for skill_name, required_fragments in expected.items():
        path = f".claude/skills/{skill_name}/SKILL.md"
        text = read_text(path)
        assert_true("description:" in text, f"{skill_name} 缺少 description。")
        assert_true("reusable outside D3A" in text, f"{skill_name} 必须声明可在 D3A 外复用。")

    upstream_method_path = ROOT / ".claude/skills/idc-brainstorming/references/superpowers-brainstorming-method.md"
    assert_true(upstream_method_path.exists(), "idc-brainstorming 必须实际携带 Superpowers brainstorming method。")
    upstream_method = upstream_method_path.read_text()
    for fragment in [
        "https://github.com/obra/superpowers",
        "Spike",
        "Bounded",
        "Architectural",
        "One-Way Complexity Ratchet",
        "Ask one decision at a time",
        "Explore Approaches",
        "Present The Design",
        "Draft Spec Self-Review",
        "IDC Terminal Mapping",
        "Relationship To IDC Lane",
        "Never map them directly",
        "idc-intent-alignment for implementation approval",
    ]:
        assert_true(fragment in upstream_method, f"Superpowers brainstorming local method 缺少：{fragment}")
        for fragment in required_fragments:
            assert_true(fragment in text, f"{skill_name} 缺少关键片段：{fragment}")

    atomic_doc = read_text("docs/atomic-skills.md")
    for skill_name in expected:
        assert_true(skill_name in atomic_doc, f"atomic-skills 文档缺少 {skill_name}。")
    assert_true("D3A 是 Domain Module" in atomic_doc, "atomic-skills 文档必须说明 D3A 不是通用原子 skill。")

    general_skill = read_text(".claude/skills/idc-general-coding/SKILL.md")
    assert_true("Route back to:" in general_skill and ".claude/skills/idc-intent-discovery/SKILL.md" in general_skill, "idc-general-coding 必须把 rough general 请求导回 idc-intent-discovery。")


def test_superpowers_adapter_skill_is_integrated_under_skills():
    adapter = read_text(".claude/skills/idc-superpowers-adapter/SKILL.md")
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    atomic_doc = read_text("docs/atomic-skills.md")
    attribution = read_text("docs/source-attribution.md")

    assert_true(adapter.startswith("---\n"), "idc-superpowers-adapter 必须有 skill frontmatter。")
    assert_true("name: idc-superpowers-adapter" in adapter, "idc-superpowers-adapter 缺少 name。")
    assert_true("IDC Harness = control plane" in adapter, "idc-superpowers-adapter 必须声明 IDC 是控制面。")
    assert_true("Superpowers Adapter = execution discipline" in adapter, "idc-superpowers-adapter 必须声明自己是执行纪律。")
    assert_true("Domain Module = enterprise domain constraints" in adapter, "idc-superpowers-adapter 必须保留 Domain Module 边界。")
    for stage in [
        "writing-plans",
        "executing-plans",
        "test-driven-development",
        "subagent-driven-development",
        "systematic-debugging",
        "requesting-code-review",
        "receiving-code-review",
        "verification-before-completion",
        "finishing-a-development-branch",
    ]:
        assert_true(stage in adapter, f"idc-superpowers-adapter 缺少阶段：{stage}")

    for override in [
        "IDC rules override this adapter whenever they conflict.",
        "IDC Domain Module Router owns Domain selection.",
        "IDC module policy owns Lane applicability",
        "D3A uses its fixed workflow with Lane marked `not_applicable`",
        "Lane Resolver dynamically",
        "IDC Contract Gate owns required contracts.",
        "D3A Layer and DT Domain registries cannot be changed here.",
        "API Contract must be frozen before implementation.",
        "Superpowers-style verification cannot replace IDC Completion Gate.",
        "OKL, docs, TR3 DT design, and repository search are knowledge inputs, not DONE evidence.",
    ]:
        assert_true(override in adapter, f"idc-superpowers-adapter 缺少 IDC override：{override}")

    assert_true("idc-superpowers-adapter" in read_text(".claude/skills/idc-workflow/references/registries/skill-adapters.yaml"), "Skill registry 必须允许 Selector 选择 idc-superpowers-adapter。")
    assert_true("Superpowers Adapter may provide the inner engineering loop" in id_workflow, "idc-workflow 必须声明 Superpowers Adapter 的边界。")
    assert_true("idc-superpowers-adapter" in atomic_doc, "atomic-skills 文档必须记录 idc-superpowers-adapter。")
    assert_true(".claude/skills/idc-superpowers-adapter/SKILL.md" in attribution, "source attribution 必须记录 adapter 落点。")
    assert_true("https://github.com/obra/superpowers/tree/main/skills" in attribution, "source attribution 必须记录 Superpowers skills 来源。")


def test_gc_sop_and_original_repo_skill_adapters_exist():
    gc = read_text(".claude/skills/idc-gc-sop-adapter/SKILL.md")
    dt_design = read_text(".claude/skills/idc-dt-design/SKILL.md")
    dt_writer = read_text(".claude/skills/idc-dt-writer/SKILL.md")
    third = read_text(".claude/skills/idc-gc-third-skill-placeholder/SKILL.md")
    atomic_doc = read_text("docs/atomic-skills.md")
    checklist = read_text("docs/confidential-migration-checklist.md")
    adapter_registry = read_text(".claude/skills/idc-workflow/references/registries/skill-adapters.yaml")

    for path, text in [
        (".claude/skills/idc-gc-sop-adapter/SKILL.md", gc),
        (".claude/skills/idc-dt-design/SKILL.md", dt_design),
        (".claude/skills/idc-dt-writer/SKILL.md", dt_writer),
        (".claude/skills/idc-gc-third-skill-placeholder/SKILL.md", third),
    ]:
        assert_true(text.startswith("---\n"), f"{path} 必须有 skill frontmatter。")

    for fragment in [
        "name: idc-gc-sop-adapter",
        "enterprise GC full-suite SOP",
        "IDC Core = dynamic routing framework",
        "GC SOP Adapter = reusable enterprise atomic execution abilities",
        ".claude/skills/idc-dt-design/SKILL.md",
        ".claude/skills/idc-dt-writer/SKILL.md",
        ".claude/skills/idc-gc-third-skill-placeholder/SKILL.md",
        "The third original-repository skill is intentionally a placeholder",
        "evidence_ref_required: true",
        "<ENTERPRISE_GC_SOP_REF>",
        "Do not silently relocate a declared artifact destination",
    ]:
        assert_true(fragment in gc, f"idc-gc-sop-adapter 缺少：{fragment}")

    for fragment in [
        "name: idc-dt-design",
        "original enterprise repository skill used to design",
        "DT design is not RED evidence.",
        "DT design is not GREEN evidence.",
        "READY_FOR_DT_WRITER",
        "<ENTERPRISE_ORIGINAL_REPO_SKILL_REF>",
    ]:
        assert_true(fragment in dt_design, f"idc-dt-design adapter 缺少：{fragment}")

    for fragment in [
        "name: idc-dt-writer",
        "original enterprise repository skill used to write",
        "dt_design_ref",
        "red_evidence_refs",
        "green_evidence_refs",
        "Do not mark D3A DONE; IDC Completion Gate owns DONE.",
        "max_change_loc: 500",
    ]:
        assert_true(fragment in dt_writer, f"idc-dt-writer adapter 缺少：{fragment}")

    for fragment in [
        "name: idc-gc-third-skill-placeholder",
        "<ENTERPRISE_GC_THIRD_SKILL_NAME>",
        "Do not execute this placeholder",
        "Do not guess the third skill's purpose.",
    ]:
        assert_true(fragment in third, f"third skill placeholder 缺少：{fragment}")

    for fragment in ["idc-gc-sop-adapter", "idc-dt-design", "idc-dt-writer", "idc-gc-third-skill-placeholder"]:
        assert_true(fragment in atomic_doc, f"atomic-skills 文档缺少 {fragment}。")
        assert_true(fragment in adapter_registry, f"Skill registry 未注册 {fragment}。")

    assert_true("真实 GC 全家桶 SOP atomic ability mapping" in checklist, "保密区 checklist 必须包含 GC SOP mapping。")
    assert_true("`idc-dt-design`、`idc-dt-writer`、`<ENTERPRISE_GC_THIRD_SKILL_NAME>`" in checklist, "保密区 checklist 必须列出三个原仓 skill。")


def test_domain_and_build_skills_define_entry_rules_at_skill_layer():
    d3a_skill = read_text(".claude/skills/idc-d3a-coding/SKILL.md")
    dt_skill = read_text(".claude/skills/idc-dt-build/SKILL.md")
    tran_skill = read_text(".claude/skills/idc-tran-build/SKILL.md")
    grilling_skill = read_text(".claude/skills/idc-intent-grilling/SKILL.md")
    alignment_skill = read_text(".claude/skills/idc-intent-alignment/SKILL.md")

    for path, text in [
        (".claude/skills/idc-d3a-coding/SKILL.md", d3a_skill),
        (".claude/skills/idc-dt-build/SKILL.md", dt_skill),
        (".claude/skills/idc-tran-build/SKILL.md", tran_skill),
    ]:
        assert_true(text.startswith("---\n"), f"{path} 必须有 skill frontmatter。")
        assert_true("## When To Use" in text, f"{path} 必须在 skill 层定义 When To Use。")
        assert_true("Do not use" in text, f"{path} 必须在 skill 层定义 Do not use。")

    assert_true("Domain = d3a" in d3a_skill and "Human Alignment 已 approved" in d3a_skill, "idc-d3a-coding 必须声明 D3A 和 approval 入口条件。")
    assert_true(".claude/skills/idc-intent-discovery/SKILL.md" in d3a_skill, "rough D3A 必须导回 idc-intent-discovery。")
    assert_true(".claude/skills/idc-intent-grilling/SKILL.md" in d3a_skill, "D3A 缺 contract 必须导回 idc-intent-grilling。")
    assert_true("任务是 General Coding" in dt_skill, "idc-dt-build 必须禁止 General Coding 使用。")
    assert_true("selected DT domain" in dt_skill, "idc-dt-build 必须要求 selected DT domain。")
    assert_true("所有 required DT domain 已有 GREEN evidence" in tran_skill, "idc-tran-build 必须要求 required DT GREEN。")
    assert_true("D3A DONE gate" in tran_skill, "idc-tran-build 必须声明只作为 D3A DONE gate。")
    assert_true("rough / raw idea requests" in grilling_skill and ".claude/skills/idc-intent-discovery/SKILL.md" in grilling_skill, "idc-intent-grilling 必须把 rough 请求导回 discovery。")
    assert_true("critical contract / scope / completion gate questions remain" in alignment_skill and ".claude/skills/idc-intent-grilling/SKILL.md" in alignment_skill, "idc-intent-alignment 必须把未澄清问题导回 grilling。")
    assert_true("Do not merge Clarification View into Alignment View." in alignment_skill, "idc-intent-alignment 必须禁止把澄清折进 Alignment。")
    assert_true("pending details" in alignment_skill, "idc-intent-alignment 必须禁止在 Alignment View 放待定细节。")


def test_claude_project_entries_expose_skills_and_agents():
    for skill_dir in sorted((ROOT / ".claude" / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        claude_skill = ROOT / ".claude" / "skills" / skill_dir.name / "SKILL.md"
        assert_true(claude_skill.exists(), f"Claude Code 项目级 skill 入口不存在：{claude_skill}")
        assert_true(claude_skill.read_text().startswith("---\n"), f"Claude Code skill 缺少 frontmatter：{skill_dir.name}")

    for agent_file in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        claude_agent = ROOT / ".claude" / "agents" / agent_file.name
        assert_true(claude_agent.exists(), f"Claude Code 项目级 agent 入口不存在：{claude_agent}")
        text = claude_agent.read_text()
        assert_true(text.startswith("---\n"), f"Claude Code agent 缺少 frontmatter：{claude_agent}")
        assert_true("## 职责" in text or "## 输入" in text, f"Claude Code agent 必须包含可执行职责：{agent_file.name}")


def test_human_views_exist_and_hide_raw_yaml():
    required_files = [
        ".claude/skills/idc-workflow/references/human-views/brainstorming-view.md",
        ".claude/skills/idc-workflow/references/human-views/clarification-view.md",
        ".claude/skills/idc-workflow/references/human-views/alignment-view.md",
        ".claude/skills/idc-workflow/references/human-views/completion-view.md",
        ".claude/skills/idc-workflow/references/human-views/escalation-view.md",
    ]
    for file_name in required_files:
        text = read_text(file_name)
        assert_true("## 模板" in text, f"{file_name} 缺少用户模板。")
        assert_true("## 规则" in text, f"{file_name} 缺少展示规则。")

    brainstorming = read_text(".claude/skills/idc-workflow/references/human-views/brainstorming-view.md")
    alignment = read_text(".claude/skills/idc-workflow/references/human-views/alignment-view.md")
    clarification = read_text(".claude/skills/idc-workflow/references/human-views/clarification-view.md")
    completion = read_text(".claude/skills/idc-workflow/references/human-views/completion-view.md")
    escalation = read_text(".claude/skills/idc-workflow/references/human-views/escalation-view.md")
    assert_true("只在 raw idea 场景默认展示" in brainstorming, "Brainstorming View 必须只用于 raw idea。")
    assert_true("短但结构化的需求跳过 Brainstorming" in brainstorming, "Brainstorming View 必须声明短但结构化需求跳过。")
    assert_true("不因上下文裁剪牺牲需求探索质量" in brainstorming, "Brainstorming View 不能因上下文裁剪牺牲探索质量。")
    assert_true("每轮最多展示 5 个关键问题" in clarification, "Clarification View 必须限制问题数量。")
    assert_true("选择题问题卡" in clarification, "Clarification View 必须默认使用选择题问题卡。")
    assert_true("2-4 个互斥选项" in clarification, "Clarification View 必须声明每题 2-4 个互斥选项。")
    assert_true("不输出长篇文章式追问" in clarification, "Clarification View 不能输出长篇文章式追问。")
    assert_true("grill-me-method" in clarification, "Clarification View 必须支持 Grill Me method 展示。")
    assert_true("当前 Frontier" in clarification, "Clarification View 必须展示 frontier round。")
    assert_true("不直接向用户展示完整 YAML" in alignment, "Alignment View 必须隐藏完整 YAML。")
    assert_true("Alignment View 不能承载待定细节" in alignment, "Alignment View 不能承载待定细节。")
    assert_true("不允许把 Clarification View 合并进 Alignment View" in alignment, "Alignment View 不能合并 Clarification View。")
    assert_true("Evidence 只展示摘要和 ref" in completion, "Completion View 必须限制 evidence 展示粒度。")
    assert_true("不把技术日志全文塞给用户" in escalation, "Escalation View 必须避免展示完整日志。")


def test_user_questions_must_use_ask_user_tool():
    policy = read_text(".claude/skills/idc-workflow/references/workflows/ask-user-tool-policy.md")
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    claude = read_text("CLAUDE.md")
    files = [
        ".claude/skills/idc-workflow/references/workflows/discovery-provider.md",
        ".claude/skills/idc-workflow/references/workflows/clarification-provider.md",
        ".claude/skills/idc-workflow/references/workflows/human-alignment.md",
        ".claude/skills/idc-workflow/references/workflows/resume-policy.md",
        ".claude/skills/idc-workflow/references/workflows/automated-closure-loop.md",
        ".claude/skills/idc-workflow/references/human-views/brainstorming-view.md",
        ".claude/skills/idc-workflow/references/human-views/clarification-view.md",
        ".claude/skills/idc-workflow/references/human-views/alignment-view.md",
        ".claude/skills/idc-workflow/references/human-views/escalation-view.md",
        ".claude/skills/idc-brainstorming/SKILL.md",
        ".claude/skills/idc-intent-discovery/SKILL.md",
        ".claude/skills/idc-intent-grilling/SKILL.md",
        ".claude/skills/idc-intent-grilling-with-docs/SKILL.md",
        ".claude/skills/idc-intent-alignment/SKILL.md",
    ]

    assert_true("所有问用户的问题" in claude and "AskUserTool" in claude, "CLAUDE.md 必须声明 AskUserTool 统一提问约束。")
    assert_true("AskUserTool Policy" in policy, "必须存在 AskUserTool policy。")
    assert_true("BLOCKED_NEEDS_ASK_USER_TOOL" in policy, "AskUserTool 不可用时必须阻塞。")
    assert_true("AskUserQuestion" in policy and "宿主工具名映射" in policy, "AskUserTool policy 必须提供宿主工具名映射，不得按字面名找不到就阻塞。")
    assert_true("references/workflows/ask-user-tool-policy.md" in id_workflow, "idc-workflow 必须加载 AskUserTool policy。")
    assert_true("do not ask the user by plain text" in id_workflow, "idc-workflow 必须禁止普通文本追问。")

    for file_name in files:
        text = read_text(file_name)
        assert_true("AskUserTool" in text, f"{file_name} 必须声明用户问题走 AskUserTool。")
        assert_true("BLOCKED_NEEDS_ASK_USER_TOOL" in text, f"{file_name} 必须声明 AskUserTool 不可用时阻塞。")


def test_clarification_provider_uses_grill_me_method_with_fallback():
    workflow = read_text(".claude/skills/idc-workflow/references/workflows/clarification-provider.md")
    schema = read_text(".claude/skills/idc-workflow/references/schemas/clarification-provider.schema.yaml")
    human_alignment = read_text(".claude/skills/idc-workflow/references/workflows/human-alignment.md")
    requirement_assessor = read_text(".claude/skills/idc-workflow/references/workflows/requirement-assessor.md")
    attribution = read_text("docs/source-attribution.md")
    skill = read_text(".claude/skills/idc-intent-grilling/SKILL.md")
    method = read_text(".claude/skills/idc-intent-grilling/references/grill-me-method.md")
    docs_skill = read_text(".claude/skills/idc-intent-grilling-with-docs/SKILL.md")
    docs_method = read_text(".claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md")
    template = read_text(".claude/skills/idc-intent-grilling/assets/question-card-template.md")
    id_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")
    context_planner = read_text(".claude/skills/idc-team-config/scripts/plan_context.rb")

    assert_true("mattpocock/skills" in workflow, "Clarification Provider 必须标注 Grill Me 方法论来源。")
    assert_true("grill-me-method" in workflow, "Clarification Provider 必须声明 grill-me-method。")
    assert_true("grill-with-docs-method" in workflow, "Clarification Provider 必须声明 grill-with-docs-method。")
    assert_true("builtin-critical-questions" in workflow, "Clarification Provider 必须声明 builtin fallback。")
    assert_true("decision tree" in workflow, "Clarification Provider 必须吸收 decision tree。")
    assert_true("frontier round" in workflow, "Clarification Provider 必须吸收 frontier round。")
    assert_true("Commitment check" in workflow or "commitment check" in workflow, "Clarification Provider 必须吸收 commitment check。")
    assert_true("max_questions: 5" in schema, "Clarification Provider schema 必须限制最多 5 个问题。")
    assert_true("min_options_per_question: 2" in schema, "Clarification Provider schema 必须要求至少 2 个选项。")
    assert_true("max_options_per_question: 4" in schema, "Clarification Provider schema 必须限制最多 4 个选项。")
    assert_true("answer_style: multiple_choice" in workflow, "Clarification Provider 输出必须支持选择题。")
    assert_true("Default answer_style is multiple_choice." in schema, "Clarification Provider 默认必须是选择题。")
    assert_true("不用长篇文章式追问用户" in workflow, "Clarification Provider 不能用长篇文章式追问。")
    assert_true("decision_tree:" in schema, "Clarification Provider schema 必须包含 decision tree。")
    assert_true("commitment_check:" in schema, "Clarification Provider schema 必须包含 commitment check。")
    assert_true("Provider cannot override Domain, Lane, contract, or completion gate." in schema, "Clarification Provider 不能覆盖核心决策。")
    assert_true("https://github.com/mattpocock/skills" in attribution, "Source attribution 必须记录来源 URL。")
    assert_true("workflows/clarification-provider.md" in human_alignment, "Human Alignment 必须引用 Clarification Provider。")
    assert_true("禁止把 Clarification 折叠进 Alignment View" in human_alignment, "Human Alignment 必须禁止澄清短路进 Alignment。")
    assert_true("返回 `NEED_CLARIFICATION` 时，不能继续生成 Alignment View" in requirement_assessor, "Requirement Assessor 必须阻止 NEED_CLARIFICATION 继续生成 Alignment。")
    assert_true("next: \"Clarification Provider\"" in requirement_assessor, "Requirement Assessor 必须把澄清交给 Provider。")
    assert_true("references/grill-me-method.md" in skill, "idc-intent-grilling 必须加载 Grill Me method reference。")
    assert_true("assets/question-card-template.md" in skill, "idc-intent-grilling 必须加载 question card asset。")
    assert_true("name: idc-intent-grilling-with-docs" in docs_skill, "必须内置 idc-intent-grilling-with-docs skill。")
    assert_true("references/grill-with-docs-method.md" in docs_skill, "idc-intent-grilling-with-docs 必须加载 Grill With Docs reference。")
    assert_true("Update public docs only when decisions crystallize" in docs_skill, "Grill With Docs 必须只沉淀已明确决策。")
    assert_true("Do not write implementation code." in docs_skill, "Grill With Docs 不能写实现代码。")
    for fragment in [
        "Grill With Docs Method",
        "Read bounded docs",
        "Update docs only for crystallized decisions",
        "Writable Docs",
        "Do not turn speculative options into recorded decisions",
    ]:
        assert_true(fragment in docs_method, f"Grill With Docs method reference 缺少：{fragment}")
    for fragment in [
        "Grill Me Method",
        "Build decision tree",
        "select current frontier",
        "commitment check",
        "READY_FOR_ALIGNMENT",
        "NEXT_FRONTIER",
        "ESCALATE",
        "Do not ask more than 5 questions",
    ]:
        assert_true(fragment in method, f"Grill Me method reference 缺少：{fragment}")
    for fragment in [
        "Question Card Template",
        "Blocks:",
        "Why needed:",
        "Use 2-4 options.",
        "Do not show raw YAML to the user.",
    ]:
        assert_true(fragment in template, f"Grill Me question card asset 缺少：{fragment}")
    assert_true(".claude/skills/idc-intent-grilling/references/grill-me-method.md" in context_planner, "Clarification Context Plan 必须加载 idc-intent-grilling method reference。")
    assert_true("question-card-template.md" in read_text(".claude/skills/idc-intent-grilling/SKILL.md"), "idc-intent-grilling 必须按需引用 question card asset。")
    assert_true(".claude/skills/idc-intent-grilling-with-docs/SKILL.md" in context_planner, "Docs clarification Context Plan 必须加载 idc-intent-grilling-with-docs。")
    assert_true(".claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md" in context_planner, "Docs clarification Context Plan 必须加载 Grill With Docs method reference。")


def test_discovery_provider_uses_superpowers_brainstorming_for_raw_idea():
    workflow = read_text(".claude/skills/idc-workflow/references/workflows/discovery-provider.md")
    schema = read_text(".claude/skills/idc-workflow/references/schemas/discovery-provider.schema.yaml")
    input_adapter = read_text(".claude/skills/idc-workflow/references/workflows/input-adapter.md")
    normalized_schema = read_text(".claude/skills/idc-workflow/references/schemas/normalized-request.schema.yaml")
    attribution = read_text("docs/source-attribution.md")

    assert_true("obra/superpowers" in workflow, "Discovery Provider 必须标注 Superpowers 方法论来源。")
    assert_true("upstream-superpowers-brainstorming" in workflow, "Discovery Provider 必须声明 upstream Superpowers baseline。")
    assert_true("idc-brainstorming-overlay" in workflow, "Discovery Provider 必须声明 IDC overlay。")
    assert_true("builtin-discovery-questions" in workflow, "Discovery Provider 必须声明 builtin fallback。")
    assert_true("focused discovery questions" in workflow, "Discovery Provider 必须支持聚焦探索问题。")
    assert_true("不因上下文裁剪牺牲需求探索质量" in workflow, "Discovery Provider 不能因上下文裁剪牺牲探索质量。")
    assert_true("不要因为需求很短就默认 Brainstorming" in workflow, "Discovery Provider 不能因为需求短就默认 Brainstorming。")
    assert_true("即使只有一句话，只要目标、行为和验收线索已出现，也不进入 Brainstorming。" in workflow, "Discovery Provider 必须让短但结构化需求跳过 Brainstorming。")
    assert_true("2-3 个方案" in workflow, "Discovery Provider 必须支持多方案取舍。")
    assert_true("Draft spec is not an approved contract." in schema, "Discovery draft spec 不能等于 approved contract。")
    assert_true("Upstream Superpowers brainstorming is the baseline." in schema, "Discovery schema 必须声明 upstream baseline。")
    assert_true("IDC overlay only adapts handoff" in schema, "Discovery schema 必须声明 overlay 只做适配。")
    assert_true("TR3 design docs skip Discovery." in schema, "TR3 必须默认跳过 Discovery。")
    assert_true("input_maturity: raw_idea" in input_adapter, "Input Adapter 必须能标记 raw_idea。")
    assert_true("next_pre_alignment_step: Discovery Provider" in input_adapter, "raw_idea 必须进入 Discovery Provider。")
    assert_true("tr3_design_doc 默认跳过 Discovery Provider" in normalized_schema, "Normalized schema 必须声明 TR3 跳过 Discovery。")
    assert_true("https://github.com/obra/superpowers" in attribution, "Source attribution 必须记录 Superpowers 来源 URL。")
    assert_true("upstream baseline" in attribution, "Source attribution 必须声明 upstream baseline。")
    assert_true("lane_decision_deferred: true" in schema, "Discovery 必须把 Lane 决策延迟给 Lane Resolver。")
    assert_true("must not map directly to IDC Lane" in schema, "Superpowers path 不能直接映射 IDC Lane。")


def test_d3a_unclear_input_cannot_bypass_brainstorming_or_grill_me():
    module = read_text(".claude/skills/idc-workflow/references/domains/d3a/module.yaml")
    workflow = read_text(".claude/skills/idc-workflow/references/workflows/d3a-workflow.md")
    d3a_skill = read_text(".claude/skills/idc-d3a-coding/SKILL.md")
    normalized_schema = read_text(".claude/skills/idc-workflow/references/schemas/normalized-request.schema.yaml")
    idc_workflow = read_text(".claude/skills/idc-workflow/SKILL.md")

    for fragment in [
        "pre_alignment:",
        "domain_hint_does_not_imply_readiness: true",
        "raw_idea_route:",
        "skills/idc-intent-discovery/SKILL.md",
        "skills/idc-brainstorming/SKILL.md",
        "skills/idc-intent-grilling/SKILL.md",
        "questions_via: AskUserTool",
        "execution_requires_human_alignment: approved",
    ]:
        assert_true(fragment in module, f"D3A module 缺少前置澄清契约：{fragment}")

    for fragment in [
        "D3A hint / D3A task",
        "Input Maturity Gate",
        "raw_idea",
        "idc-brainstorming",
        "structured requirement / TR3 with critical gaps",
        "idc-intent-grilling",
        "Human Alignment Check",
        "AskUserTool approval",
        "D3A domain hint 不代表 readiness",
    ]:
        assert_true(fragment in workflow or fragment in d3a_skill, f"D3A 不清晰输入路由缺少：{fragment}")

    pre_alignment_flow = workflow.split("## 固定流程的起点", 1)[1].split("## 固定 Architecture Space", 1)[0]
    fixed_execution_index = pre_alignment_flow.rfind("-> D3A Fixed Workflow")
    assert_true(fixed_execution_index > 0, "D3A 前置流程必须声明 approved 后才进入固定执行。")
    for prerequisite in ["Input Maturity Gate", "idc-brainstorming", "idc-intent-grilling", "Human Alignment Check", "AskUserTool approval"]:
        assert_true(pre_alignment_flow.find(prerequisite) < fixed_execution_index, f"{prerequisite} 必须发生在 D3A Fixed Workflow 之前。")
    main_flow = workflow.split("## 主流程", 1)[1].split("动态部分只允许", 1)[0]
    assert_true(main_flow.find("Requirement Assessor + Human Alignment Check") < main_flow.find("D3A Fixed Workflow"), "D3A Requirement Assessor 必须在固定执行前发现关键缺口。")

    assert_true("D3A raw_idea 仍须 Discovery/Brainstorming" in normalized_schema, "Normalized Request 必须保持 D3A 的 maturity route。")
    assert_true("D3A selection does not imply readiness" in idc_workflow, "IDC 入口必须禁止把 D3A 选择当作 readiness。")
    assert_true("不允许绕过 Human Alignment approval" in d3a_skill, "D3A executor 必须拒绝未批准输入。")


def test_planner_cannot_produce_registry_external_layers():
    plan_path = "examples/mock-d3a-task/d3a-plan.yaml"
    layers = set(extract_inline_list_after_key(plan_path, "coding_layers"))
    domains = set(extract_inline_list_after_key(plan_path, "dt_domains"))
    assert_true(layers <= LAYER_REGISTRY, f"Plan 包含未知 Layer：{layers - LAYER_REGISTRY}")
    assert_true(domains <= DT_REGISTRY, f"Plan 包含未知 DT Domain：{domains - DT_REGISTRY}")

    for edge in extract_plan_edges(plan_path):
        assert_true(edge["from"] in LAYER_REGISTRY, "Dependency DAG 包含未知 source layer。")
        assert_true(edge["to"] in LAYER_REGISTRY, "Dependency DAG 包含未知 target layer。")

    for layer, mapping in extract_verification_mapping(plan_path).items():
        required = set(mapping["required_dt_domains"])
        assert_true(layer in LAYER_REGISTRY, f"Verification mapping 包含未知 Layer：{layer}")
        assert_true(required <= DT_REGISTRY, f"Verification mapping 包含未知 DT Domain：{required - DT_REGISTRY}")


def requirement_assessor_decision(requirement):
    checks = {
        "goal_clear": bool(requirement.get("goal")),
        "core_behavior_clear": bool(requirement.get("core_behavior")),
        "api_semantics_sufficient": bool(requirement.get("api_semantics")),
        "acceptance_criteria_definable": bool(requirement.get("acceptance_criteria")),
        "critical_ambiguity_exists": bool(requirement.get("critical_ambiguity_exists")),
    }
    missing_critical = (
        not checks["goal_clear"]
        or not checks["core_behavior_clear"]
        or not checks["api_semantics_sufficient"]
        or not checks["acceptance_criteria_definable"]
        or checks["critical_ambiguity_exists"]
    )
    return "NEED_CLARIFICATION" if missing_critical else "READY_FOR_SPEC"


def test_requirement_assessor_detects_missing_critical_fields():
    vague_requirement = {
        "goal": "Add a thing",
        "core_behavior": "",
        "api_semantics": "",
        "acceptance_criteria": [],
        "critical_ambiguity_exists": True,
    }
    clear_requirement = {
        "goal": "返回 dummy widget state。",
        "core_behavior": "解析 dummy id，并返回 READY、BLOCKED 或 UNKNOWN。",
        "api_semantics": "DummyGetWidgetState(dummy_widget_id) 返回 state 或 DUMMY_NOT_FOUND。",
        "acceptance_criteria": ["已知 id 返回 state。", "未知 id 返回 DUMMY_NOT_FOUND。"],
        "critical_ambiguity_exists": False,
    }
    assert_true(requirement_assessor_decision(vague_requirement) == "NEED_CLARIFICATION", "模糊需求被错误放行。")
    assert_true(requirement_assessor_decision(clear_requirement) == "READY_FOR_SPEC", "清晰需求被错误阻塞。")


def test_layer_context_packet_only_contains_selected_layer():
    context_files = {
        "DO": "examples/mock-d3a-task/context-packets/do.yaml",
        "TFE": "examples/mock-d3a-task/context-packets/tfe.yaml",
        "DRV": "examples/mock-d3a-task/context-packets/drv.yaml",
    }
    for expected_layer, path in context_files.items():
        assert_true(extract_context_layer(path) == expected_layer, f"{path} 指向了错误 Layer。")
        serialized = read_text(path)
        for other_layer in LAYER_REGISTRY - {expected_layer}:
            assert_true(
                not re.search(rf"\b{re.escape(other_layer)}\b", serialized),
                f"{path} 泄漏了无关 Layer knowledge：{other_layer}",
            )


ALLOWED_LAYER_TRANSITIONS = {
    "SPEC_READY": {"TEST_PREPARING"},
    "TEST_PREPARING": {"RED_CONFIRMED"},
    "RED_CONFIRMED": {"IMPLEMENTING"},
    "IMPLEMENTING": {"IMPL_REVIEW", "GREEN_CONFIRMED"},
    "IMPL_REVIEW": {"GREEN_CONFIRMED", "DT_REVERIFY"},
    "GREEN_CONFIRMED": {"SCAN_RUNNING", "ATOMIC_COMMIT_CREATED", "LAYER_COMPLETE"},
    "SCAN_RUNNING": {"SCAN_GREEN", "DEFECT_FIX"},
    "SCAN_GREEN": {"ATOMIC_COMMIT_CREATED", "LAYER_COMPLETE"},
    "ATOMIC_COMMIT_CREATED": {"LAYER_COMPLETE"},
}


def can_transition(source, target, has_red_evidence=False):
    if target == "GREEN_CONFIRMED" and not has_red_evidence:
        return False
    return target in ALLOWED_LAYER_TRANSITIONS.get(source, set())


def test_dummy_widget_state_query_known_id():
    import dummy_widget
    state = dummy_widget.DummyGetWidgetState("dummy-1")
    assert_true(
        state == dummy_widget.DummyWidgetState.READY,
        "已知 dummy widget id 应返回 READY。",
    )


def test_dummy_widget_state_query_unknown_id():
    import dummy_widget
    result = dummy_widget.DummyGetWidgetState("does-not-exist")
    assert_true(isinstance(result, dummy_widget.DummyError), "未知 id 应返回 typed placeholder error。")
    assert_true(result.code == dummy_widget.DUMMY_NOT_FOUND, "未知 id 应返回 DUMMY_NOT_FOUND。")


def test_no_red_evidence_cannot_enter_green():
    assert_true(not can_transition("IMPLEMENTING", "GREEN_CONFIRMED", has_red_evidence=False), "没有 RED 却允许进入 GREEN。")
    assert_true(can_transition("IMPLEMENTING", "GREEN_CONFIRMED", has_red_evidence=True), "已有 RED 却阻塞 GREEN。")


def test_tdd_extensions_are_team_config_driven():
    tdd = read_text(".claude/skills/idc-workflow/references/workflows/tdd-state-machine.md")
    expected_workflows = {
        "impl-review.md": "team-config.yaml.bindings.impl_review.skill_ref",
        "scan-and-fix-loop.md": "team-config.yaml.bindings.static_scan.skill_ref",
        "atomic-commit.md": "team-config.yaml.bindings.git_commit.skill_ref",
        "knowledge-archive.md": "team-config.yaml.bindings.knowledge_archive.skill_ref",
        "transfer-to-test.md": "team-config.yaml.bindings.system_test.skill_ref",
    }
    for file_name, binding_ref in expected_workflows.items():
        path = f".claude/skills/idc-workflow/references/workflows/{file_name}"
        text = read_text(path)
        assert_true(binding_ref in text, f"{file_name} 必须通过 team-config 引用 skill。")
        assert_true("Do not hard-code" in text or "does not hard-code" in text, f"{file_name} 必须禁止硬编码企业路径或命令。")
    for state in [
        "IMPL_REVIEW",
        "SCAN_RUNNING",
        "SCAN_GREEN",
        "ATOMIC_COMMIT_CREATED",
        "KNOWLEDGE_ARCHIVE",
        "TRANSFER_TO_TEST",
        "DEFECT_FIX",
    ]:
        assert_true(state in tdd, f"TDD 状态机缺少扩展状态：{state}")
    assert_true("team-config.yaml" in tdd and "NEEDS_TEAM_CONFIG" in tdd, "TDD 扩展必须由 team-config 驱动。")


def test_registries_are_team_config_overridable():
    template = read_text("team-config.yaml.template")
    assert_true("dt_domains: []" in template, "team-config 模板必须保留 domain.d3a.dt_domains 覆盖键。")
    assert_true("components: []" in template and "test_domains: []" in template, "team-config 模板必须有 general.components / general.test_domains 覆盖键。")
    assert_true("dt_docs" not in template, "knowledge.dt_docs 已并入 domain.d3a.dt_domains 条目，不得复活。")
    assert_true("d3a_layers" not in template, "D3A Layer 架构固定，不提供配置覆盖键。")
    chain_files = [
        ".claude/skills/idc-workflow/references/workflows/domain-module-router.md",
        ".claude/skills/idc-workflow/references/workflows/knowledge-gate.md",
        ".claude/skills/idc-workflow/references/workflows/general-coding.md",
        ".claude/skills/idc-general-coding/SKILL.md",
        ".claude/skills/idc-d3a-coding/SKILL.md",
        ".claude/skills/idc-dt-build/SKILL.md",
        ".claude/skills/idc-tran-build/SKILL.md",
        ".claude/skills/idc-workflow/SKILL.md",
    ]
    for path in chain_files:
        assert_true("team-config.yaml" in read_text(path), f"{path} 必须声明 team-config 覆盖规则。")
    router = read_text(chain_files[0])
    id_workflow = read_text(chain_files[-1])
    assert_true("整体替换" in router and "不合并" in router, "Domain Module Router 必须声明整体替换、不合并。")
    assert_true("never merge sources" in id_workflow, "idc-workflow 必须声明 registry 覆盖不合并来源。")


def test_filled_team_config_when_present():
    config_file = ROOT / "team-config.yaml"
    if not config_file.exists():
        return
    text = config_file.read_text(encoding="utf-8")
    for leftover in ["<TEAM_ID>", "<REPO_PATH>", "<DT_ID>", "<ENTERPRISE_"]:
        assert_true(leftover not in text, f"team-config.yaml 仍有未填占位符：{leftover}")
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"
    checked = subprocess.run(
        ["ruby", str(resolver), "--config", str(config_file), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert_true(
        checked.returncode == 0,
        f"填好的 team-config.yaml 必须通过正式 Resolver，不得由测试重复解析 YAML：{checked.stderr}",
    )


def test_plan_context_rejects_domain_mode_mismatch():
    preflight = ROOT / ".claude/skills/idc-team-config/scripts/prepare_runtime.rb"
    context_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_context.rb"

    with tempfile.TemporaryDirectory() as temp_dir:
        general_config = Path(temp_dir) / "team-config.yaml"
        general_config.write_text(
            """config_version: 1

team:
  id: gate-general-team
  repo_path: .

domain:
  mode: general

bindings: {}
""",
            encoding="utf-8",
        )
        effective = Path(temp_dir) / "effective.yaml"
        preflighted = subprocess.run(
            ["ruby", str(preflight), "--config", str(general_config), "--output", str(effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(
            preflighted.returncode == 0 and "status: READY" in preflighted.stdout,
            f"General 模式最小配置 preflight 必须 READY：{preflighted.stdout}\n{preflighted.stderr}",
        )

        mismatched = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(effective), "--phase", "decision", "--domain", "d3a"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(
            mismatched.returncode != 0 and "does not match effective domain" in mismatched.stdout,
            f"effective domain 为 general 时 --domain d3a 必须被拒绝：{mismatched.stdout}",
        )

        matched = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(effective), "--phase", "decision", "--domain", "general"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(
            matched.returncode == 0 and "status: READY" in matched.stdout,
            f"effective domain 为 general 时 --domain general 必须保持 READY：{matched.stdout}",
        )


def test_domain_mode_requires_registered_builtin_module():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"

    with tempfile.TemporaryDirectory() as temp_dir:
        registry = Path(temp_dir) / "registry.yaml"
        registry.write_text(
            """domain_modules:
  - id: general
    module_file: domains/general/module.yaml
    status: active
  - id: template-domain
    module_file: domains/template-domain/module.yaml
    status: template
""",
            encoding="utf-8",
        )
        d3a_config = Path(temp_dir) / "team-config.yaml"
        d3a_config.write_text(
            """config_version: 1

team:
  id: gate-d3a-team
  repo_path: .

domain:
  mode: d3a

bindings: {}
""",
            encoding="utf-8",
        )
        checked = subprocess.run(
            ["ruby", str(resolver), "--config", str(d3a_config), "--registry", str(registry), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(
            checked.returncode != 0,
            f"domain.mode d3a 指向未注册 d3a 的 registry 时必须 INVALID：{checked.stdout}",
        )
        assert_true(
            "domain.mode d3a is not registered in the domain module registry; register it or switch domain.mode" in checked.stderr,
            f"Registry Gate 必须给出可操作错误信息：{checked.stderr}",
        )


def test_domain_mode_general_with_d3a_unplugged_stays_ready():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"

    with tempfile.TemporaryDirectory() as temp_dir:
        registry = Path(temp_dir) / "registry.yaml"
        registry.write_text(
            """domain_modules:
  - id: general
    module_file: domains/general/module.yaml
    status: active
  - id: template-domain
    module_file: domains/template-domain/module.yaml
    status: template
""",
            encoding="utf-8",
        )
        general_config = Path(temp_dir) / "team-config.yaml"
        general_config.write_text(
            """config_version: 1

team:
  id: gate-general-team
  repo_path: .

domain:
  mode: general

bindings: {}
""",
            encoding="utf-8",
        )
        checked = subprocess.run(
            ["ruby", str(resolver), "--config", str(general_config), "--registry", str(registry), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(
            checked.returncode == 0 and "READY" in checked.stdout,
            f"拔掉 d3a 注册不得影响 general 团队：{checked.stdout}\n{checked.stderr}",
        )


def test_select_capabilities_rejects_unknown_signal():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"
    selector = ROOT / ".claude/skills/idc-team-config/scripts/select_capabilities.rb"
    config = ROOT / "examples/team-config.full-bindings.yaml"
    assert_true(resolver.exists() and selector.exists() and config.exists(), "Resolver / Selector / full-bindings 配置缺失。")

    with tempfile.TemporaryDirectory() as temp_dir:
        effective = Path(temp_dir) / "effective.yaml"
        resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(config), "--output", str(effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(resolved.returncode == 0, f"team-config Resolver 执行失败：{resolved.stderr}")

        bad_demand = Path(temp_dir) / "unknown-signal.yaml"
        bad_demand.write_text(
            """capability_demand:
  execution_unit_ref: sigtest
  selected_stage: verification
  selected_domain: general
  lane_applicability: applicable
  selected_lane: lite
  execution_profile: lane_driven
  required_capability_keys: []
  optional_capability_keys: []
  observed_signals: [test_faild]
  contract_refs: []
""",
            encoding="utf-8",
        )
        bad = subprocess.run(
            ["ruby", str(selector), "--effective", str(effective), "--demand", str(bad_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(bad.returncode != 0, "未知 observed_signals 必须非零退出，不能静默放行。")
        assert_true("NEEDS_SIGNAL_MAPPING" in bad.stderr, f"stderr 必须报告 NEEDS_SIGNAL_MAPPING：{bad.stderr}")
        assert_true("test_faild" in bad.stderr, "stderr 必须列出未知信号 token。")

        good_demand = Path(temp_dir) / "known-signal.yaml"
        good_demand.write_text(
            """capability_demand:
  execution_unit_ref: sigtest
  selected_stage: verification
  selected_domain: general
  lane_applicability: applicable
  selected_lane: lite
  execution_profile: lane_driven
  required_capability_keys: []
  optional_capability_keys: []
  observed_signals: [tdd_required]
  contract_refs: []
""",
            encoding="utf-8",
        )
        good = subprocess.run(
            ["ruby", str(selector), "--effective", str(effective), "--demand", str(good_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(good.returncode == 0, f"已知信号必须 READY 退出 0：{good.stderr}{good.stdout}")
        assert_true("status: READY" in good.stdout, "已知信号 demand 必须 status: READY。")


def test_lane_profiles_use_ordered_mode():
    config_file = ROOT / "team-config.yaml"
    if not config_file.exists():
        return
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    profiles = config["lane"]["profiles"]
    for lane in ["fast", "lite", "complex"]:
        assert_true(
            profiles[lane]["orchestration"]["mode"] == "ordered",
            f"{lane} profile 必须使用 ordered orchestration。",
        )
    lite_stages = {step["stage"] for step in profiles["lite"]["orchestration"]["steps"]}
    assert_true(
        {"planning", "implementation", "review", "verification", "fix"} <= lite_stages,
        "lite steps 必须覆盖 planning/implementation/review/verification/fix 五个 stage。",
    )
    complex_stages = {step["stage"] for step in profiles["complex"]["orchestration"]["steps"]}
    assert_true(
        {"planning", "implementation", "review", "verification", "fix", "completion"} <= complex_stages,
        "complex steps 必须覆盖 planning/implementation/review/verification/fix/completion 六个 stage。",
    )


ALIGNMENT_PIPELINE_STEPS = [
    ("alignment-discovery", "discovery", "intent_discovery", "raw_idea"),
    ("alignment-brainstorming", "divergence", "brainstorming", "alternatives_needed"),
    ("alignment-grilling", "clarification", "intent_grilling", "critical_gaps_remain"),
    ("alignment-grilling-with-docs", "clarification", "intent_grilling_with_docs", "docs_clarification_required"),
    ("alignment-check", "alignment_check", "intent_alignment", None),
]

ALIGNMENT_SKILL_REFS = {
    "intent_discovery": ".claude/skills/idc-intent-discovery/SKILL.md",
    "brainstorming": ".claude/skills/idc-brainstorming/SKILL.md",
    "intent_grilling": ".claude/skills/idc-intent-grilling/SKILL.md",
    "intent_grilling_with_docs": ".claude/skills/idc-intent-grilling-with-docs/SKILL.md",
    "intent_alignment": ".claude/skills/idc-intent-alignment/SKILL.md",
}


def build_alignment_section(bindings=None, steps=None, mode="ordered"):
    if bindings is None:
        bindings = ALIGNMENT_SKILL_REFS
    if steps is None:
        steps = ALIGNMENT_PIPELINE_STEPS
    lines = ["", "alignment:", "  bindings:"]
    for capability, skill_ref in bindings.items():
        lines.append(f"    {capability}: {{skill_ref: {skill_ref}}}")
    lines.append("  orchestration:")
    lines.append(f"    mode: {mode}")
    lines.append("    steps:")
    for step_id, stage, skill_id, signal in steps:
        signals = f"[{signal}]" if signal else "[]"
        lines.append(f"      - id: {step_id}")
        lines.append(f"        stage: {stage}")
        lines.append(f"        skill_ids: [{skill_id}]")
        lines.append(f"        trigger_signals: {signals}")
    return "\n".join(lines) + "\n"


def write_alignment_config(temp_dir, name, section_text):
    config_path = Path(temp_dir) / name
    config_path.write_text(
        (ROOT / "examples/team-config.full-bindings.yaml").read_text(encoding="utf-8") + section_text,
        encoding="utf-8",
    )
    return config_path


def run_alignment_resolver(config_path, output_path=None):
    command = ["ruby", str(ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"), "--config", str(config_path)]
    command += ["--output", str(output_path)] if output_path is not None else ["--check"]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def has_top_level_alignment(text):
    return re.search(r"^alignment:$", text, flags=re.MULTILINE) is not None


def test_alignment_pipeline_config_shape_mirrors_lane_profiles():
    template = read_text("team-config.yaml.template")
    schema = read_text(".claude/skills/idc-workflow/references/schemas/team-config.schema.yaml")

    assert_true(has_top_level_alignment(template), "team-config.yaml.template 必须提供顶层 alignment 段。")
    remainder = "alignment:\n" + re.split(r"^alignment:$", template, flags=re.MULTILINE)[1]
    alignment = yaml.safe_load(remainder)["alignment"]
    assert_true("bindings" in alignment, "alignment 段缺少 bindings。")
    assert_true("orchestration" in alignment, "alignment 段缺少 orchestration。")
    bindings = alignment["bindings"]
    assert_true(set(bindings) == set(ALIGNMENT_SKILL_REFS), f"alignment.bindings 能力键漂移：{sorted(bindings)}。")
    for capability, skill_ref in ALIGNMENT_SKILL_REFS.items():
        assert_true(bindings[capability].get("skill_ref") == skill_ref, f"alignment.bindings.{capability} 默认绑定漂移。")
    for capability, binding in bindings.items():
        assert_true(
            re.match(r"^\.claude/skills/idc-[a-z0-9-]+/SKILL\.md$", binding.get("skill_ref") or "") is not None,
            f"alignment.bindings.{capability} 必须绑定 .claude/skills/idc-*/SKILL.md 形态的 skill ref。",
        )
    orchestration = alignment["orchestration"]
    assert_true(orchestration.get("mode") == "ordered", "alignment.orchestration.mode 默认必须是 ordered。")
    serialized_steps = [
        (step.get("id"), step.get("stage"), step.get("skill_ids"), step.get("trigger_signals"))
        for step in orchestration.get("steps", [])
    ]
    expected_steps = [
        (step_id, stage, [skill_id], [signal] if signal else [])
        for step_id, stage, skill_id, signal in ALIGNMENT_PIPELINE_STEPS
    ]
    assert_true(serialized_steps == expected_steps, f"alignment.orchestration.steps 默认链漂移：{serialized_steps}。")
    for step_id, _, skill_ids, _ in serialized_steps:
        for skill_id in skill_ids:
            assert_true(skill_id in bindings, f"{step_id} 的 skill_ids 必须能在 alignment.bindings 解析：{skill_id}。")

    for fragment in ["alignment:", "skill_ids:", "trigger_signals:"]:
        assert_true(fragment in schema, f"team-config schema 必须同步定义 alignment 段形状：{fragment}")


def test_alignment_pipeline_framework_invariants_are_enforced():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"
    assert_true(resolver.exists(), "缺少 Team Config Resolver。")

    with tempfile.TemporaryDirectory() as temp_dir:
        canonical = write_alignment_config(temp_dir, "alignment-canonical.yaml", build_alignment_section())
        canonical_effective = Path(temp_dir) / "alignment-canonical-effective.yaml"
        canonical_resolved = run_alignment_resolver(canonical, canonical_effective)
        assert_true(canonical_resolved.returncode == 0, f"完整 alignment 配置必须通过 Resolver：{canonical_resolved.stderr}")
        canonical_text = canonical_effective.read_text(encoding="utf-8")
        for fragment in ["alignment-discovery", "alignment-brainstorming", "alignment-grilling", "alignment-grilling-with-docs", "alignment-check", "mode: ordered"]:
            assert_true(fragment in canonical_text, f"有效配置必须物化解析后的 alignment 管线：{fragment}")

        rebound = write_alignment_config(
            temp_dir,
            "alignment-rebound.yaml",
            build_alignment_section(bindings={**ALIGNMENT_SKILL_REFS, "intent_alignment": ".claude/skills/idc-gc-sop-adapter/SKILL.md"}),
        )
        rebound_checked = run_alignment_resolver(rebound)
        assert_true(rebound_checked.returncode == 0, f"alignment_check step 只能 rebind、不能删除，rebind 必须被接受：{rebound_checked.stderr}")

        unbound = write_alignment_config(
            temp_dir,
            "alignment-unbound.yaml",
            build_alignment_section(bindings={key: value for key, value in ALIGNMENT_SKILL_REFS.items() if key != "intent_discovery"}),
        )
        unbound_checked = run_alignment_resolver(unbound)
        assert_true(unbound_checked.returncode != 0, "step 引用未绑定 skill 时不得静默放行。")
        assert_true(
            "NEEDS_TEAM_CONFIG" in unbound_checked.stderr and "intent_discovery" in unbound_checked.stderr,
            f"未解析 skill 必须返回 NEEDS_TEAM_CONFIG 有界错误：{unbound_checked.stderr}",
        )

        missing_stage = write_alignment_config(
            temp_dir,
            "alignment-missing-stage.yaml",
            build_alignment_section(steps=[step for step in ALIGNMENT_PIPELINE_STEPS if step[1] != "clarification"]),
        )
        missing_stage_checked = run_alignment_resolver(missing_stage)
        assert_true(missing_stage_checked.returncode != 0, "ordered alignment 缺失 stage 映射时不得静默回落。")
        assert_true(
            "NEEDS_ORCHESTRATION_MAPPING" in missing_stage_checked.stderr and "clarification" in missing_stage_checked.stderr,
            f"缺失 stage 映射必须对齐 lane 的 NEEDS_ORCHESTRATION_MAPPING 阻断规则：{missing_stage_checked.stderr}",
        )

        gate_removed = write_alignment_config(
            temp_dir,
            "alignment-gate-removed.yaml",
            build_alignment_section(steps=ALIGNMENT_PIPELINE_STEPS[:4]),
        )
        gate_removed_checked = run_alignment_resolver(gate_removed)
        assert_true(gate_removed_checked.returncode != 0, "alignment_check step 不可删除。")
        assert_true(
            "alignment_check" in gate_removed_checked.stderr and "cannot be removed" in gate_removed_checked.stderr,
            f"Human Alignment gate step 删除必须被明确拒绝：{gate_removed_checked.stderr}",
        )

        no_raw_idea = write_alignment_config(
            temp_dir,
            "alignment-no-raw-idea.yaml",
            build_alignment_section(steps=[(*ALIGNMENT_PIPELINE_STEPS[0][:3], None)] + list(ALIGNMENT_PIPELINE_STEPS[1:])),
        )
        no_raw_idea_checked = run_alignment_resolver(no_raw_idea)
        assert_true(no_raw_idea_checked.returncode != 0, "raw_idea 信号下限不得被移除。")
        assert_true(
            "raw_idea" in no_raw_idea_checked.stderr and "trigger_signals" in no_raw_idea_checked.stderr,
            f"raw_idea 必须被至少一个 step 的 trigger_signals 覆盖：{no_raw_idea_checked.stderr}",
        )

        no_gap_signal = write_alignment_config(
            temp_dir,
            "alignment-no-gap-signal.yaml",
            build_alignment_section(steps=[(step[0], step[1], step[2], None if step[3] == "critical_gaps_remain" else step[3]) for step in ALIGNMENT_PIPELINE_STEPS]),
        )
        no_gap_signal_checked = run_alignment_resolver(no_gap_signal)
        assert_true(
            no_gap_signal_checked.returncode != 0 and "critical_gaps_remain" in no_gap_signal_checked.stderr,
            f"critical_gaps_remain 必须被至少一个 step 的 trigger_signals 覆盖：{no_gap_signal_checked.stderr}",
        )

        non_idc_ref = write_alignment_config(
            temp_dir,
            "alignment-non-idc.yaml",
            build_alignment_section(bindings={**ALIGNMENT_SKILL_REFS, "brainstorming": "docs/architecture.md"}),
        )
        non_idc_checked = run_alignment_resolver(non_idc_ref)
        assert_true(non_idc_checked.returncode != 0, "alignment 绑定不得脱离 idc- skill 形态。")
        assert_true(
            "alignment.bindings" in non_idc_checked.stderr and "idc-" in non_idc_checked.stderr,
            f"alignment 绑定的 skill_ref 必须保持 .claude/skills/idc-*/SKILL.md 形态：{non_idc_checked.stderr}",
        )

        partial = write_alignment_config(temp_dir, "alignment-partial.yaml", build_alignment_section().split("  orchestration:", 1)[0])
        partial_effective = Path(temp_dir) / "alignment-partial-effective.yaml"
        partial_resolved = run_alignment_resolver(partial, partial_effective)
        assert_true(partial_resolved.returncode == 0, f"缺少 orchestration 的 alignment 段必须回落框架默认链：{partial_resolved.stderr}")
        partial_text = partial_effective.read_text(encoding="utf-8")
        assert_true("alignment-discovery" in partial_text and "alignment-check" in partial_text, "回落后必须物化默认 alignment 链。")


def test_alignment_pipeline_runtime_consumption_is_materialized():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"
    preflight = ROOT / ".claude/skills/idc-team-config/scripts/prepare_runtime.rb"
    context_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_context.rb"
    config = ROOT / "examples/team-config.full-bindings.yaml"
    effective_schema = read_text(".claude/skills/idc-workflow/references/schemas/effective-team-config.schema.yaml")

    with tempfile.TemporaryDirectory() as temp_dir:
        default_config = Path(temp_dir) / "alignment-default-general.yaml"
        default_config.write_text(
            config.read_text(encoding="utf-8").replace("mode: d3a", "mode: general", 1),
            encoding="utf-8",
        )
        default_effective = Path(temp_dir) / "alignment-default-effective.yaml"
        default_resolved = run_alignment_resolver(default_config, default_effective)
        assert_true(default_resolved.returncode == 0, f"未配置 alignment 段的解析失败：{default_resolved.stderr}")
        default_text = default_effective.read_text(encoding="utf-8")
        assert_true(has_top_level_alignment(default_text), "未配置 alignment 段时 effective-team-config 必须物化框架默认链。")
        assert_true("alignment-discovery" in default_text and "alignment-check" in default_text, "默认 alignment 链必须包含 discovery 与 alignment_check step。")

        preflight_effective = Path(temp_dir) / "alignment-preflight-effective.yaml"
        preflight_run = subprocess.run(
            ["ruby", str(preflight), "--config", str(config), "--output", str(preflight_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(preflight_run.returncode == 0 and "status: READY" in preflight_run.stdout, f"未配置 alignment 段时 preflight 必须保持 READY：{preflight_run.stdout}")
        assert_true("alignment_policy_check_count: 5" in preflight_run.stdout, "preflight 必须输出 alignment_policy_checks（每 step dry-run）。")
        alignment_checks = preflight_run.stdout.split("alignment_policy_checks:", 1)[1]
        assert_true(alignment_checks.count("status: PASS") == 5, "每个 alignment step 的 dry-run（绑定解析、序 emitted、信号下限）必须 PASS。")

        decision_default = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(default_effective), "--phase", "decision", "--domain", "general"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(decision_default.returncode == 0, f"decision Context Plan 失败：{decision_default.stdout}{decision_default.stderr}")
        assert_true(".claude/skills/idc-intent-alignment/SKILL.md" in decision_default.stdout, "未配置 alignment 段时 decision 意图 refs 必须与当前硬编码列表等价。")

        configured = write_alignment_config(temp_dir, "alignment-configured.yaml", build_alignment_section())
        configured.write_text(
            configured.read_text(encoding="utf-8").replace("mode: d3a", "mode: general", 1),
            encoding="utf-8",
        )
        configured_effective = Path(temp_dir) / "alignment-configured-effective.yaml"
        configured_resolved = run_alignment_resolver(configured, configured_effective)
        assert_true(configured_resolved.returncode == 0, f"显式 alignment 配置解析失败：{configured_resolved.stderr}")
        decision_configured = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(configured_effective), "--phase", "decision", "--domain", "general"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(decision_configured.returncode == 0, f"配置化 alignment 的 decision Context Plan 失败：{decision_configured.stdout}{decision_configured.stderr}")
        for skill_ref in ALIGNMENT_SKILL_REFS.values():
            assert_true(skill_ref in decision_configured.stdout, f"decision 阶段意图类 required_refs 必须从 effective alignment 管线推导：{skill_ref}")

        assert_true(has_top_level_alignment(effective_schema), "effective-team-config schema 必须定义物化后的 alignment 管线。")


def test_alignment_pipeline_docs_record_section_and_ownership():
    docs = {
        "idc-workflow": read_text(".claude/skills/idc-workflow/SKILL.md"),
        "idc-team-config": read_text(".claude/skills/idc-team-config/SKILL.md"),
        "README": read_text("README.md"),
        "team-config.yaml.template": read_text("team-config.yaml.template"),
    }
    for name, text in docs.items():
        assert_true(has_top_level_alignment(text), f"{name} 必须记录 alignment 配置段。")
        assert_true(
            "不可配置" in text or "not configurable" in text or "cannot be configured" in text,
            f"{name} 必须记录 router / gate 所有权不可配置的边界。",
        )
        assert_true(
            "回落" in text or "default alignment" in text or "framework default" in text,
            f"{name} 必须记录未配置 alignment 段时的框架默认回落行为。",
        )


def test_alignment_pipeline_execution_defers_to_config_not_hardcoded():
    workflow_text = read_text(".claude/skills/idc-workflow/SKILL.md")

    bypass_lines = [
        "idc-intent-grilling if critical gaps remain",
        "idc-intent-grilling-with-docs if clarification must update docs",
        "only when clarification should create non-sensitive decision records",
    ]
    for bypass in bypass_lines:
        assert_true(
            bypass not in workflow_text,
            f"idc-workflow 路由块不得保留写死的 signal→skill 旁路行：{bypass}",
        )

    assert_true(
        "effective.alignment.orchestration.steps" in workflow_text,
        "idc-workflow 必须以 effective alignment pipeline 的 steps 作为 pre-alignment 唯一源。",
    )

    assert_true(
        len(workflow_text.splitlines()) <= 320,
        "idc-workflow 入口说明重新膨胀，破坏 progressive disclosure。",
    )


def test_team_config_resolver_and_lane_capability_selection_execute():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"
    selector = ROOT / ".claude/skills/idc-team-config/scripts/select_capabilities.rb"
    preflight = ROOT / ".claude/skills/idc-team-config/scripts/prepare_runtime.rb"
    context_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_context.rb"
    knowledge_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_knowledge.rb"
    config = ROOT / "examples/team-config.full-bindings.yaml"
    assert_true(resolver.exists() and selector.exists() and preflight.exists() and context_planner.exists() and knowledge_planner.exists(), "单配置 Preflight / Resolver / Capability Selector / Knowledge / Context Planner 脚本缺失。")

    with tempfile.TemporaryDirectory() as temp_dir:
        effective = Path(temp_dir) / "effective.yaml"
        resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(config), "--output", str(effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(resolved.returncode == 0, f"team-config Resolver 执行失败：{resolved.stderr}")
        effective_text = effective.read_text(encoding="utf-8")
        assert_true("source_sha256:" in effective_text, "有效配置必须记录源 YAML digest，避免陈旧运行态。")
        assert_true("available_capabilities:" in effective_text, "有效配置必须物化已绑定 capabilities。")
        assert_true(effective_text.count("source: fixed-binding") == 20, "20 个绑定必须全部进入 available capabilities。")
        assert_true("source: adapter-extension" in effective_text and "idc-team-api-review" in effective_text, "团队 adapter extension 必须进入有效候选池。")
        assert_true("registration_audit:" in effective_text and "status: PASS" in effective_text, "有效配置必须通过 Skill Registration Audit。")
        assert_true("fast-implement" in effective_text and "complex-plan" in effective_text, "每个 Lane 的 Skill 编排必须物化进有效配置。")

        general_config = Path(temp_dir) / "team-config-general.yaml"
        general_config.write_text(
            config.read_text(encoding="utf-8").replace("mode: d3a", "mode: general", 1),
            encoding="utf-8",
        )
        general_effective = Path(temp_dir) / "general-effective.yaml"
        general_resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(general_config), "--output", str(general_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(general_resolved.returncode == 0, f"General 模式变体解析失败：{general_resolved.stderr}")

        decision_without_lane = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(general_effective), "--phase", "decision", "--domain", "general"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(decision_without_lane.returncode == 0 and "status: READY" in decision_without_lane.stdout, f"decision 阶段不应强制 --lane：{decision_without_lane.stdout}")
        assert_true("lane-resolver.md" in decision_without_lane.stdout, "decision 阶段必须加载 Lane Resolver。")
        planning_without_lane = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(general_effective), "--phase", "planning", "--domain", "general"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(planning_without_lane.returncode == 2 and "--lane is required" in planning_without_lane.stdout, "planning 起必须强制 --lane。")

        expected = {
            "fast": (1, ["coding_standard"]),
            "lite": (4, ["tech_design", "phase_plan"]),
            "complex": (5, ["tech_design", "phase_plan", "scene_challenge"]),
            "d3a": (2, ["dt_design", "ut_design"]),
        }
        for name, (count, ids) in expected.items():
            result = subprocess.run(
                ["ruby", str(selector), "--effective", str(effective), "--demand", str(ROOT / f"examples/capability-demands/{name}.yaml")],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert_true(result.returncode == 0, f"{name} Capability Selection 失败：{result.stderr}")
            assert_true(result.stdout.count("capability_id:") >= count, f"{name} 没有输出足够的 selection/skip decision。")
            selected_block = result.stdout.split("skipped:", 1)[0]
            assert_true(selected_block.count("capability_id:") == count, f"{name} 选择数量错误，期望 {count}。")
            for capability_id in ids:
                assert_true(f"capability_id: {capability_id}" in selected_block, f"{name} 应选择 {capability_id}。")
            assert_true("status: READY" in result.stdout, f"{name} selection 必须 READY。")

        fast_result = subprocess.run(
            ["ruby", str(selector), "--effective", str(effective), "--demand", str(ROOT / "examples/capability-demands/fast.yaml")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true("mode: ordered" in fast_result.stdout and "fast-implement" in fast_result.stdout, "Fast 必须执行团队 ordered orchestration。")
        assert_true("requirement: configured" in fast_result.stdout and "execution_order: 1" in fast_result.stdout, "配置步骤必须成为有顺序的实际选择。")

        missing_stage_demand = Path(temp_dir) / "fast-review.yaml"
        missing_stage_demand.write_text(
            """capability_demand:
  selected_stage: review
  selected_domain: general
  lane_applicability: applicable
  selected_lane: fast
  execution_profile: lane_driven
  required_capability_keys: []
  optional_capability_keys: []
  observed_signals: []
  contract_refs: []
""",
            encoding="utf-8",
        )
        missing_stage = subprocess.run(
            ["ruby", str(selector), "--effective", str(effective), "--demand", str(missing_stage_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(missing_stage.returncode == 3 and "NEEDS_ORCHESTRATION_MAPPING" in missing_stage.stdout, "ordered Lane 缺少当前 stage 时必须阻断，不能静默回退。")

        denied_demand = Path(temp_dir) / "complex-finishing.yaml"
        denied_demand.write_text(
            """capability_demand:
  selected_stage: finishing
  selected_domain: general
  lane_applicability: applicable
  selected_lane: complex
  execution_profile: lane_driven
  required_capability_keys: [atomic_commit]
  optional_capability_keys: []
  observed_signals: [atomic_commit_required]
  contract_refs: []
""",
            encoding="utf-8",
        )
        denied = subprocess.run(
            ["ruby", str(selector), "--effective", str(effective), "--demand", str(denied_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(denied.returncode == 2 and "team_lane_denied" in denied.stdout, "Lane deny 配置必须真正排除 Skill。")
        assert_true("status: NEEDS_ADAPTER_MAPPING" in denied.stdout, "被 deny 的必需能力不得从默认 registry 偷偷补回。")

        invalid = Path(temp_dir) / "invalid.yaml"
        invalid.write_text(config.read_text(encoding="utf-8") + "\ncommand: forbidden\n", encoding="utf-8")
        rejected = subprocess.run(
            ["ruby", str(resolver), "--config", str(invalid), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(rejected.returncode != 0 and "is forbidden" in rejected.stderr, "Resolver 必须拒绝命令键。")

        unknown_lane_skill = Path(temp_dir) / "unknown-lane-skill.yaml"
        unknown_lane_skill.write_text(config.read_text(encoding="utf-8").replace("allow: [coding_standard, static_scan, defect_fix]", "allow: [coding_standard, idc-not-bound]", 1), encoding="utf-8")
        unknown_rejected = subprocess.run(
            ["ruby", str(resolver), "--config", str(unknown_lane_skill), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(unknown_rejected.returncode != 0 and "references unavailable skill ID: idc-not-bound" in unknown_rejected.stderr, "Lane 引用未绑定 Skill 时 Resolver 必须拒绝。")

        protected_binding = Path(temp_dir) / "protected-domain-skill-binding.yaml"
        protected_binding.write_text(
            config.read_text(encoding="utf-8").replace(
                "coding_standard: {skill_ref: .claude/skills/idc-gc-sop-adapter/SKILL.md}",
                "coding_standard: {skill_ref: .claude/skills/idc-general-coding/SKILL.md}",
                1,
            ),
            encoding="utf-8",
        )
        protected_rejected = subprocess.run(
            ["ruby", str(resolver), "--config", str(protected_binding), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(protected_rejected.returncode != 0 and "binds an orchestration/domain Skill as an atomic capability" in protected_rejected.stderr, "General Coding 等外层 Skill 不得注册进原子 binding。")

        overlap_row = """  - id: idc-overlap-coding
    execution_role: atomic_capability
    capability_keys: [coding_standard]
    allowed_stages: [implementation]
    eligible_lanes: [complex]
    execution_profiles: []
    trigger_signals: [implementation_required]
    skill_ref: .claude/skills/idc-gc-sop-adapter/SKILL.md
    evidence_required: true
    composes_with: []
    supersedes: []
"""
        ambiguous_config = Path(temp_dir) / "ambiguous-registration.yaml"
        ambiguous_config.write_text(config.read_text(encoding="utf-8").replace("adapter_extensions:\n", "adapter_extensions:\n" + overlap_row, 1), encoding="utf-8")
        ambiguous = subprocess.run(
            ["ruby", str(resolver), "--config", str(ambiguous_config), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(ambiguous.returncode != 0 and "ambiguous capability registration" in ambiguous.stderr, "未声明策略的 capability/stage/scope/trigger 重叠必须被拒绝。")

        pre_alignment_overlap = overlap_row.replace("idc-overlap-coding", "idc-overlap-brainstorming")
        pre_alignment_overlap = pre_alignment_overlap.replace("execution_role: atomic_capability", "execution_role: pre_alignment_capability")
        pre_alignment_overlap = pre_alignment_overlap.replace("[coding_standard]", "[brainstorming]")
        pre_alignment_overlap = pre_alignment_overlap.replace("[implementation]", "[discovery]")
        pre_alignment_overlap = pre_alignment_overlap.replace("[complex]", "[]")
        pre_alignment_overlap = pre_alignment_overlap.replace("[implementation_required]", "[input_maturity_raw_idea]")
        pre_alignment_config = Path(temp_dir) / "ambiguous-pre-alignment.yaml"
        pre_alignment_config.write_text(config.read_text(encoding="utf-8").replace("adapter_extensions:\n", "adapter_extensions:\n" + pre_alignment_overlap, 1), encoding="utf-8")
        pre_alignment_rejected = subprocess.run(
            ["ruby", str(resolver), "--config", str(pre_alignment_config), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(pre_alignment_rejected.returncode != 0 and "ambiguous capability registration" in pre_alignment_rejected.stderr, "无 Lane 的 Pre-alignment capability 重叠也必须被检测。")

        composed_config = Path(temp_dir) / "composed-registration.yaml"
        composed_config.write_text(ambiguous_config.read_text(encoding="utf-8").replace("composes_with: []", "composes_with: [coding_standard]", 1), encoding="utf-8")
        composed_effective = Path(temp_dir) / "composed-effective.yaml"
        composed = subprocess.run(
            ["ruby", str(resolver), "--config", str(composed_config), "--output", str(composed_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(composed.returncode == 0 and "resolution: compose" in composed_effective.read_text(encoding="utf-8"), "显式 composes_with 必须允许有意组合。")

        superseding_config = Path(temp_dir) / "superseding-registration.yaml"
        superseding_config.write_text(ambiguous_config.read_text(encoding="utf-8").replace("supersedes: []", "supersedes: [coding_standard]", 1), encoding="utf-8")
        superseding_effective = Path(temp_dir) / "superseding-effective.yaml"
        superseding = subprocess.run(
            ["ruby", str(resolver), "--config", str(superseding_config), "--output", str(superseding_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(superseding.returncode == 0, "显式 supersedes 必须通过 Registration Audit。")
        complex_impl_demand = Path(temp_dir) / "complex-implementation.yaml"
        complex_impl_demand.write_text(
            """capability_demand:
  selected_stage: implementation
  selected_domain: general
  lane_applicability: applicable
  selected_lane: complex
  execution_profile: lane_driven
  required_capability_keys: [coding_standard]
  optional_capability_keys: []
  observed_signals: [implementation_required]
  contract_refs: []
""",
            encoding="utf-8",
        )
        superseded_selection = subprocess.run(
            ["ruby", str(selector), "--effective", str(superseding_effective), "--demand", str(complex_impl_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(superseded_selection.returncode == 0 and "capability_id: idc-overlap-coding" in superseded_selection.stdout, "superseding Skill 必须进入真实选择结果。")
        assert_true("capability_id: coding_standard" in superseded_selection.stdout and "reason: superseded" in superseded_selection.stdout, "被替代 Skill 必须明确记录 superseded。")

        zero_budget_config = Path(temp_dir) / "zero-lite-budget.yaml"
        zero_budget_config.write_text(config.read_text(encoding="utf-8").replace("lite: {max_optional_skills: 3}", "lite: {max_optional_skills: 0}"), encoding="utf-8")
        zero_budget_effective = Path(temp_dir) / "zero-lite-budget-effective.yaml"
        zero_budget_resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(zero_budget_config), "--output", str(zero_budget_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(zero_budget_resolved.returncode == 0, "团队必须能够调整任意 Lane 的 optional Skill budget。")
        zero_budget_selected = subprocess.run(
            ["ruby", str(selector), "--effective", str(zero_budget_effective), "--demand", str(ROOT / "examples/capability-demands/lite.yaml")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        zero_selected_block = zero_budget_selected.stdout.split("skipped:", 1)[0]
        assert_true(zero_selected_block.count("capability_id:") == 2, "Lite budget=0 时只能保留团队编排的两个 Skill。")
        assert_true("optional_budget_exhausted" in zero_budget_selected.stdout, "调整后的 Lane budget 必须在运行时生效。")

        legacy_config = Path(temp_dir) / "legacy-v1.yaml"
        legacy_text = re.sub(r"lane:\n  default: lite\n  profiles:.*?\ncapability_selection:", "lane:\n  default: lite\ncapability_selection:", config.read_text(encoding="utf-8"), flags=re.S)
        legacy_config.write_text(legacy_text, encoding="utf-8")
        legacy_effective = Path(temp_dir) / "legacy-effective.yaml"
        legacy_resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(legacy_config), "--output", str(legacy_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(legacy_resolved.returncode == 0, "缺少 lane.profiles 的旧 V1 配置必须保持兼容。")
        assert_true("profiles:" in legacy_effective.read_text(encoding="utf-8"), "Resolver 必须为旧配置物化 autonomous Lane profiles。")

        team_repo = Path(temp_dir) / "second-team-repo"
        team_skill = team_repo / "skills/team-coding/SKILL.md"
        team_skill.parent.mkdir(parents=True)
        team_skill.write_text("---\nname: team-coding\ndescription: portable test skill\n---\n", encoding="utf-8")
        portable_config = Path(temp_dir) / "team-config.yaml"
        portable_text = config.read_text(encoding="utf-8")
        portable_text = portable_text.replace("repo_path: .", f"repo_path: {team_repo}", 1)
        portable_text = portable_text.replace(
            "coding_standard: {skill_ref: .claude/skills/idc-gc-sop-adapter/SKILL.md}",
            "coding_standard: {skill_ref: 'team://skills/team-coding/SKILL.md'}",
            1,
        )
        portable_text = portable_text.replace(
            "static_scan: {skill_ref: .claude/skills/idc-gc-sop-adapter/SKILL.md}",
            "static_scan: {skill_ref: 'harness://.claude/skills/idc-gc-sop-adapter/SKILL.md'}",
            1,
        )
        portable_config.write_text(portable_text, encoding="utf-8")
        portable_effective = Path(temp_dir) / "portable-effective.yaml"
        portable_preflight = subprocess.run(
            ["ruby", str(preflight), "--config", str(portable_config), "--output", str(portable_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(
            portable_preflight.returncode == 0 and "status: READY" in portable_preflight.stdout,
            f"第二团队只填 YAML 后，自动 preflight 必须 READY：{portable_preflight.stdout}\n{portable_preflight.stderr}",
        )
        assert_true("registration_audit_status: PASS" in portable_preflight.stdout, "第二团队配置必须通过 Skill Registration Audit。")
        assert_true("lane_policy_check_count: 6" in portable_preflight.stdout, "Preflight 必须用真实 Selector 验证三个 Lane 的 steps 与 required Skills。")
        bootstrap_block = portable_preflight.stdout.split("bootstrap_load_plan:", 1)[1].split("lane_policy_check_count:", 1)[0]
        assert_true("load_policy: read_required_refs_only" in bootstrap_block, "Preflight 必须输出机器化 bootstrap Context Load Plan。")
        assert_true(bootstrap_block.count("    - ") == 3, "Bootstrap 只能加载 Input / Scenario / Domain Router 三个最小引用。")
        assert_true("skill-adapters.yaml" not in bootstrap_block and "idc-general-coding/SKILL.md" not in bootstrap_block, "Bootstrap 不得预加载 registry 或 Domain execution Skill。")
        portable_effective_text = portable_effective.read_text(encoding="utf-8")
        assert_true(str(team_skill) in portable_effective_text, "team:// Skill 必须按第二团队 repo_path 解析为绝对路径。")
        harness_skill = ROOT / ".claude/skills/idc-gc-sop-adapter/SKILL.md"
        assert_true(str(harness_skill) in portable_effective_text, "harness:// Skill 必须按 IDC Core root 解析为绝对路径。")
        assert_true(not list(portable_effective.parent.glob(".*effective*.tmp-*")), "Resolver 原子写入后不得残留临时配置。")
        portable_selection = subprocess.run(
            ["ruby", str(selector), "--effective", str(portable_effective), "--demand", str(ROOT / "examples/capability-demands/fast.yaml")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(portable_selection.returncode == 0 and str(team_skill) in portable_selection.stdout, "跨团队 Skill 绝对路径必须进入真实选择结果。")

        missing_preflight = subprocess.run(
            ["ruby", str(preflight), "--config", str(Path(temp_dir) / "missing.yaml"), "--output", str(Path(temp_dir) / "missing-effective.yaml")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(missing_preflight.returncode == 2 and "NEEDS_TEAM_CONFIG" in missing_preflight.stdout, "缺少 team-config.yaml 时必须阻断，不能使用 template 或旧 runtime fallback。")

        missing_knowledge_config = Path(temp_dir) / "missing-knowledge.yaml"
        missing_knowledge_config.write_text(
            portable_text.replace("architecture_doc_ref: docs/architecture.md", "architecture_doc_ref: 'team://docs/missing-architecture.md'", 1),
            encoding="utf-8",
        )
        missing_knowledge = subprocess.run(
            ["ruby", str(preflight), "--config", str(missing_knowledge_config), "--output", str(Path(temp_dir) / "missing-knowledge-effective.yaml")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(missing_knowledge.returncode != 0 and "knowledge.architecture_doc_ref does not exist" in missing_knowledge.stdout, "错误的本地 knowledge ref 必须在 preflight 阶段暴露。")

        minimal_effective = Path(temp_dir) / "minimal-effective.yaml"
        minimal_preflight = subprocess.run(
            ["ruby", str(preflight), "--config", str(ROOT / "examples/team-config.minimal.yaml"), "--output", str(minimal_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(minimal_preflight.returncode == 0 and "status: READY" in minimal_preflight.stdout, "最小 General team-config 必须无需额外配置即可 preflight READY。")
        minimal_text = minimal_effective.read_text(encoding="utf-8")
        for fragment in ["default: lite", "mode: autonomous", "mode: disabled", "max_optional_skills: 1"]:
            assert_true(fragment in minimal_text, f"最小配置必须物化安全默认值：{fragment}")

        custom_effective = Path(temp_dir) / "custom-effective.yaml"
        custom = subprocess.run(
            ["ruby", str(resolver), "--config", str(ROOT / "examples/team-config.custom-domain.yaml"), "--output", str(custom_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(custom.returncode == 0, f"Custom Domain 单配置解析失败：{custom.stderr}")
        custom_text = custom_effective.read_text(encoding="utf-8")
        assert_true("source: team-config-inline" in custom_text and "id: demo-payment" in custom_text, "Custom Domain 必须从 team-config 内联物化。")

        decision_plan = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(general_effective), "--phase", "decision", "--domain", "general", "--lane", "fast"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(decision_plan.returncode == 0 and "status: READY" in decision_plan.stdout, f"General Decision Context Plan 失败：{decision_plan.stdout}\n{decision_plan.stderr}")
        assert_true("domains/general/module.yaml" in decision_plan.stdout and "lanes/fast.yaml" in decision_plan.stdout, "Decision 阶段必须加载命中的 Domain 与 Lane。")
        assert_true("domains/d3a/module.yaml" not in decision_plan.stdout and "idc-gc-sop-adapter/SKILL.md" not in decision_plan.stdout, "Decision 阶段不得预加载 D3A 或执行 adapter。")

        d3a_plan = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(effective), "--phase", "planning", "--domain", "d3a"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(d3a_plan.returncode == 0 and "d3a-planning-constraints.yaml" in d3a_plan.stdout, "D3A Planning 必须在无 Lane 参数时生成固定流程上下文。")
        assert_true("lanes/fast.yaml" not in d3a_plan.stdout and "lane-resolver.md" not in d3a_plan.stdout, "D3A 不得加载动态 Lane 上下文。")

        selection_file = Path(temp_dir) / "fast-selection.yaml"
        selected = subprocess.run(
            ["ruby", str(selector), "--effective", str(general_effective), "--demand", str(ROOT / "examples/capability-demands/fast.yaml"), "--output", str(selection_file)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(selected.returncode == 0, f"Context Planner 测试准备 selection 失败：{selected.stderr}")
        knowledge_plan_file = Path(temp_dir) / "fast-knowledge-plan.yaml"
        knowledge_planned = subprocess.run(
            ["ruby", str(knowledge_planner), "--effective", str(general_effective), "--demand", str(ROOT / "examples/knowledge-demands/fast.yaml"), "--output", str(knowledge_plan_file)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(knowledge_planned.returncode == 0, f"Context Planner 测试准备 Knowledge Plan 失败：{knowledge_planned.stderr}")
        execution_plan = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(general_effective), "--phase", "execution", "--domain", "general", "--lane", "fast", "--selection", str(selection_file), "--knowledge-plan", str(knowledge_plan_file)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(execution_plan.returncode == 0 and "status: READY" in execution_plan.stdout, f"Execution Context Plan 失败：{execution_plan.stdout}\n{execution_plan.stderr}")
        assert_true("capability_id: coding_standard" in execution_plan.stdout and "idc-general-coding/SKILL.md" in execution_plan.stdout, "Execution 必须加载 Domain protocol 与真实选中能力。")
        assert_true("knowledge_plan_id:" in execution_plan.stdout and "kind: component" in execution_plan.stdout and "kind: test_domain" in execution_plan.stdout, "Execution Context Plan 必须绑定当前单元的 Knowledge Plan。")
        assert_true("capability_id: dt_build" not in execution_plan.stdout and "idc-d3a-coding/SKILL.md" not in execution_plan.stdout, "Fast General execution 不得加载未选中的 DT/D3A Skill。")

        missing_selection = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(general_effective), "--phase", "execution", "--domain", "general", "--lane", "fast", "--knowledge-plan", str(knowledge_plan_file)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(missing_selection.returncode != 0 and "--selection is required for execution" in missing_selection.stdout, "Execution 不得绕过 Capability Selector 直接生成加载计划。")

        missing_knowledge_plan = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(general_effective), "--phase", "execution", "--domain", "general", "--lane", "fast", "--selection", str(selection_file)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(missing_knowledge_plan.returncode != 0 and "--knowledge-plan is required for execution" in missing_knowledge_plan.stdout, "Execution 不得绕过 Knowledge Planner 直接生成加载计划。")

        custom_plan = subprocess.run(
            ["ruby", str(context_planner), "--effective", str(custom_effective), "--phase", "planning", "--domain", "custom", "--lane", "lite"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(custom_plan.returncode == 0 and ".claude/skills/idc-general-coding/SKILL.md" in custom_plan.stdout, "Custom Domain 必须按阶段加载 team-config 绑定的 planner Skill。")
        custom_knowledge_demand = Path(temp_dir) / "custom-knowledge-demand.yaml"
        custom_knowledge_demand.write_text(
            """knowledge_demand:
  execution_unit_ref: custom-payment-unit
  selected_domain: custom
  selected_layer: PAYMENT_API
  selected_components: []
  selected_test_domains: [PAYMENT_TEST]
  include_architecture: true
  include_feature_docs_scope: false
  include_verification_mapping: false
  repo_context_required: false
""",
            encoding="utf-8",
        )
        custom_knowledge_plan = subprocess.run(
            ["ruby", str(knowledge_planner), "--effective", str(custom_effective), "--demand", str(custom_knowledge_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(custom_knowledge_plan.returncode == 0 and "status: READY" in custom_knowledge_plan.stdout, f"Custom Domain Knowledge Plan 失败：{custom_knowledge_plan.stdout}\n{custom_knowledge_plan.stderr}")
        assert_true("id: PAYMENT_API" in custom_knowledge_plan.stdout and "id: PAYMENT_TEST" in custom_knowledge_plan.stdout, "Custom Domain Knowledge Plan 必须选择当前 layer/test-domain knowledge。")

        workflow_text = read_text(".claude/skills/idc-workflow/SKILL.md")
        assert_true("Read these files first" not in workflow_text, "idc-workflow 不得保留全量首读清单。")
        assert_true(len(workflow_text.splitlines()) <= 320, "idc-workflow 入口说明重新膨胀，破坏 progressive disclosure。")


def can_enter_all_layers_green(required_domains, green_domains):
    return set(required_domains) <= set(green_domains)


def test_d3a_and_general_lane_runtime_matrix_execute():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"
    selector = ROOT / ".claude/skills/idc-team-config/scripts/select_capabilities.rb"
    knowledge_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_knowledge.rb"
    knowledge_verifier = ROOT / ".claude/skills/idc-team-config/scripts/verify_knowledge_consumption.rb"
    context_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_context.rb"
    authorizer = ROOT / ".claude/skills/idc-workflow/scripts/authorize_execution.rb"
    matrix = {
        "fast": {"domain": "general", "lane": "fast", "unit": "fast-unit", "selected": 1, "domain_skill": ".claude/skills/idc-general-coding/SKILL.md"},
        "lite": {"domain": "general", "lane": "lite", "unit": "lite-unit", "selected": 4, "domain_skill": ".claude/skills/idc-general-coding/SKILL.md"},
        "complex": {"domain": "general", "lane": "complex", "unit": "complex-unit", "selected": 5, "domain_skill": ".claude/skills/idc-general-coding/SKILL.md"},
        "d3a": {"domain": "d3a", "lane": None, "unit": "d3a-do-unit", "selected": 2, "domain_skill": ".claude/skills/idc-d3a-coding/SKILL.md"},
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        effective = Path(temp_dir) / "effective.yaml"
        resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(ROOT / "examples/team-config.full-bindings.yaml"), "--output", str(effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(resolved.returncode == 0, f"Runtime matrix Resolver 失败：{resolved.stderr}")

        general_config = Path(temp_dir) / "team-config-general.yaml"
        general_config.write_text(
            (ROOT / "examples/team-config.full-bindings.yaml").read_text(encoding="utf-8").replace("mode: d3a", "mode: general", 1),
            encoding="utf-8",
        )
        general_effective = Path(temp_dir) / "general-effective.yaml"
        general_resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(general_config), "--output", str(general_effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(general_resolved.returncode == 0, f"Runtime matrix General 模式变体解析失败：{general_resolved.stderr}")

        for scenario, expected in matrix.items():
            # plan_context 的 domain gate 要求 --domain 与 effective domain 一致：
            # general 场景用 general 模式 effective，d3a 场景用 full-bindings 的 d3a effective。
            scenario_effective = general_effective if expected["domain"] == "general" else effective
            selection = Path(temp_dir) / f"{scenario}-selection.yaml"
            selected = subprocess.run(
                ["ruby", str(selector), "--effective", str(scenario_effective), "--demand", str(ROOT / f"examples/capability-demands/{scenario}.yaml"), "--output", str(selection)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert_true(selected.returncode == 0, f"{scenario} Selector 失败：{selected.stdout}\n{selected.stderr}")
            selection_text = selection.read_text(encoding="utf-8")
            selected_block = selection_text.split("skipped:", 1)[0]
            assert_true("status: READY" in selection_text, f"{scenario} Selector 未 READY。")
            assert_true(selected_block.count("capability_id:") == expected["selected"], f"{scenario} 选择数量错误。")

            knowledge_plan = Path(temp_dir) / f"{scenario}-knowledge-plan.yaml"
            knowledge_planned = subprocess.run(
                ["ruby", str(knowledge_planner), "--effective", str(scenario_effective), "--demand", str(ROOT / f"examples/knowledge-demands/{scenario}.yaml"), "--output", str(knowledge_plan)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert_true(knowledge_planned.returncode == 0, f"{scenario} Knowledge Plan 失败：{knowledge_planned.stdout}\n{knowledge_planned.stderr}")
            knowledge_text = knowledge_plan.read_text(encoding="utf-8")
            assert_true("status: READY" in knowledge_text and f"execution_unit_ref: {expected['unit']}" in knowledge_text, f"{scenario} Knowledge Plan 未绑定正确 execution unit。")
            knowledge_plan_id = re.search(r"knowledge_plan_id:\s+(\w+)", knowledge_text).group(1)
            required_block = knowledge_text.split("required_static_knowledge:", 1)[1].split("search_scopes:", 1)[0]
            required_refs = re.findall(r'^\s+ref: "([^"]+)"', required_block, flags=re.MULTILINE)
            assert_true(required_refs, f"{scenario} Knowledge Plan 没有选择任何静态知识。")

            phase_outputs = {}
            for phase in ["decision", "planning", "execution", "completion"]:
                command = [
                    "ruby", str(context_planner),
                    "--effective", str(scenario_effective),
                    "--phase", phase,
                    "--domain", expected["domain"],
                ]
                if expected["lane"]:
                    command.extend(["--lane", expected["lane"]])
                if phase == "execution":
                    command.extend(["--selection", str(selection), "--knowledge-plan", str(knowledge_plan)])
                planned = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                assert_true(planned.returncode == 0 and "status: READY" in planned.stdout, f"{scenario}/{phase} Context Plan 失败：{planned.stdout}\n{planned.stderr}")
                phase_outputs[phase] = planned.stdout

            execution_output = phase_outputs["execution"]
            assert_true(expected["domain_skill"] in execution_output, f"{scenario} 未加载正确的 Domain execution Skill。")
            assert_true(execution_output.count("capability_id:") == expected["selected"], f"{scenario} Context Plan 没有保留全部选中能力。")
            assert_true(f"knowledge_plan_id: {knowledge_plan_id}" in execution_output, f"{scenario} Execution Context 未绑定 Knowledge Plan。")
            if expected["domain"] == "d3a":
                all_output = "\n".join(phase_outputs.values())
                assert_true("lane: " in all_output and "lane: fast" not in all_output and "lane: lite" not in all_output and "lane: complex" not in all_output, "D3A 必须保持 Lane not_applicable。")
                assert_true("references/lanes/" not in all_output and "lane-resolver.md" not in all_output, "D3A Context Plan 不得加载动态 Lane 资源。")
                assert_true("d3a-planning-constraints.yaml" in phase_outputs["planning"] and "d3a-execution-constraints.yaml" in execution_output, "D3A 必须加载固定 Planning/Execution 约束。")
                for kind in ["layer", "test_domain", "architecture", "verification_mapping"]:
                    assert_true(f"kind: {kind}" in knowledge_text, f"D3A Knowledge Plan 缺少 {kind}。")
            else:
                assert_true(f"references/lanes/{expected['lane']}.yaml" in "\n".join(phase_outputs.values()), f"{scenario} 必须加载自己的 Lane policy。")
                assert_true("idc-d3a-coding/SKILL.md" not in execution_output, f"{scenario} General 路径不得加载 D3A execution Skill。")

            authorization = Path(temp_dir) / f"{scenario}-authorization.yaml"
            lane_value = expected["lane"] if expected["lane"] else "null"
            authorization.write_text(
                f"""execution_authorization_request:
  task_id: matrix-{scenario}
  workflow_id: {expected['domain']}_execution
  selected_domain: {expected['domain']}
  selected_lane: {lane_value}
  human_alignment_status: approved
  approved_alignment_ref: alignment-{scenario}
  execution_unit_ref: {expected['unit']}
  context_packet_ref: context-{scenario}
  capability_selection_ref: {selection}
  capability_selection_status: READY
  knowledge_load_plan_ref: {knowledge_plan}
  knowledge_load_plan_status: READY
  knowledge_plan_id: {knowledge_plan_id}
  domain_execution_skill_ref: {expected['domain_skill']}
  selected_atomic_skill_refs: [selected-by-capability-selector]
  delegation_contract_ref: delegation-{scenario}
  main_agent_role: planning_and_delegation_only
  executor: {{kind: subagent, agent_id: {expected['domain']}-coder}}
  allowed_paths: [src/example]
  expected_outputs: [changed_paths, evidence_refs, execution_receipt]
""",
                encoding="utf-8",
            )
            authorized = subprocess.run(
                ["ruby", str(authorizer), "--request", str(authorization)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert_true(authorized.returncode == 0 and "status: AUTHORIZED" in authorized.stdout, f"{scenario} Execution Authorization 失败：{authorized.stdout}\n{authorized.stderr}")

            receipt = Path(temp_dir) / f"{scenario}-knowledge-receipt.yaml"
            loaded_yaml = "\n".join(f'    - "{ref}"' for ref in required_refs)
            provider_refs = "[provider-result]" if scenario in ["complex", "d3a"] else "[]"
            scope_refs = "[feature-doc-result]" if scenario == "complex" else "[]"
            receipt.write_text(
                f"""knowledge_consumption_receipt:
  knowledge_plan_id: {knowledge_plan_id}
  execution_unit_ref: {expected['unit']}
  loaded_static_refs:
{loaded_yaml}
  search_scope_result_refs: {scope_refs}
  provider_result_refs: {provider_refs}
  knowledge_summary_refs: [knowledge-summary]
""",
                encoding="utf-8",
            )
            verified = subprocess.run(
                ["ruby", str(knowledge_verifier), "--plan", str(knowledge_plan), "--receipt", str(receipt)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert_true(verified.returncode == 0 and "status: VERIFIED" in verified.stdout, f"{scenario} Knowledge Consumption 未闭环：{verified.stdout}\n{verified.stderr}")

            relative_receipt = Path(temp_dir) / f"{scenario}-relative-receipt.yaml"
            relative_lines = "\n".join(f'    - "{ref[len(str(ROOT)) + 1:]}"' for ref in required_refs)
            relative_receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(loaded_yaml, relative_lines),
                encoding="utf-8",
            )
            relative_verified = subprocess.run(
                ["ruby", str(knowledge_verifier), "--plan", str(knowledge_plan), "--receipt", str(relative_receipt)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert_true(relative_verified.returncode == 0 and "status: VERIFIED" in relative_verified.stdout, f"{scenario} 仓库相对路径回执必须与绝对路径计划等价（路径归一化）：{relative_verified.stdout}")

            if scenario == "d3a":
                cross_layer_receipt = Path(temp_dir) / "d3a-cross-layer-receipt.yaml"
                cross_layer_receipt.write_text(
                    receipt.read_text(encoding="utf-8").replace(
                        "  search_scope_result_refs:",
                        f'    - "{ROOT / ".claude/skills/idc-workflow/references/knowledge/d3a/layers/DRV.md"}"\n  search_scope_result_refs:',
                        1,
                    ),
                    encoding="utf-8",
                )
                cross_layer = subprocess.run(
                    ["ruby", str(knowledge_verifier), "--plan", str(knowledge_plan), "--receipt", str(cross_layer_receipt)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                assert_true(cross_layer.returncode == 3 and "unplanned knowledge refs were loaded" in cross_layer.stdout, "D3A 跨 Layer 知识注入必须被机器 Gate 阻断。")

                missing_static_receipt = Path(temp_dir) / "d3a-missing-static-receipt.yaml"
                missing_static_receipt.write_text(receipt.read_text(encoding="utf-8").replace(f'    - "{required_refs[0]}"\n', "", 1), encoding="utf-8")
                missing_static = subprocess.run(
                    ["ruby", str(knowledge_verifier), "--plan", str(knowledge_plan), "--receipt", str(missing_static_receipt)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                assert_true(missing_static.returncode == 3 and "required knowledge refs were not loaded" in missing_static.stdout, "遗漏 required Layer knowledge 必须阻断 Completion。")

                tampered_plan = Path(temp_dir) / "d3a-tampered-knowledge-plan.yaml"
                tampered_plan.write_text(knowledge_text.replace("selected_layer: DO", "selected_layer: DRV", 1), encoding="utf-8")
                tampered_authorization = Path(temp_dir) / "d3a-tampered-authorization.yaml"
                tampered_authorization.write_text(authorization.read_text(encoding="utf-8").replace(str(knowledge_plan), str(tampered_plan), 1), encoding="utf-8")
                tampered = subprocess.run(
                    ["ruby", str(authorizer), "--request", str(tampered_authorization)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                assert_true(tampered.returncode == 3 and "knowledge plan integrity check failed" in tampered.stdout, "Knowledge Plan 被修改后必须由 Authorization Gate 阻断。")

            if scenario in ["complex", "d3a"]:
                missing_provider_receipt = Path(temp_dir) / f"{scenario}-missing-provider-receipt.yaml"
                missing_provider_receipt.write_text(receipt.read_text(encoding="utf-8").replace("provider_result_refs: [provider-result]", "provider_result_refs: []"), encoding="utf-8")
                missing_provider = subprocess.run(
                    ["ruby", str(knowledge_verifier), "--plan", str(knowledge_plan), "--receipt", str(missing_provider_receipt)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                assert_true(missing_provider.returncode == 3 and "provider_result_refs are required" in missing_provider.stdout, f"{scenario} 缺少 Repo Context receipt 时必须阻断。")

        invalid_demand = Path(temp_dir) / "invalid-d3a-knowledge-demand.yaml"
        invalid_demand.write_text((ROOT / "examples/knowledge-demands/d3a.yaml").read_text(encoding="utf-8").replace("selected_layer: DO", "selected_layer: UNKNOWN_LAYER"), encoding="utf-8")
        missing_mapping = subprocess.run(
            ["ruby", str(knowledge_planner), "--effective", str(effective), "--demand", str(invalid_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(missing_mapping.returncode == 2 and "NEEDS_KNOWLEDGE_MAPPING" in missing_mapping.stdout, "未知 D3A Layer 必须返回 NEEDS_KNOWLEDGE_MAPPING。")

    d3a_workflow = read_text(".claude/skills/idc-workflow/references/workflows/d3a-workflow.md")
    d3a_skill = read_text(".claude/skills/idc-d3a-coding/SKILL.md")
    assert_true("DT RED" in d3a_workflow and "Required DT GREEN" in d3a_workflow, "D3A 固定流程必须保留 DT RED/GREEN。")
    assert_true("DONE 必须同时满足 required DT GREEN 和 `tran_build PASS`" in d3a_skill, "D3A 固定完成 Gate 必须要求 DT GREEN 与 tran_build PASS。")


def test_d3a_team_dt_domain_override_takes_effect():
    resolver = ROOT / ".claude/skills/idc-team-config/scripts/resolve_team_config.rb"
    selector = ROOT / ".claude/skills/idc-team-config/scripts/select_capabilities.rb"
    knowledge_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_knowledge.rb"
    context_planner = ROOT / ".claude/skills/idc-team-config/scripts/plan_context.rb"
    team_config = ROOT / "examples/team-config.d3a-team-dt.yaml"
    team_demand = ROOT / "examples/knowledge-demands/d3a-team-dt.yaml"
    for required in [resolver, selector, knowledge_planner, context_planner, team_config, team_demand]:
        assert_true(required.exists(), f"team dt override 链路缺少文件：{required}")

    with tempfile.TemporaryDirectory() as temp_dir:
        effective = Path(temp_dir) / "effective.yaml"
        resolved = subprocess.run(
            ["ruby", str(resolver), "--config", str(team_config), "--output", str(effective)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(resolved.returncode == 0, f"team dt override Resolver 失败：{resolved.stderr}")

        effective_data = yaml.safe_load(effective.read_text(encoding="utf-8"))
        effective_ids = [entry["id"] for entry in effective_data["knowledge_catalog"]["d3a"]["test_domains"]]
        assert_true(effective_ids == ["TEAM_DT_A", "TEAM_DT_B"], f"dt_domains 覆盖必须整体替换默认 registry：{effective_ids}")
        for builtin in ["TPRINT", "FW", "DPF"]:
            assert_true(builtin not in effective_ids, f"覆盖后内置 {builtin} 不得残留（整体替换，不合并）。")
        assert_true(effective_data["domain"]["test_domains_source"] == "team-config.yaml", "覆盖后 domain.test_domains_source 必须指向 team-config.yaml。")

        team_knowledge_plan = Path(temp_dir) / "team-knowledge-plan.yaml"
        team_planned = subprocess.run(
            ["ruby", str(knowledge_planner), "--effective", str(effective), "--demand", str(team_demand), "--output", str(team_knowledge_plan)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(team_planned.returncode == 0 and "status: READY" in team_knowledge_plan.read_text(encoding="utf-8"), f"team dt Knowledge Plan 未 READY：{team_planned.stdout}\n{team_planned.stderr}")
        team_plan_text = team_knowledge_plan.read_text(encoding="utf-8")
        assert_true("execution_unit_ref: d3a-do-unit" in team_plan_text, "team dt Knowledge Plan 必须绑定 d3a-do-unit。")
        team_plan_id = re.search(r"knowledge_plan_id:\s+(\w+)", team_plan_text).group(1)
        team_required = yaml.safe_load(team_plan_text)["knowledge_load_plan"]["required_static_knowledge"]
        team_dt_refs = {entry["id"]: entry["ref"] for entry in team_required if entry.get("kind") == "test_domain"}
        assert_true(set(team_dt_refs) == {"TEAM_DT_A", "TEAM_DT_B"}, f"team dt Knowledge Plan 必须解析团队 DT 知识：{sorted(team_dt_refs)}")
        assert_true(str(team_dt_refs.get("TEAM_DT_A", "")).endswith(".claude/skills/idc-workflow/references/knowledge/general/tests/GENERAL_TEST_PLACEHOLDER.md"), "TEAM_DT_A 必须绑定团队配置声明的 knowledge_ref。")
        assert_true(str(team_dt_refs.get("TEAM_DT_B", "")).endswith("docs/architecture.md"), "TEAM_DT_B 必须绑定团队配置声明的 knowledge_ref。")

        builtin_dt_demand = Path(temp_dir) / "builtin-dt-demand.yaml"
        builtin_dt_demand.write_text(
            team_demand.read_text(encoding="utf-8").replace(
                "selected_test_domains: [TEAM_DT_A, TEAM_DT_B]", "selected_test_domains: [TPRINT]"
            ),
            encoding="utf-8",
        )
        builtin_planned = subprocess.run(
            ["ruby", str(knowledge_planner), "--effective", str(effective), "--demand", str(builtin_dt_demand)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(builtin_planned.returncode != 0 and "NEEDS_KNOWLEDGE_MAPPING" in builtin_planned.stdout, "覆盖后选择内置 TPRINT 必须被拒绝（整体替换，不合并）。")
        assert_true("TPRINT" in builtin_planned.stdout and "not available in effective knowledge catalog" in builtin_planned.stdout, f"错误必须指明 TPRINT 不在生效 catalog：{builtin_planned.stdout}")

        selection = Path(temp_dir) / "team-dt-selection.yaml"
        selected = subprocess.run(
            ["ruby", str(selector), "--effective", str(effective), "--demand", str(ROOT / "examples/capability-demands/d3a.yaml"), "--output", str(selection)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(selected.returncode == 0 and "status: READY" in selection.read_text(encoding="utf-8"), f"team dt Selector 失败：{selected.stdout}\n{selected.stderr}")

        executed = subprocess.run(
            [
                "ruby", str(context_planner),
                "--effective", str(effective),
                "--phase", "execution",
                "--domain", "d3a",
                "--selection", str(selection),
                "--knowledge-plan", str(team_knowledge_plan),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert_true(executed.returncode == 0 and "status: READY" in executed.stdout, f"team dt Execution Context Plan 失败：{executed.stdout}\n{executed.stderr}")
        assert_true(f"knowledge_plan_id: {team_plan_id}" in executed.stdout, "Execution Context 必须绑定同一个 team dt Knowledge Plan。")
        assert_true("idc-d3a-coding/SKILL.md" in executed.stdout, "D3A Execution Context 必须加载 idc-d3a-coding Skill。")

    doc_locks = [
        ".claude/skills/idc-workflow/references/constraints/planning/d3a-planning-constraints.yaml",
        ".claude/skills/idc-workflow/references/workflows/d3a-workflow.md",
        ".claude/skills/idc-workflow/references/schemas/d3a-plan.schema.yaml",
    ]
    for path in doc_locks:
        doc = read_text(path)
        assert_true("knowledge_catalog.d3a.test_domains" in doc and "整体替换" in doc, f"{path} 必须按生效 registry 声明 DT Domain 选择。")
        assert_true("只能选择 TPRINT、FW、DPF" not in doc and "V0 DT Domain" not in doc, f"{path} 不得把 TPRINT、FW、DPF 硬编码为唯一可选 DT 集合。")
    assert_true("TRAN_CFG、DO、VISP_ADP、TFC_TFI、TFE、ADP、DRV" in read_text(doc_locks[0]), "D3A Coding Layer 固定声明必须保留。")


def can_enter_done(required_domains, green_domains, tran_build_status):
    return can_enter_all_layers_green(required_domains, green_domains) and tran_build_status == "PASS"


def test_unpassed_dt_blocks_all_layers_green():
    assert_true(not can_enter_all_layers_green(["TPRINT", "FW"], ["TPRINT"]), "缺少 FW GREEN 时没有阻塞。")
    assert_true(can_enter_all_layers_green(["TPRINT", "FW"], ["TPRINT", "FW"]), "全部 DT GREEN 后仍被阻塞。")


def test_tran_build_must_pass_before_done():
    assert_true(not can_enter_done(["TPRINT"], ["TPRINT"], "FAIL"), "tran_build FAIL 时允许 DONE。")
    assert_true(can_enter_done(["TPRINT"], ["TPRINT"], "PASS"), "所有 evidence 通过后仍阻塞 DONE。")


def test_placeholder_hygiene():
    text = "\n".join(
        path.read_text(errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    )
    assert_true(any(pattern in text for pattern in PLACEHOLDER_PATTERNS), "没有发现 enterprise placeholder。")

    forbidden_guesses = [
        "internal" + "." + "company",
        "/" + "opt" + "/" + "enterprise",
        "prod" + "-" + "d3a",
    ]
    lowered = text.lower()
    for phrase in forbidden_guesses:
        assert_true(phrase not in lowered, f"发现疑似猜测的企业细节：{phrase}")


def run():
    tests = [
        test_registry_files_match_fixed_architecture,
        test_registry_knowledge_templates_exist,
        test_domain_module_registry_files_exist,
        test_framework_supports_dynamic_scenarios_and_skill_adapters,
        test_active_domain_module_declares_required_contract,
        test_d3a_uses_shared_execution_skeleton_with_enterprise_constraints,
        test_active_domain_module_asset_paths_exist,
        test_general_domain_module_is_active_and_self_closing,
        test_lane_registry_files_exist,
        test_every_lane_is_self_closing,
        test_lane_resolver_fixtures_are_stable,
        test_tr3_fixtures_preserve_classification_signals,
        test_alignment_and_escalation_contracts_exist,
        test_execution_unit_loc_limit_is_enforced,
        test_repo_context_provider_contract_is_context_bounded,
        test_provider_selection_matrix_is_anchor_aware_and_okl_query_bounded,
        test_context_engineering_is_progressive_and_not_token_policy,
        test_repo_rules_are_canonical_in_claude_md,
        test_delegation_contract_keeps_main_agent_as_planner,
        test_resume_policy_supports_interruption_recovery,
        test_confidential_vertical_slice_readiness_gate_exists,
        test_progressive_constraint_loading_files_exist,
        test_e2e_tr3_d3a_demo_is_complete,
        test_e2e_general_demo_is_complete,
        test_manual_test_scenarios_exist_for_user_experience,
        test_adoption_and_deep_dive_docs_exist,
        test_id_workflow_skill_exists_and_has_triggers,
        test_framework_behaviors_are_skillized_with_boundaries,
        test_atomic_pre_alignment_skills_exist_and_are_reusable,
        test_superpowers_adapter_skill_is_integrated_under_skills,
        test_gc_sop_and_original_repo_skill_adapters_exist,
        test_domain_and_build_skills_define_entry_rules_at_skill_layer,
        test_claude_project_entries_expose_skills_and_agents,
        test_human_views_exist_and_hide_raw_yaml,
        test_user_questions_must_use_ask_user_tool,
        test_clarification_provider_uses_grill_me_method_with_fallback,
        test_discovery_provider_uses_superpowers_brainstorming_for_raw_idea,
        test_d3a_unclear_input_cannot_bypass_brainstorming_or_grill_me,
        test_planner_cannot_produce_registry_external_layers,
        test_requirement_assessor_detects_missing_critical_fields,
        test_layer_context_packet_only_contains_selected_layer,
        test_no_red_evidence_cannot_enter_green,
        test_tdd_extensions_are_team_config_driven,
        test_registries_are_team_config_overridable,
        test_team_config_resolver_and_lane_capability_selection_execute,
        test_d3a_and_general_lane_runtime_matrix_execute,
        test_d3a_team_dt_domain_override_takes_effect,
        test_filled_team_config_when_present,
        test_plan_context_rejects_domain_mode_mismatch,
        test_domain_mode_requires_registered_builtin_module,
        test_domain_mode_general_with_d3a_unplugged_stays_ready,
        test_lane_profiles_use_ordered_mode,
        test_alignment_pipeline_config_shape_mirrors_lane_profiles,
        test_alignment_pipeline_framework_invariants_are_enforced,
        test_alignment_pipeline_runtime_consumption_is_materialized,
        test_alignment_pipeline_docs_record_section_and_ownership,
        test_alignment_pipeline_execution_defers_to_config_not_hardcoded,
        test_select_capabilities_rejects_unknown_signal,
        test_unpassed_dt_blocks_all_layers_green,
        test_tran_build_must_pass_before_done,
        test_placeholder_hygiene,
    ]
    failures = []
    for test in tests:
        try:
            test()
            print(f"通过 {test.__name__}")
        except Exception as exc:
            failures.append((test.__name__, exc))
            print(f"失败 {test.__name__}: {exc}")

    if failures:
        print(f"\n{len(failures)} 个测试失败。")
        return 1

    print(f"\n{len(tests)} 个测试通过。")
    return 0


if __name__ == "__main__":
    sys.exit(run())
