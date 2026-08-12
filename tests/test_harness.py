#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LAYER_REGISTRY = {"TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV"}
DT_REGISTRY = {"TPRINT", "FW", "DPF"}
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
    "simple_verification",
}


def read_text(path):
    return (ROOT / path).read_text()


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
    return re.findall(r"^\s+module_file:\s+(.+)\s*$", read_text("domains/registry.yaml"), flags=re.MULTILINE)


def extract_domain_module_ids():
    return set(re.findall(r"^\s+-\s+id:\s+([a-z0-9-]+)\s*$", read_text("domains/registry.yaml"), flags=re.MULTILINE))


def extract_lane_files():
    return re.findall(r"^\s+file:\s+(.+)\s*$", read_text("lanes/registry.yaml"), flags=re.MULTILINE)


def extract_lane_ids():
    return set(re.findall(r"^\s+-\s+id:\s+([a-z0-9-]+)\s*$", read_text("lanes/registry.yaml"), flags=re.MULTILINE))


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
    layers = extract_registry_ids("registries/d3a-layers.yaml")
    domains = extract_registry_ids("registries/dt-domains.yaml")
    assert_true(layers == LAYER_REGISTRY, "D3A layer registry 发生漂移。")
    assert_true(domains == DT_REGISTRY, "DT domain registry 发生漂移。")


def test_registry_knowledge_templates_exist():
    files = extract_registry_knowledge_files("registries/d3a-layers.yaml")
    files += extract_registry_knowledge_files("registries/dt-domains.yaml")
    for file_name in files:
        path = ROOT / file_name
        assert_true(path.exists(), f"Registry 指向的 knowledge 模板不存在：{file_name}")
        assert_true("<ENTERPRISE_" in path.read_text(), f"Knowledge 模板缺少 enterprise placeholder：{file_name}")


def test_domain_module_registry_files_exist():
    module_ids = extract_domain_module_ids()
    assert_true("d3a" in module_ids, "Domain Module registry 缺少 d3a module。")
    for module_file in extract_domain_module_files():
        assert_true((ROOT / module_file).exists(), f"Domain Module 文件不存在：{module_file}")


def test_active_domain_module_declares_required_contract():
    module_file = "domains/d3a/module.yaml"
    text = read_text(module_file)
    for required in ["id:", "name:", "status:", "route:", "registries:", "workflow:", "knowledge:", "execution:"]:
        assert_true(required in text, f"d3a module 缺少 contract 区块：{required}")
    assert_true(extract_module_string_value(module_file, "id") == "d3a", "d3a module id 不正确。")
    assert_true(extract_module_string_value(module_file, "status") == "active", "d3a module 必须是 active。")
    assert_true("required_contracts:" in text, "d3a module 必须声明 required_contracts。")
    assert_true("- api_contract" in text, "d3a module 必须要求 api_contract。")
    assert_true("- verification_contract" in text, "d3a module 必须要求 verification_contract。")


def test_active_domain_module_asset_paths_exist():
    for asset_path in extract_module_asset_paths("domains/d3a/module.yaml"):
        assert_true((ROOT / asset_path).exists(), f"d3a module 引用的资产不存在：{asset_path}")


def test_lane_registry_files_exist():
    assert_true(extract_lane_ids() == {"fast", "lite", "complex"}, "Lane registry 必须只包含 fast/lite/complex。")
    for lane_file in extract_lane_files():
        assert_true((ROOT / lane_file).exists(), f"Lane 文件不存在：{lane_file}")


def test_every_lane_is_self_closing():
    for lane_file in extract_lane_files():
        text = read_text(lane_file)
        assert_true("completion_requirements:" in text, f"{lane_file} 缺少 completion_requirements。")
        assert_true("completion_summary_exists" in text, f"{lane_file} 必须要求 completion summary。")
        has_evidence_requirement = "evidence" in text or "tests_or_builds_passed" in text
        assert_true(has_evidence_requirement, f"{lane_file} 必须要求 evidence。")


