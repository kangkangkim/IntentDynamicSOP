// IDC Team Config Studio — 自检测试套件
//
// 验证策略：
//   1. 在 Node 中以 DOM stub 加载真实 script.js（测的是线上文件，不是副本）
//   2. 生成的 YAML 必须通过仓库权威校验器 resolve_team_config.py --check
//   3. parseYaml 对仓库 5 份真实配置做 round-trip 保真校验
//   4. validateConfig 故障注入 + 禁止键扫描
//   5. Chrome headless 冒烟测试（真实浏览器渲染）+ 截图
//
// 运行：node prototypes/team-config-studio/studio.test.mjs

import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const resolver = join(root, ".claude", "skills", "idc-team-config", "scripts", "resolve_team_config.py");
const tempDir = mkdtempSync(join(tmpdir(), "idc-studio-test-"));

let passed = 0;
const failures = [];
function check(name, condition, detail = "") {
  if (condition) { passed += 1; console.log(`通过 ${name}`); }
  else { failures.push(`${name}${detail ? `：${detail}` : ""}`); console.log(`失败 ${name}${detail ? `：${detail}` : ""}`); }

}

/* ---------------- 1. 加载真实 script.js ---------------- */

function elStub() {
  return {
    innerHTML: "", textContent: "", className: "", value: "", dataset: {}, style: {},
    classList: { add() {}, remove() {} },
    addEventListener() {}, appendChild() {}, querySelector: () => null, querySelectorAll: () => [],
    scrollWidth: 0, scrollLeft: 0
  };
}

function loadStudio() {
  const source = readFileSync(join(here, "script.js"), "utf8");
  const api = {};
  globalThis.__harvest = (obj) => Object.assign(api, obj);
  globalThis.document = {
    getElementById: () => elStub(), querySelector: () => null, querySelectorAll: () => [],
    addEventListener() {}, createElement: () => elStub()
  };
  globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
  // 并行开发中函数可能增删：按名字惰性收割，缺席的置为 undefined，由用例自行判定是否必需
  const wanted = ["defaultConfig", "buildYaml", "validateConfig", "parseYaml", "mergeDefaults", "clone", "csv", "yamlScalar", "flow", "extensionsToText", "textToExtensions", "laneStepsToText", "textToLaneSteps", "availableSkillIds", "applyAlignmentPreset", "detectAlignmentPreset", "stepFiresOn", "applyImportedYaml", "wizardSkip", "ALIGNMENT_PRESETS", "enabledModes", "setModeEnabled", "setPrimaryDomain", "referencedBindingKeys"];
  const exportsLine = `;__harvest((() => { const out = {}; for (const name of ${JSON.stringify(wanted)}) { try { out[name] = eval(name); } catch (_) { out[name] = undefined; } } try { out.getState = () => state; out.setState = (next) => { state = next; }; out.getActiveSection = () => activeSection; out.setActiveSection = (id) => { activeSection = id; }; out.getWizard = () => wizard; } catch (_) {} return out; })());`;
  (0, eval)(source + "\n" + exportsLine);
  return api;
}

let studio;
try {
  studio = loadStudio();
  check("script.js 可在 Node stub 环境加载并完成首次 render", true);
} catch (error) {
  check("script.js 可在 Node stub 环境加载并完成首次 render", false, error.message);
  console.log("\n加载失败，终止。");
  process.exit(1);
}
for (const fn of ["defaultConfig", "buildYaml", "validateConfig", "parseYaml", "mergeDefaults"]) {
  check(`核心函数存在: ${fn}`, typeof studio[fn] === "function");
}

/* ---------------- 2. 权威 resolver ---------------- */