def lane_resolver_decision(signals):
    hard_triggers = sorted(trigger for trigger in COMPLEX_HARD_TRIGGERS if signals.get(trigger))
    if hard_triggers:
        return {
            "selected_lane": "complex",
            "decision_rule": "hard_trigger",
            "hard_triggers": hard_triggers,
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
    for block in extract_lane_fixture_blocks():
        fixture_id, signals, expected_lane, expected_rule = parse_lane_fixture(block)
        decision = lane_resolver_decision(signals)
        assert_true(decision["selected_lane"] == expected_lane, f"{fixture_id} lane 判断漂移。")
        assert_true(decision["decision_rule"] == expected_rule, f"{fixture_id} decision_rule 判断漂移。")
        assert_true("hard_triggers" in decision, f"{fixture_id} 缺少 hard_triggers。")
        assert_true("fast_disqualified_by" in decision, f"{fixture_id} 缺少 fast_disqualified_by。")


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
    alignment_schema = read_text("schemas/alignment-pack.schema.yaml")
    escalation_schema = read_text("schemas/escalation-policy.schema.yaml")
    human_alignment = read_text("workflows/human-alignment.md")
    automated_loop = read_text("workflows/automated-closure-loop.md")

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
    execution_schema = read_text("schemas/execution-unit.schema.yaml")
    execution_policy = read_text("workflows/execution-unit-policy.md")
    automated_loop = read_text("workflows/automated-closure-loop.md")
    d3a_workflow = read_text("workflows/d3a-workflow.md")
    d3a_coder = read_text("agents/d3a-layer-coder.md")

    for path, text in [
        ("schemas/execution-unit.schema.yaml", execution_schema),
        ("workflows/execution-unit-policy.md", execution_policy),
        ("workflows/automated-closure-loop.md", automated_loop),
        ("workflows/d3a-workflow.md", d3a_workflow),
        ("agents/d3a-layer-coder.md", d3a_coder),
    ]:
        assert_true("500" in text, f"{path} 必须声明 500 行限制。")

    assert_true("max_change_loc: 500" in execution_schema, "Execution Unit schema 必须声明 max_change_loc: 500。")
    assert_true("每个 execution unit 都必须有自己的 evidence" in execution_policy, "Execution Unit 必须有独立 evidence。")
    assert_true("max_layers_per_packet = 1" in d3a_workflow, "D3A 必须限制一个 packet 一个 Layer。")
    assert_true("execution_unit_too_large" in read_text("schemas/escalation-policy.schema.yaml"), "Escalation 必须覆盖 execution unit 过大。")


def test_repo_context_provider_contract_is_token_bounded():
    schema = read_text("schemas/repo-context-provider.schema.yaml")
    workflow = read_text("workflows/repo-context-providers.md")
    token_policy = read_text("docs/token-budget-policy.md")

    for provider in ["grep", "codegraph", "okl"]:
        assert_true(provider in schema.lower(), f"Repo Context Provider schema 缺少 {provider}。")
    assert_true("max_results: 10" in schema, "Repo Context Provider 必须默认 max_results: 10。")
    assert_true("max_snippet_chars: 800" in schema, "Repo Context Provider 必须默认 max_snippet_chars: 800。")
    assert_true("evidence_ref_required: true" in schema, "Repo Context Provider 必须要求 evidence_ref。")
    assert_true("OKL 文档不能替代 test/build evidence" in schema, "OKL 不能替代工具 evidence。")
    assert_true("grep / CodeGraph / OKL" in workflow, "Provider workflow 必须说明 grep / CodeGraph / OKL。")
    assert_true("fast: 2k - 6k" in token_policy, "Token Budget Policy 必须声明 fast 预算。")
    assert_true("complex: 分阶段" in token_policy, "Token Budget Policy 必须声明 complex 分阶段预算。")


def test_progressive_constraint_loading_files_exist():
    stages = {
        "decision": "constraints/decision",
        "planning": "constraints/planning",
        "execution": "constraints/execution",
    }
    for stage, directory in stages.items():
        files = sorted((ROOT / directory).glob("*.yaml"))
        assert_true(files, f"{stage} constraints 不能为空。")
        for file_path in files:
            text = file_path.read_text()
            assert_true(f"stage: {stage}" in text, f"{file_path} stage 不正确。")
            assert_true("constraints:" in text, f"{file_path} 缺少 constraints。")
            assert_true("forbidden_actions:" in text, f"{file_path} 缺少 forbidden_actions。")

    workflow = read_text("workflows/progressive-constraint-loading.md")
    assert_true("Decision Constraints" in workflow, "约束加载文档缺少 Decision。")
    assert_true("Planning Constraints" in workflow, "约束加载文档缺少 Planning。")
    assert_true("Execution Constraints" in workflow, "约束加载文档缺少 Execution。")


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
    assert_true("selected_lane: complex" in decision, "E2E demo 必须选择 complex lane。")
    assert_true("max_change_loc: 500" in plan, "E2E demo execution unit 必须声明 500 LOC。")
    assert_true("tran-build-pass" in evidence, "E2E demo 必须包含 tran_build evidence。")
    assert_true("DONE" in completion, "E2E demo 必须包含 completion summary。")


def test_adoption_and_deep_dive_docs_exist():
    assert_true((ROOT / "docs/adoption-guide.md").exists(), "缺少 adoption guide。")
    for file_name in [
        "docs/deep-dive/repo-context-providers.md",
        "docs/deep-dive/progressive-constraint-loading.md",
        "docs/deep-dive/lane-and-completion.md",
        "docs/deep-dive/tr3-input.md",
    ]:
        assert_true((ROOT / file_name).exists(), f"缺少 deep dive 文档：{file_name}")


def test_id_workflow_skill_exists_and_has_triggers():
    skill_path = ROOT / "skills/id-workflow/SKILL.md"
    assert_true(skill_path.exists(), "缺少 ID workflow skill。")
    text = skill_path.read_text()
    assert_true("name: id-workflow" in text, "ID workflow skill 缺少 name。")
    assert_true("description:" in text, "ID workflow skill 缺少 description。")
    assert_true("Alignment Pack" in text, "ID workflow skill 必须支持 Alignment Pack。")
    assert_true("TR3" in text, "ID workflow skill 必须支持 TR3。")
    assert_true("500 LOC" in text, "ID workflow skill 必须声明 500 LOC 限制。")
    assert_true("Human Alignment approval" in text, "ID workflow skill 必须要求 Human Alignment approval。")


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
    "IMPLEMENTING": {"GREEN_CONFIRMED"},
    "GREEN_CONFIRMED": {"LAYER_COMPLETE"},
}


def can_transition(source, target, has_red_evidence=False):
    if target == "GREEN_CONFIRMED" and not has_red_evidence:
        return False
    return target in ALLOWED_LAYER_TRANSITIONS.get(source, set())


def test_no_red_evidence_cannot_enter_green():
    assert_true(not can_transition("IMPLEMENTING", "GREEN_CONFIRMED", has_red_evidence=False), "没有 RED 却允许进入 GREEN。")
    assert_true(can_transition("IMPLEMENTING", "GREEN_CONFIRMED", has_red_evidence=True), "已有 RED 却阻塞 GREEN。")


def can_enter_all_layers_green(required_domains, green_domains):
    return set(required_domains) <= set(green_domains)


def can_enter_done(required_domains, green_domains, tran_build_status):
    return can_enter_all_layers_green(required_domains, green_domains) and tran_build_status == "PASS"


def test_unpassed_dt_blocks_all_layers_green():
    assert_true(not can_enter_all_layers_green(["TPRINT", "FW"], ["TPRINT"]), "缺少 FW GREEN 时没有阻塞。")
    assert_true(can_enter_all_layers_green(["TPRINT", "FW"], ["TPRINT", "FW"]), "全部 DT GREEN 后仍被阻塞。")


def test_tran_build_must_pass_before_done():
    assert_true(not can_enter_done(["TPRINT"], ["TPRINT"], "FAIL"), "tran_build FAIL 时允许 DONE。")
    assert_true(can_enter_done(["TPRINT"], ["TPRINT"], "PASS"), "所有 evidence 通过后仍阻塞 DONE。")


def test_placeholder_hygiene():
    text = "\n".join(path.read_text(errors="ignore") for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts)
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
        test_active_domain_module_declares_required_contract,
        test_active_domain_module_asset_paths_exist,
        test_lane_registry_files_exist,
        test_every_lane_is_self_closing,
        test_lane_resolver_fixtures_are_stable,
        test_tr3_fixtures_preserve_classification_signals,
        test_alignment_and_escalation_contracts_exist,
        test_execution_unit_loc_limit_is_enforced,
        test_repo_context_provider_contract_is_token_bounded,
        test_progressive_constraint_loading_files_exist,
        test_e2e_tr3_d3a_demo_is_complete,
        test_adoption_and_deep_dive_docs_exist,
        test_id_workflow_skill_exists_and_has_triggers,
        test_planner_cannot_produce_registry_external_layers,
        test_requirement_assessor_detects_missing_critical_fields,
        test_layer_context_packet_only_contains_selected_layer,
        test_no_red_evidence_cannot_enter_green,
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