function runResolver(yamlText, label) {
  const file = join(tempDir, `${label}.yaml`);
  writeFileSync(file, yamlText);
  try {
    const output = execFileSync("python3", [resolver, "--config", file, "--check"], { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    return { ok: true, output };
  } catch (error) {
    return { ok: false, output: `${error.stdout || ""}${error.stderr || ""}`.trim() };
  }
}

function allChecksOk(result) {
  return result.checks.every((item) => item.ok);
}

function deepContains(subset, superset, path = "$") {
  if (subset === null || subset === undefined) return subset === superset;
  if (Array.isArray(subset)) {
    if (!Array.isArray(superset) || JSON.stringify(subset) !== JSON.stringify(superset)) return `${path}: 数组不一致`;
    return true;
  }
  if (typeof subset === "object") {
    if (typeof superset !== "object" || superset === null) return `${path}: 期望对象`;
    for (const [key, value] of Object.entries(subset)) {
      const child = deepContains(value, superset[key], `${path}.${key}`);
      if (child !== true) return child;
    }
    return true;
  }
  return subset === superset ? true : `${path}: ${JSON.stringify(subset)} !== ${JSON.stringify(superset)}`;
}

const forbiddenKeys = ["command:", "build_command:", "run_command:", "pass_condition:"];
function assertNoForbiddenKeys(yamlText, label) {
  const hit = forbiddenKeys.filter((key) => yamlText.includes(key));
  check(`${label}: 输出不含禁止键`, hit.length === 0, `发现 ${hit.join(", ")}`);
}

/* ---------------- 3. 默认配置 ---------------- */

const defaultYaml = studio.buildYaml(studio.defaultConfig());
check("默认配置通过浏览器侧全部检查", allChecksOk(studio.validateConfig()));
const defaultResolver = runResolver(defaultYaml, "default");
check("默认配置 YAML 通过权威 resolver", defaultResolver.ok, defaultResolver.output);
assertNoForbiddenKeys(defaultYaml, "默认配置");

/* ---------------- 4. 仓库真实配置 round-trip ---------------- */

const repoConfigs = [
  "team-config.yaml",
  "examples/team-config.minimal.yaml",
  "examples/team-config.full-bindings.yaml",
  "examples/team-config.d3a-team-dt.yaml",
  "examples/team-config.custom-domain.yaml"
];
const parsedExamples = {};
for (const relPath of repoConfigs) {
  const label = relPath.split("/").pop();
  const parsed = studio.parseYaml(readFileSync(join(root, relPath), "utf8"));
  parsedExamples[label] = parsed;
  const merged = studio.mergeDefaults(studio.defaultConfig(), parsed);
  const regenerated = studio.buildYaml(merged);
  const reParsed = studio.parseYaml(regenerated);
  const missing = deepContains(parsed, reParsed);
  check(`${label}: 导入 → 重新生成语义保真`, missing === true, missing);
  const resolverRun = runResolver(regenerated, label.replace(/[^a-z0-9-]/gi, "_"));
  check(`${label}: 重新生成 YAML 通过权威 resolver`, resolverRun.ok, resolverRun.output);
  assertNoForbiddenKeys(regenerated, label);
}

/* ---------------- 5. UI 从零构造的三种 Domain 场景 ---------------- */

// 5a. General + 三条 Lane 均为 ordered 编排
// resolver 要求 allow/required/deny 引用的 skill 必须已绑定（skill_ref 非空），因此先绑定再编排
const generalFixture = studio.defaultConfig();
generalFixture.team.id = "demo-general-team";
generalFixture.domain.mode = "general";
const generalBoundSkills = ["coding_standard", "tech_design", "ut_generate", "impl_review", "static_scan", "system_test", "defect_fix", "git_commit"];
// 注意只能绑定原子能力 Skill：idc-general-coding 属于外层协议，会被 resolver 以 execution_role 拒绝
generalBoundSkills.forEach((key) => {
  generalFixture.bindings[key].skill_ref = ".claude/skills/idc-gc-sop-adapter/SKILL.md";
});
generalFixture.lane.profiles.fast = {
  skills: { allow: ["coding_standard", "defect_fix"], deny: [], required: ["defect_fix"] },
  orchestration: {
    mode: "ordered",
    steps: [{ id: "fast-hotfix", stage: "fix", skill_ids: ["defect_fix"], trigger_signals: ["test_failure"] }]
  }
};
generalFixture.lane.profiles.lite = {
  skills: { allow: ["coding_standard", "tech_design", "ut_generate", "static_scan", "defect_fix"], deny: [], required: ["tech_design"] },
  orchestration: {
    mode: "ordered",
    steps: [
      { id: "lite-design", stage: "planning", skill_ids: ["tech_design"], trigger_signals: [] },
      { id: "lite-implement", stage: "implementation", skill_ids: ["ut_generate"], trigger_signals: [] },
      { id: "lite-verify", stage: "verification", skill_ids: ["static_scan"], trigger_signals: [] }
    ]
  }
};
generalFixture.lane.profiles.complex = {
  skills: { allow: ["coding_standard", "tech_design", "ut_generate", "impl_review", "static_scan", "system_test", "defect_fix"], deny: ["git_commit"], required: ["tech_design", "system_test"] },
  orchestration: {
    mode: "ordered",
    steps: [
      { id: "complex-design", stage: "planning", skill_ids: ["tech_design"], trigger_signals: ["high_risk_change"] },
      { id: "complex-implement", stage: "implementation", skill_ids: ["ut_generate"], trigger_signals: [] },
      { id: "complex-review", stage: "review", skill_ids: ["impl_review"], trigger_signals: [] },
      { id: "complex-verify", stage: "verification", skill_ids: ["static_scan", "system_test"], trigger_signals: [] },
      { id: "complex-fix", stage: "fix", skill_ids: ["defect_fix"], trigger_signals: ["verification_failed"] }
    ]
  }
};
const generalYaml = studio.buildYaml(generalFixture);
studio.setState(generalFixture);
check("General 场景（三 Lane ordered 编排）通过浏览器侧检查", allChecksOk(studio.validateConfig()));
const generalResolverRun = runResolver(generalYaml, "scenario_general");
check("General 场景 YAML 通过权威 resolver", generalResolverRun.ok, generalResolverRun.output);
assertNoForbiddenKeys(generalYaml, "General 场景");

// 5b. D3A：dt 绑定 + 团队 DT domains（skill_ref 取自仓库 d3a 示例，保证真实可用）
const d3aReference = parsedExamples["team-config.d3a-team-dt.yaml"] || {};
const d3aFixture = studio.defaultConfig();
d3aFixture.team.id = "demo-d3a-team";
d3aFixture.domain.mode = "d3a";
if (d3aReference.domain && Array.isArray(d3aReference.domain.d3a && d3aReference.domain.d3a.dt_domains)) {
  d3aFixture.domain.d3a.dt_domains = studio.clone(d3aReference.domain.d3a.dt_domains);
}
for (const key of ["dt_design", "dt_writer", "dt_build", "tran_build"]) {
  const ref = d3aReference.bindings && d3aReference.bindings[key] && d3aReference.bindings[key].skill_ref;
  d3aFixture.bindings[key].skill_ref = ref || `.claude/skills/idc-${key.replace("_", "-")}/SKILL.md`;
}
studio.setState(d3aFixture);
check("D3A 场景通过浏览器侧检查", allChecksOk(studio.validateConfig()));
const d3aResolverRun = runResolver(studio.buildYaml(d3aFixture), "scenario_d3a");
check("D3A 场景 YAML 通过权威 resolver", d3aResolverRun.ok, d3aResolverRun.output);
assertNoForbiddenKeys(studio.buildYaml(d3aFixture), "D3A 场景");

// 5c. Custom：内联 Domain（字段值取自仓库 custom 示例）
const customReference = parsedExamples["team-config.custom-domain.yaml"] || {};
const customFixture = studio.defaultConfig();
customFixture.team.id = "demo-custom-team";
customFixture.domain.mode = "custom";
if (customReference.domain && customReference.domain.custom) {
  customFixture.domain.custom = studio.clone(customReference.domain.custom);
}
studio.setState(customFixture);
check("Custom 场景通过浏览器侧检查", allChecksOk(studio.validateConfig()));
const customResolverRun = runResolver(studio.buildYaml(customFixture), "scenario_custom");
check("Custom 场景 YAML 通过权威 resolver", customResolverRun.ok, customResolverRun.output);

/* ---------------- 6. validateConfig 故障注入 ---------------- */

function injectFault(name, mutate) {
  const config = studio.defaultConfig();
  mutate(config);
  studio.setState(config);
  const result = studio.validateConfig();
  check(`故障注入被检出: ${name}`, !allChecksOk(result));
}
injectFault("required 不在 allow 中", (config) => {
  config.lane.profiles.lite.skills.allow = ["coding_standard"];
  config.lane.profiles.lite.skills.required = ["tech_design"];
});
injectFault("ordered 模式缺 steps", (config) => {
  config.lane.profiles.fast.orchestration.mode = "ordered";
  config.lane.profiles.fast.orchestration.steps = [];
});
injectFault("Alignment 缺少 divergence 阶段", (config) => {
  config.alignment.orchestration.steps = config.alignment.orchestration.steps.filter((step) => step.stage !== "divergence");
});
injectFault("Extension 缺少 idc- 前缀", (config) => {
  config.adapter_extensions = [{ id: "team-api-review", skill_ref: ".claude/skills/idc-gc-sop-adapter/SKILL.md" }];
});
// 与 resolver 的 "references unavailable skill ID" 规则对齐：allow 引用未绑定 skill，浏览器侧必须先拦下
injectFault("lane 引用未绑定的 skill", (config) => {
  config.lane.profiles.lite.skills.allow = ["coding_standard", "unbound_skill"];
  config.lane.profiles.lite.skills.required = [];
});
injectFault("ordered steps 引用未绑定的 skill", (config) => {
  config.bindings.tech_design.skill_ref = ".claude/skills/idc-gc-sop-adapter/SKILL.md";
  config.lane.profiles.lite.orchestration.mode = "ordered";
  config.lane.profiles.lite.orchestration.steps = [{ id: "lite-design", stage: "planning", skill_ids: ["unbound_skill"], trigger_signals: [] }];
});
{
  const unboundConfig = studio.defaultConfig();
  unboundConfig.lane.profiles.lite.skills.allow = ["coding_standard", "unbound_skill"];
  unboundConfig.lane.profiles.lite.skills.required = [];
  const unboundRun = runResolver(studio.buildYaml(unboundConfig), "unbound_lane_skill");
  check("parity: lane 引用未绑定 skill 时 resolver 同样拒绝", !unboundRun.ok && unboundRun.output.includes("references unavailable skill ID"), unboundRun.output.slice(0, 160));
}
studio.setState(studio.defaultConfig());
check("故障清除后恢复全绿", allChecksOk(studio.validateConfig()));

/* ---------------- 6b. 对齐策略 preset（按输入成熟度分流） ---------------- */

for (const presetId of Object.keys(studio.ALIGNMENT_PRESETS || {})) {
  const presetConfig = studio.defaultConfig();
  const applied = studio.applyAlignmentPreset(presetConfig, presetId);
  studio.setState(presetConfig);
  const stages = presetConfig.alignment.orchestration.steps.map((step) => step.stage);
  const signals = presetConfig.alignment.orchestration.steps.flatMap((step) => step.trigger_signals);
  check(`preset ${presetId}: 应用成功且可被识别`, applied === true && studio.detectAlignmentPreset(presetConfig) === presetId);
  check(`preset ${presetId}: 保留 4 个必需 stage（信号门控而非删除步骤）`,
    ["discovery", "divergence", "clarification", "alignment_check"].every((stage) => stages.includes(stage)));
  check(`preset ${presetId}: 满足信号下限 raw_idea + critical_gaps_remain`,
    ["raw_idea", "critical_gaps_remain"].every((signal) => signals.includes(signal)));
  check(`preset ${presetId}: 通过浏览器侧检查`, allChecksOk(studio.validateConfig()));
  const presetRun = runResolver(studio.buildYaml(presetConfig), `preset_${presetId}`);
  check(`preset ${presetId}: YAML 通过权威 resolver`, presetRun.ok, presetRun.output.slice(0, 160));
}
{
  const customized = studio.defaultConfig();
  studio.applyAlignmentPreset(customized, "full");
  customized.alignment.orchestration.steps[0].trigger_signals = ["raw_idea", "something_else"];
  check("手动修改步骤后不再匹配任何 preset（进入自定义）", studio.detectAlignmentPreset(customized) === null);
}
{
  const gate = { id: "check", stage: "alignment_check", skill_ids: ["intent_alignment"], trigger_signals: [] };
  const discovery = { id: "d", stage: "discovery", skill_ids: ["intent_discovery"], trigger_signals: ["raw_idea"] };
  check("stepFiresOn: 无信号 = 恒触发", studio.stepFiresOn(gate, "raw_idea") === true && studio.stepFiresOn(gate, "structured_requirement_ready") === true);
  check("stepFiresOn: raw_idea 步骤对 structured 输入不触发", studio.stepFiresOn(discovery, "raw_idea") === true && studio.stepFiresOn(discovery, "structured_requirement_ready") === false);
  check("stepFiresOn: 无预览信号时返回 null", studio.stepFiresOn(discovery, null) === null);
}

/* ---------------- 6c. 向导：跳过 / 导入可视化 ---------------- */

if (typeof studio.wizardSkip === "function" && studio.getWizard && studio.setActiveSection) {
  studio.setState(studio.defaultConfig());
  studio.setActiveSection("alignment");
  studio.wizardSkip();
  check("跳过 alignment 后标记 skipped 并前进到 lanes", studio.getWizard().skipped.alignment === true && studio.getActiveSection() === "lanes");
  studio.setActiveSection("welcome");
  studio.wizardSkip();
  check("welcome 不可跳过（保持原位）", studio.getActiveSection() === "welcome" && !studio.getWizard().skipped.welcome);
} else {
  check("向导函数存在（wizardSkip/getWizard）", false, "script.js 未导出向导函数");
}
{
  const d3aText = readFileSync(join(root, "examples/team-config.d3a-team-dt.yaml"), "utf8");
  const imported = studio.applyImportedYaml(d3aText);
  check("导入 YAML 成功并直接跳到策略总览", imported.ok === true && studio.getActiveSection() === "overview");
  check("导入后状态已合并（D3A 示例的 team 生效）", studio.getState().domain.mode === "d3a");
  const importedRun = runResolver(studio.buildYaml(studio.getState()), "imported_overview");
  check("导入后重新生成的 YAML 仍通过权威 resolver", importedRun.ok, importedRun.output.slice(0, 160));
}
{
  const bad = studio.applyImportedYaml("这是一行没有冒号的文本，不是合法 YAML 映射");
  check("导入非法 YAML 返回失败且不崩", bad.ok === false && typeof bad.error === "string");
}

/* ---------------- 6d. domain.enabled 多选 / Skills 增删 / Knowledge×D3A 联动 ---------------- */

if (typeof studio.setModeEnabled === "function" && typeof studio.enabledModes === "function") {
  studio.setState(studio.defaultConfig());
  check("默认 enabled = [general]（通用可选而非锁定）", JSON.stringify(studio.enabledModes()) === JSON.stringify(["general"]));
  studio.setModeEnabled("d3a", true);
  check("启用 D3A 后 enabled = general + d3a（真多选）", JSON.stringify(studio.enabledModes()) === JSON.stringify(["general", "d3a"]));
  check("主路由保持 general 不被覆盖", studio.getState().domain.mode === "general");
  studio.setPrimaryDomain("d3a");
  check("设为主路由后 mode=d3a 且包含于 enabled", studio.getState().domain.mode === "d3a" && studio.enabledModes().includes("d3a"));
  studio.setModeEnabled("general", false);
  check("可停用通用（enabled 只剩 d3a）", JSON.stringify(studio.enabledModes()) === JSON.stringify(["d3a"]));
  const d3aOnlyYaml = studio.buildYaml(studio.getState());
  check("YAML 输出 enabled 列表", d3aOnlyYaml.includes("enabled: [d3a]"));
  const d3aOnlyRun = runResolver(d3aOnlyYaml, "enabled_d3a_only");
  check("只启用 D3A（不含通用）的 YAML 通过权威 resolver", d3aOnlyRun.ok, d3aOnlyRun.output.slice(0, 200));
  check("浏览器侧检查通过（mode ∈ enabled / 无重复 / 合法值）", allChecksOk(studio.validateConfig()));
  studio.setModeEnabled("general", true);
  const multiRun = runResolver(studio.buildYaml(studio.getState()), "enabled_general_d3a");
  check("general + d3a 双启用 YAML 通过权威 resolver", multiRun.ok, multiRun.output.slice(0, 200));
  studio.setState(studio.defaultConfig());
  studio.setModeEnabled("general", false);
  check("停用唯一启用域被拒绝（enabled 至少一个）", JSON.stringify(studio.enabledModes()) === JSON.stringify(["general"]));
} else {
  check("多选函数存在（enabledModes/setModeEnabled）", false, "script.js 未导出多选函数");
}
{
  const customPrefill = studio.defaultConfig();
  studio.setState(customPrefill);
  const st = studio.getState();
  st.bindings.api_review = { skill_ref: ".claude/skills/idc-gc-sop-adapter/SKILL.md" };
  check("自定义 capability 进入 Lane 可用技能池", studio.availableSkillIds().includes("api_review"));
  const customYaml = studio.buildYaml(st);
  check("自定义 capability 输出到 YAML", customYaml.includes("api_review: {skill_ref: .claude/skills/idc-gc-sop-adapter/SKILL.md}"));
  const customRun = runResolver(customYaml, "custom_capability");
  check("含自定义 capability 的 YAML 通过权威 resolver", customRun.ok, customRun.output.slice(0, 200));
  st.lane.profiles.lite.skills.required = ["api_review"];
  check("被 Lane 引用后 referencedBindingKeys 覆盖该 key", studio.referencedBindingKeys().has("api_review"));
  delete st.bindings.api_review;
  check("删除被引用的 capability 后浏览器侧检查报错（引用一致性）", !allChecksOk(studio.validateConfig()));
}
{
  const linked = studio.defaultConfig();
  studio.setState(linked);
  const st = studio.getState();
  st.domain.mode = "d3a";
  st.domain.enabled = ["d3a"];
  st.knowledge.layer_docs.TRAN_CFG = "docs/architecture.md";
  const layerYaml = studio.buildYaml(st);
  check("Layer 映射输出到 YAML", layerYaml.includes("layer_docs:") && layerYaml.includes("TRAN_CFG: docs/architecture.md"));
  const layerRun = runResolver(layerYaml, "layer_docs_d3a");
  check("含 Layer 映射的 YAML 通过权威 resolver", layerRun.ok, layerRun.output.slice(0, 200));
}
{
  const tr3 = studio.defaultConfig();
  studio.applyAlignmentPreset(tr3, "tr3");
  const grilling = tr3.alignment.orchestration.steps.find((step) => step.id === "alignment-grilling");
  const withDocs = tr3.alignment.orchestration.steps.find((step) => step.id === "alignment-grilling-with-docs");
  const discovery = tr3.alignment.orchestration.steps.find((step) => step.id === "alignment-discovery");
  check("TR3 preset: 盘问步骤以 tr3_design_doc AND 缺口信号门控",
    grilling.trigger_signals.includes("tr3_design_doc") && grilling.trigger_signals.includes("critical_gaps_remain")
    && withDocs.trigger_signals.includes("tr3_design_doc"));
  check("TR3 preset: TR3 输入不触发 Discovery（跳过发散）", !discovery.trigger_signals.includes("tr3_design_doc"));
}

/* ---------------- 7. 纯函数单元 ---------------- */

check("csv 支持中英文逗号", JSON.stringify(studio.csv("a, b， c")) === JSON.stringify(["a", "b", "c"]));
const extensionRoundTrip = studio.textToExtensions("idc-team-api-review | api_review, code_review | review | .claude/skills/idc-gc-sop-adapter/SKILL.md | atomic_capability");
check("textToExtensions 解析 5 列", extensionRoundTrip.length === 1
  && extensionRoundTrip[0].id === "idc-team-api-review"
  && JSON.stringify(extensionRoundTrip[0].capability_keys) === JSON.stringify(["api_review", "code_review"])
  && extensionRoundTrip[0].execution_role === "atomic_capability");
const steps = [{ id: "s1", stage: "planning", skill_ids: ["tech_design"], trigger_signals: ["high_risk"] }];
if (typeof studio.laneStepsToText === "function" && typeof studio.textToLaneSteps === "function") {
  check("laneStepsToText ↔ textToLaneSteps round-trip", JSON.stringify(studio.textToLaneSteps(studio.laneStepsToText(steps))) === JSON.stringify(steps));
} else {
  console.log("跳过 laneSteps 文本 round-trip（当前 script.js 未提供该函数）");
}
check("parseYaml 解析 flow/引用/嵌套", (() => {
  const parsed = studio.parseYaml('a: [x, "y z", 3]\nb:\n  c: null\n  d: "quoted#hash"\nlist:\n  - id: one\n    knowledge_ref: docs/one.md\n');
  return JSON.stringify(parsed.a) === JSON.stringify(["x", "y z", 3])
    && parsed.b.c === null && parsed.b.d === "quoted#hash"
    && parsed.list[0].id === "one" && parsed.list[0].knowledge_ref === "docs/one.md";
})());
check("yamlScalar 对特殊字符加引号", studio.yamlScalar("hello: world").startsWith("\""));

/* ---------------- 8. Chrome headless 冒烟 ---------------- */

const chromeCandidates = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
];
const { existsSync } = await import("node:fs");
const chrome = chromeCandidates.find((candidate) => existsSync(candidate));
if (!chrome) {
  check("Chrome headless 冒烟测试", false, "未找到可用浏览器");
} else {
  const pageUrl = `file://${join(here, "index.html")}`;
  let dom = "";
  try {
    dom = execFileSync(chrome, ["--headless", "--disable-gpu", "--no-first-run", "--dump-dom", pageUrl], { encoding: "utf8", timeout: 45000, stdio: ["ignore", "pipe", "pipe"] });
  } catch (error) {
    check("Chrome headless 冒烟测试", false, String(error.message).slice(0, 200));
  }
  if (dom) {
    check("页面真实渲染: YAML 输出非空", dom.includes("config_version: 1"));
    check("页面真实渲染: 校验徽章为 Ready", dom.includes(">Ready<"));
    check("页面真实渲染: 9 个分区导航齐全（含向导 welcome）", ["welcome", "setup", "domains", "alignment", "lanes", "skills", "knowledge", "policy", "overview"]
      .every((section) => dom.includes(`data-section="${section}"`)));
    check("页面真实渲染: 策略总览入口存在", dom.includes("最终策略总览"));
    check("页面真实渲染: 欢迎页含开始/导入双入口", dom.includes("data-wizard-start") && dom.includes("data-import-open"));
    check("页面真实渲染: 向导条含上一步/下一步", dom.includes("data-wizard-prev") && dom.includes("data-wizard-next"));
    check("页面真实渲染: 欢迎页渲染完成", dom.includes("把团队工作方式接入 IDC harness"));
    check("页面真实渲染: 顶栏与标题改名 IDC HARNESS SETUP", dom.includes("IDC HARNESS SETUP"));
    const dumpView = async (hash) => {
      try {
        return execFileSync(chrome, ["--headless", "--disable-gpu", "--no-first-run", "--dump-dom", `${pageUrl}#${hash}`], { encoding: "utf8", timeout: 45000, stdio: ["ignore", "pipe", "pipe"] });
      } catch (_) { return ""; }
    };
    const setupDom = await dumpView("setup");
    check("页面真实渲染: 任务卡支持主路由标记与多选", setupDom.includes("主路由") && setupDom.includes("data-task-select=\"general\"") && setupDom.includes("domain.enabled"));
    const alignDom = await dumpView("alignment");
    check("页面真实渲染: TR3 输入预览开关存在", alignDom.includes("TR3 设计文档") && alignDom.includes("data-align-preset=\"tr3\""));
    const skillsDom = await dumpView("skills");
    check("页面真实渲染: capability 添加入口存在", skillsDom.includes("data-add-binding") && skillsDom.includes("+ 添加 capability"));
    const shotPath = "/tmp/idc-studio-visual-check.png";
    try {
      execFileSync(chrome, ["--headless", "--disable-gpu", "--no-first-run", "--window-size=1680,1050", `--screenshot=${shotPath}`, pageUrl], { timeout: 45000, stdio: ["ignore", "pipe", "pipe"] });
      check("视觉截图已生成", existsSync(shotPath), shotPath);
    } catch (error) {
      check("视觉截图已生成", false, String(error.message).slice(0, 200));
    }
  }
}

/* ---------------- 汇总 ---------------- */

console.log(`\n${passed} 项通过，${failures.length} 项失败。`);
if (failures.length) {
  failures.forEach((item) => console.log(`- ${item}`));
  process.exit(1);
}
process.exit(0);
