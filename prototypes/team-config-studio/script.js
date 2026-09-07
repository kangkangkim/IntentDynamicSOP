const STORAGE_KEY = "idc-team-config-studio-v1";

const CORE_BINDINGS = [
  "coding_standard", "brainstorming", "asis_miner", "scene_challenge", "req_check",
  "tech_design", "phase_plan", "ut_design", "ut_generate", "impl_review",
  "tdd_workflow", "static_scan", "defect_fix", "git_commit", "knowledge_archive",
  "system_test", "dt_design", "dt_writer", "dt_build", "tran_build"
];

const ALIGNMENT_BINDINGS = {
  intent_discovery: ".claude/skills/idc-intent-discovery/SKILL.md",
  brainstorming: ".claude/skills/idc-brainstorming/SKILL.md",
  intent_grilling: ".claude/skills/idc-intent-grilling/SKILL.md",
  intent_grilling_with_docs: ".claude/skills/idc-intent-grilling-with-docs/SKILL.md",
  intent_alignment: ".claude/skills/idc-intent-alignment/SKILL.md"
};

const DEFAULT_ALIGNMENT_STEPS = [
  { id: "alignment-discovery", stage: "discovery", skill_ids: ["intent_discovery"], trigger_signals: ["raw_idea"] },
  { id: "alignment-brainstorming", stage: "divergence", skill_ids: ["brainstorming"], trigger_signals: ["alternatives_needed"] },
  { id: "alignment-grilling", stage: "clarification", skill_ids: ["intent_grilling"], trigger_signals: ["critical_gaps_remain", "structured_requirement_input", "tr3_input"] },
  { id: "alignment-grilling-with-docs", stage: "clarification", skill_ids: ["intent_grilling_with_docs"], trigger_signals: ["docs_clarification_required"] },
  { id: "alignment-check", stage: "alignment_check", skill_ids: ["intent_alignment"], trigger_signals: [] }
];

/* Alignment 策略 preset：分流机制就是 trigger_signals——
   框架三类输入成熟度：raw_idea / structured_requirement / tr3_design_doc
   （另 approved_alignment 直接跳过 pre-alignment）。
   四个必需 stage（discovery/divergence/clarification/alignment_check）在任何 preset
   下都保留为步骤，靠信号门控决定是否执行（resolver 的硬性约束）。 */
const ALIGNMENT_PRESETS = {
  full: {
    label: "全覆盖",
    tagline: "三类输入混合出现，完整链路全保留",
    steps: DEFAULT_ALIGNMENT_STEPS
  },
  exploratory: {
    label: "探索型（raw_idea 为主）",
    tagline: "团队常带模糊想法来：raw_idea 即触发发散，多方案对比后再收敛",
    steps: [
      { id: "alignment-discovery", stage: "discovery", skill_ids: ["intent_discovery"], trigger_signals: ["raw_idea"] },
      { id: "alignment-brainstorming", stage: "divergence", skill_ids: ["brainstorming"], trigger_signals: ["raw_idea", "alternatives_needed"] },
      { id: "alignment-grilling", stage: "clarification", skill_ids: ["intent_grilling"], trigger_signals: ["critical_gaps_remain", "structured_requirement_input", "tr3_input"] },
      { id: "alignment-grilling-with-docs", stage: "clarification", skill_ids: ["intent_grilling_with_docs"], trigger_signals: ["docs_clarification_required"] },
      { id: "alignment-check", stage: "alignment_check", skill_ids: ["intent_alignment"], trigger_signals: [] }
    ]
  },
  structured: {
    label: "结构化型（structured 为主）",
    tagline: "需求已含目标/行为/验收线索：跳过发散，直接带文档收敛",
    steps: [
      { id: "alignment-discovery", stage: "discovery", skill_ids: ["intent_discovery"], trigger_signals: ["raw_idea"] },
      { id: "alignment-brainstorming", stage: "divergence", skill_ids: ["brainstorming"], trigger_signals: ["alternatives_needed"] },
      { id: "alignment-grilling", stage: "clarification", skill_ids: ["intent_grilling"], trigger_signals: ["structured_requirement_input", "critical_gaps_remain", "tr3_input"] },
      { id: "alignment-grilling-with-docs", stage: "clarification", skill_ids: ["intent_grilling_with_docs"], trigger_signals: ["docs_clarification_required"] },
      { id: "alignment-check", stage: "alignment_check", skill_ids: ["intent_alignment"], trigger_signals: [] }
    ]
  },
  /* TR3（tr3_design_doc）：TR3 Adapter 先解析，默认跳过 Discovery /
     Brainstorming，并通过 tr3_input 强制进入普通 Clarification。 */
  tr3: {
    label: "TR3 型（tr3_design_doc 为主）",
    tagline: "输入是 TR3 设计文档：跳过发散，强制普通盘问；带文档盘问仍按需触发",
    steps: [
      { id: "alignment-discovery", stage: "discovery", skill_ids: ["intent_discovery"], trigger_signals: ["raw_idea"] },
      { id: "alignment-brainstorming", stage: "divergence", skill_ids: ["brainstorming"], trigger_signals: ["alternatives_needed"] },
      { id: "alignment-grilling", stage: "clarification", skill_ids: ["intent_grilling"], trigger_signals: ["tr3_input", "critical_gaps_remain", "structured_requirement_input"] },
      { id: "alignment-grilling-with-docs", stage: "clarification", skill_ids: ["intent_grilling_with_docs"], trigger_signals: ["docs_clarification_required"] },
      { id: "alignment-check", stage: "alignment_check", skill_ids: ["intent_alignment"], trigger_signals: [] }
    ]
  }
};
const PREVIEW_SIGNALS = [
  { id: "raw_idea", label: "输入：raw idea（模糊想法）" },
  { id: "structured_requirement_input", label: "输入：structured requirement（结构化需求）" },
  { id: "tr3_input", label: "输入：TR3 设计文档" }
];

function applyAlignmentPreset(config, presetId) {
  const preset = ALIGNMENT_PRESETS[presetId];
  if (!preset) return false;
  config.alignment.orchestration.mode = "ordered";
  config.alignment.orchestration.steps = clone(preset.steps);
  return true;
}
function detectAlignmentPreset(config) {
  const steps = JSON.stringify(config.alignment.orchestration.steps);
  return Object.keys(ALIGNMENT_PRESETS).find((key) => JSON.stringify(ALIGNMENT_PRESETS[key].steps) === steps) || null;
}
function stepFiresOn(step, signal) {
  if (!signal) return null;
  if (!step.trigger_signals || !step.trigger_signals.length) return true;
  return step.trigger_signals.includes(signal);
}

const SECTIONS = [
  { id: "welcome", title: "开始", eyebrow: "00 / START", description: "两分钟接入你的团队：全新配置，或导入已有 team-config.yaml 直接可视化。" },
  { id: "setup", title: "团队与路由", eyebrow: "01 / SETUP", description: "先确定团队身份和默认 Domain。Domain 是第一层分流，不等同于 Lane。" },
  { id: "domains", title: "Domain 执行配置", eyebrow: "02 / DOMAINS", description: "分别查看和配置 General、D3A、Custom 的执行所有权。固定策略会明确锁定，可配置策略直接写入 team-config.yaml。" },
  { id: "alignment", title: "意图对齐管线", eyebrow: "03 / ALIGNMENT", description: "配置执行前的意图加工能力。步骤可调整顺序和绑定，但 Human Alignment Gate、必需阶段和信号下限仍由框架保护。" },
  { id: "lanes", title: "Lane 执行策略", eyebrow: "04 / LANES", description: "Fast、Lite、Complex 表示执行强度。把已绑定的原子能力拖入 Lane，并编排每个 Lane 的执行步骤。" },
  { id: "skills", title: "原子能力绑定", eyebrow: "05 / SKILLS", description: "将 Harness 的稳定 capability key 绑定到团队已有 Skill。企业命令留在 Skill 内，不进入配置文件。" },
  { id: "knowledge", title: "知识与上下文", eyebrow: "06 / KNOWLEDGE", description: "声明架构、Feature、Layer 和验证映射。运行时仍通过 Context Load Plan 渐进加载。" },
  { id: "policy", title: "选择与演进策略", eyebrow: "07 / POLICY", description: "控制最小充分能力预算与自优化模式。这些开关不会允许自动修改 IDC Core。" },
  { id: "overview", title: "最终策略总览", eyebrow: "08 / STRATEGY", description: "把 Alignment、Domain Router、Domain execution、Lane 和 Completion 汇总成最终运行策略。" }
];

function defaultConfig() {
  const bindings = {};
  CORE_BINDINGS.forEach((key) => { bindings[key] = { skill_ref: null }; });
  const alignmentBindings = {};
  Object.entries(ALIGNMENT_BINDINGS).forEach(([key, skill_ref]) => { alignmentBindings[key] = { skill_ref }; });
  return {
    config_version: 1,
    team: { id: "new-team", repo_path: "." },
    domain: {
      mode: "general",
      d3a: { dt_domains: [], orchestration: { mode: "framework_default", steps: [] } },
      custom: {
        id: null, trigger_rules: [], lane_policy: { mode: "dynamic", selected_lane: null },
        coding_layers: [], test_domains: [], required_contracts: ["task_contract", "verification_contract"],
        workflow_skill_ref: null, planner_skill_ref: null, completion_skill_ref: null,
        orchestration: { mode: "workflow_skill", steps: [] }
      }
    },
    general: { components: [], test_domains: [] },
    bindings,
    adapter_extensions: [],
    knowledge: {
      architecture_doc_ref: null, feature_docs_root_ref: null, layer_docs: {},
      lane_docs: { fast: [], lite: [], complex: [] }, verification_mapping_ref: null,
      repo_context: { provider_skill_ref: null, policy_ref: null, fallback: "bounded_grep" }
    },
    lane: {
      default: "lite",
      profiles: {
        fast: { skills: { allow: [], deny: [], required: [] }, orchestration: { mode: "autonomous", steps: [] } },
        lite: { skills: { allow: [], deny: [], required: [] }, orchestration: { mode: "autonomous", steps: [] } },
        complex: { skills: { allow: [], deny: [], required: [] }, orchestration: { mode: "autonomous", steps: [] } }
      }
    },
    capability_selection: {
      mode: "autonomous_minimal_sufficient",
      lane_profiles: { fast: { max_optional_skills: 1 }, lite: { max_optional_skills: 3 }, complex: { max_optional_skills: null } },
      d3a_profile: { max_optional_skills: null }, require_selected_and_skipped_reasons: true
    },
    self_optimization: {
      mode: "disabled", event_store_ref: null, replay_cases_ref: null, team_overlay_ref: null,
      promotion_requires_human_alignment: true, auto_modify_core: false
    },
    alignment: { bindings: alignmentBindings, orchestration: { mode: "ordered", steps: clone(DEFAULT_ALIGNMENT_STEPS) } }
  };
}

function clone(value) { return JSON.parse(JSON.stringify(value)); }

/* ---------------- Domain 多选（domain.enabled） ----------------
   schema 允许 enabled 为列表（d3a/general/custom 任意组合，去重、非空，
   mode 必须 ∈ enabled）。运行时未命中专用域触发规则的任务回落 General Coding，
   但「启用哪些域」由团队自选，通用不是必选项。 */
const D3A_LAYER_IDS = ["TRAN_CFG", "DO", "VISP_ADP", "TFC_TFI", "TFE", "ADP", "DRV"];

function enabledModes() {
  const enabled = get("domain.enabled");
  if (Array.isArray(enabled) && enabled.length) return enabled;
  return [get("domain.mode", "general")];
}

function setModeEnabled(requested, on) {
  const enabled = enabledModes().filter((id) => id !== requested);
  if (on) enabled.push(requested);
  if (!enabled.length) { toast("至少要启用一个 Domain（通用 / D3A / 自定义）"); return; }
  if (!enabled.includes(get("domain.mode", "general"))) state.domain.mode = enabled[0];
  state.domain.enabled = enabled;
  domainEditor = state.domain.mode;
  commit({ fullRender: true });
}

function setPrimaryDomain(requested) {
  const enabled = enabledModes();
  if (!enabled.includes(requested)) state.domain.enabled = [...enabled, requested];
  state.domain.mode = requested;
  domainEditor = requested;
  commit({ fullRender: true });
}

/* 顶层 bindings 中被 Lane 引用的 key：引用中的 capability 不允许删除。 */
function referencedBindingKeys() {
  const refs = new Set();
  ["fast", "lite", "complex"].forEach((lane) => {
    const profile = get(`lane.profiles.${lane}`);
    if (!profile) return;
    [...(profile.skills.allow || []), ...(profile.skills.deny || []), ...(profile.skills.required || [])].forEach((id) => refs.add(id));
    (profile.orchestration.steps || []).forEach((step) => (step.skill_ids || []).forEach((id) => refs.add(id)));
  });
  return refs;
}

let state = loadDraft() || defaultConfig();
let activeSection = "welcome";
let bindingFilter = "";
let domainEditor = get("domain.mode", "general");

/* ---------------- 向导状态机 ----------------
   visited: 通过「下一步」走完的分区；skipped: 显式跳过（保留框架默认）。
   两者互斥：跳过后再编辑会自动解除 skipped。 */
const WIZARD_STORAGE_KEY = "idc-team-config-studio-wizard-v1";
const SKIPPABLE_SECTIONS = new Set(["domains", "alignment", "lanes", "skills", "knowledge", "policy"]);
let wizard = loadWizard();
let previewSignal = null;

function loadWizard() {
  try { const saved = JSON.parse(localStorage.getItem(WIZARD_STORAGE_KEY)); if (saved && typeof saved.current === "number") return saved; } catch (_) { /* fallthrough */ }
  return { current: 0, visited: {}, skipped: {} };
}
function saveWizard() { localStorage.setItem(WIZARD_STORAGE_KEY, JSON.stringify(wizard)); }
function wizardSectionIndex() { return Math.max(0, SECTIONS.findIndex((item) => item.id === activeSection)); }
function wizardMarkCurrent() {
  const index = wizardSectionIndex();
  if (wizard.current !== index) { wizard.current = index; saveWizard(); }
}
function wizardAdvance(markVisited) {
  const next = Math.min(SECTIONS.length - 1, wizardSectionIndex() + 1);
  if (markVisited) { wizard.visited[activeSection] = true; delete wizard.skipped[activeSection]; }
  wizard.current = next; saveWizard();
  activeSection = SECTIONS[next].id; render();
}
function wizardGo(delta) {
  if (delta > 0) { wizardAdvance(true); return; }
  const prev = Math.max(0, wizardSectionIndex() - 1);
  wizard.current = prev; saveWizard();
  activeSection = SECTIONS[prev].id; render();
}
function wizardSkip() {
  if (!SKIPPABLE_SECTIONS.has(activeSection)) return;
  wizard.skipped[activeSection] = true; delete wizard.visited[activeSection];
  wizardAdvance(false);
}
function wizardJump(sectionId) {
  const index = SECTIONS.findIndex((item) => item.id === sectionId);
  if (index < 0) return;
  wizard.current = index; saveWizard();
  activeSection = sectionId; render();
}
function wizardStepStatus(sectionId) {
  const validation = validateConfig();
  if (validation.sectionErrors[sectionId]) return "error";
  if (wizard.skipped[sectionId]) return "skipped";
  if (wizard.visited[sectionId] || sectionId === activeSection) return "done";
  return "pending";
}

const nav = document.getElementById("sectionNav");
const content = document.getElementById("editorContent");
const yamlOutput = document.getElementById("yamlOutput");

function get(path, fallback = undefined) {
  const value = path.split(".").reduce((cursor, key) => cursor == null ? undefined : cursor[key], state);
  return value === undefined ? fallback : value;
}

function set(path, value) {
  const keys = path.split(".");
  let cursor = state;
  keys.slice(0, -1).forEach((key) => {
    if (!cursor[key] || typeof cursor[key] !== "object") cursor[key] = {};
    cursor = cursor[key];
  });
  cursor[keys[keys.length - 1]] = value;
  commit();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>\"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" })[char]);
}

function input(path, label, options = {}) {
  const value = get(path, options.default ?? "");
  const type = options.type || "text";
  let control;
  if (type === "select") {
    control = `<select data-bind="${path}">${options.options.map((item) => {
      const option = typeof item === "string" ? { value: item, label: item } : item;
      return `<option value="${escapeHtml(option.value)}" ${String(value ?? "") === String(option.value) ? "selected" : ""}>${escapeHtml(option.label)}</option>`;
    }).join("")}</select>`;
  } else if (type === "textarea") {
    control = `<textarea data-bind="${path}" data-value-type="${options.valueType || "string"}">${escapeHtml(formatInputValue(value, options.valueType))}</textarea>`;
  } else {
    control = `<input data-bind="${path}" data-value-type="${options.valueType || "string"}" value="${escapeHtml(formatInputValue(value, options.valueType))}" placeholder="${escapeHtml(options.placeholder || "")}" />`;
  }
  return `<div class="field ${options.full ? "full" : ""}"><label>${label}</label>${control}${options.help ? `<small>${options.help}</small>` : ""}</div>`;
}

function formatInputValue(value, valueType) {
  if (valueType === "csv") return Array.isArray(value) ? value.join(", ") : "";
  if (value === null || value === undefined) return "";
  return value;
}

function parseInputValue(element) {
  const type = element.dataset.valueType;
  const raw = element.value.trim();
  if (type === "csv") return raw ? raw.split(/[,，]/).map((item) => item.trim()).filter(Boolean) : [];
  if (type === "nullable-number") return raw === "" || raw === "null" ? null : Number(raw);
  if (type === "nullable") return raw || null;
  return element.value;
}

function renderNav() {
  nav.innerHTML = SECTIONS.map((section, index) => `
    <button class="nav-item ${section.id === activeSection ? "active" : ""}" data-section="${section.id}" data-status="${wizardStepStatus(section.id)}">
      <span class="nav-index">${section.eyebrow.slice(0, 2)}</span><span>${section.title}</span>
      <span class="nav-state ${wizardStepStatus(section.id)}"></span>
    </button>`).join("");
}

function render() {
  wizardMarkCurrent();
  const section = SECTIONS.find((item) => item.id === activeSection);
  document.getElementById("sectionEyebrow").textContent = section.eyebrow;
  document.getElementById("sectionTitle").textContent = section.title;
  document.getElementById("sectionDescription").textContent = section.description;
  document.getElementById("teamSummary").textContent = get("team.id", "new-team");
  document.getElementById("domainSummary").textContent = `${String(get("domain.mode", "general")).toUpperCase()} Domain`;
  renderNav();
  const renderers = { welcome: renderWelcome, setup: renderSetup, domains: renderDomains, alignment: renderAlignment, lanes: renderLanes, skills: renderSkills, knowledge: renderKnowledge, policy: renderPolicy, overview: renderOverview };
  content.innerHTML = renderers[activeSection]();
  bindRenderedControls();
  renderWizardBar();
  renderYamlAndValidation();
}

function renderWizardBar() {
  const bar = document.getElementById("wizardBar");
  if (!bar) return;
  const index = wizardSectionIndex();
  const sectionId = activeSection;
  const canSkip = SKIPPABLE_SECTIONS.has(sectionId);
  const basicsMissing = sectionId === "setup" && (!get("team.id") || !get("team.repo_path"));
  const isLast = index === SECTIONS.length - 1;
  bar.innerHTML = `
    <button class="button secondary" type="button" data-wizard-prev ${index === 0 ? "disabled" : ""}>← 上一步</button>
    <span class="wizard-bar-note">${basicsMissing ? "先填写 Team ID 和 Repository Path 再继续。" : canSkip ? "拿不准可以先跳过，保留框架默认值，之后再回来调。" : isLast ? "检查策略图与 YAML，确认后下载。" : "这一步不可跳过。"}</span>
    <div class="wizard-bar-actions">
      ${canSkip ? `<button class="button ghost" type="button" data-wizard-skip>跳过此步 →</button>` : ""}
      ${isLast ? `<button class="button primary" type="button" data-wizard-download>下载 team-config.yaml</button>`
        : `<button class="button primary" type="button" data-wizard-next ${basicsMissing ? "disabled" : ""}>下一步 →</button>`}
    </div>`;
}

function renderWelcome() {
  const mode = get("domain.mode", "general");
  return `
    <section class="surface welcome-hero">
      <div class="welcome-copy">
        <span class="eyebrow">IDC HARNESS SETUP</span>
        <h2>把团队工作方式接入 IDC harness</h2>
        <p>回答几个问题，产出唯一配置源 <code>team-config.yaml</code>。Domain 执行编排、三条 Lane 策略、意图对齐管线都会逐步引导；任何一步都可以跳过并保留框架默认。</p>
      </div>
      <div class="welcome-actions">
        <button class="button primary big" type="button" data-wizard-start>开始配置 →</button>
        <button class="button secondary big" type="button" data-import-open>导入已有 team-config.yaml</button>
      </div>
      <div class="welcome-steps">
        <div><strong>01</strong><span>团队身份与任务类型</span></div>
        <div><strong>02</strong><span>意图对齐策略（按输入成熟度分流）</span></div>
        <div><strong>03</strong><span>Lane 与原子能力编排</span></div>
        <div><strong>04</strong><span>策略总览图 + YAML 下载</span></div>
      </div>
      <div class="welcome-resume">当前草稿：<strong>${escapeHtml(get("team.id", "new-team"))}</strong> · Domain：<strong>${mode}</strong>${Object.keys(wizard.visited).length || Object.keys(wizard.skipped).length ? ` · 已完成 ${Object.keys(wizard.visited).length} 步，跳过 ${Object.keys(wizard.skipped).length} 步` : ""}</div>
    </section>`;
}

function bindRenderedControls() {
  const addAlignment = content.querySelector("[data-add-alignment]");
  if (addAlignment) addAlignment.dataset.bound = "true";
  if (addAlignment) addAlignment.onclick = (event) => {
    event.stopPropagation();
    const steps = state.alignment.orchestration.steps;
    const gateIndex = steps.findIndex((step) => step.stage === "alignment_check");
    const step = { id: `alignment-step-${steps.length + 1}`, stage: "clarification", skill_ids: ["intent_grilling"], trigger_signals: [] };
    steps.splice(gateIndex < 0 ? steps.length : gateIndex, 0, step);
    commit({ fullRender: true });
    requestAnimationFrame(() => {
      const pipeline = document.getElementById("alignmentPipeline");
      if (pipeline) pipeline.scrollLeft = pipeline.scrollWidth;
    });
  };
}

function renderSetup() {
  const mode = get("domain.mode", "general");
  const enabled = enabledModes();
  const card = (id, title, desc, offDesc) => `
    <button type="button" class="task-type-card ${enabled.includes(id) ? "on" : ""}" data-task-select="${id}">
      <div class="task-check">✓</div>
      ${mode === id ? `<span class="primary-badge">主路由</span>` : ""}
      <strong>${title}</strong>
      <span>${desc}</span>
      <small>${enabled.includes(id) ? (mode === id ? "已启用并作为主路由" : "已启用；未命中触发/兜底规则的任务回落主路由") : offDesc}</small>
      ${enabled.includes(id) && mode !== id ? `<span class="set-primary" data-task-primary="${id}">设为主路由</span>` : ""}
    </button>`;
  return `
    <section class="surface">
      <div class="surface-head"><div><h3>Team Identity</h3><p>配置只属于接入团队，repo_path 是 Skill 与知识引用的解析根。</p></div></div>
      <div class="surface-body form-grid">
        ${input("team.id", "Team ID", { placeholder: "payment-platform" })}
        ${input("team.repo_path", "Repository Path", { placeholder: "." })}
      </div>
    </section>
    <section class="surface">
      <div class="surface-head">
        <div><h3>团队主要面向哪类开发任务？</h3><p>可多选（对应 <code>domain.enabled</code> 列表）：通用 / D3A / 自定义按需任意组合，其中一个是主路由（<code>domain.mode</code>）。</p></div>
      </div>
      <div class="task-type-grid">
        ${card("general", "通用开发 General", "feature / bugfix / refactor / 文档等常规任务，走 Fast·Lite·Complex Lane 动态执行", "点击启用")}
        ${card("d3a", "D3A 专用域", "团队独有：DT 测试先行的固定工作流（DT GREEN + tran_build 才算完成）", "点击启用")}
        ${card("custom", "自定义 Domain", "团队内联注册触发规则 + Planner / Workflow / Completion 三件套", "点击启用")}
      </div>
      <p class="task-type-note">启用集合写到 <code>domain.enabled</code>，主路由写到 <code>domain.mode</code>（必须包含在 enabled 中）。运行时未命中 D3A / 自定义域触发规则的任务回落 General Coding——这是框架内置兜底，不需要显式勾选通用。</p>
      <div class="route-map">
        <div class="route-row">
          <div class="route-source"><strong>Normalized Request</strong><span>意图、仓库信号、任务形态</span></div>
          <div class="route-arrow">-&gt;</div>
          ${domainOption("general", "General Coding", "Lane-driven dynamic workflow", mode)}
          ${domainOption("d3a", "D3A", "Fixed workflow, Lane N/A", mode)}
          ${domainOption("custom", "Custom Domain", "Team-owned inline module", mode)}
        </div>
        <div class="route-foot"><span>Enabled</span><strong>${enabled.join(" + ")}</strong><span>主路由</span><strong>${mode}</strong><span>${mode === "d3a" ? "跳过 Lane Resolver" : mode === "custom" ? `Lane policy: ${get("domain.custom.lane_policy.mode", "dynamic")}` : "动态选择 Fast / Lite / Complex"}</span></div>
      </div>
    </section>`;
}

function domainOption(id, title, description, selected) {
  return `<div class="route-option ${selected === id ? "selected" : ""}"><strong>${title}</strong><span>${description}</span><button type="button" data-domain="${id}" aria-label="选择 ${title}"></button></div>`;
}

function renderDomains() {
  const selected = get("domain.mode", "general");
  return `<section class="surface domain-config-shell">
    <div class="surface-head">
      <div><h3>Domain Configuration</h3><p>当前运行使用 <strong>${selected}</strong>；切换下方标签只查看配置，不改变运行路由。</p></div>
      <div class="domain-tabs">
        ${["general", "d3a", "custom"].map((domain) => `<button type="button" class="${domainEditor === domain ? "active" : ""}" data-domain-editor="${domain}">${domain.toUpperCase()}</button>`).join("")}
      </div>
    </div>
    <div class="domain-editor-banner ${domainEditor}">
      <div><span class="eyebrow">${domainEditor === "d3a" ? "TEAM-OWNED SPECIAL DOMAIN" : domainEditor === "custom" ? "INLINE TEAM DOMAIN" : "BUILT-IN FALLBACK DOMAIN"}</span><h3>${domainTitle(domainEditor)}</h3><p>${domainDescription(domainEditor)}</p></div>
      ${selected === domainEditor ? `<span class="status good">当前启用</span>` : `<button class="button secondary" type="button" data-activate-domain="${domainEditor}">设为当前 Domain</button>`}
    </div>
    <div class="domain-editor-body">${domainEditor === "general" ? renderGeneralDomain() : domainEditor === "d3a" ? renderD3aDomain() : renderCustomDomain()}</div>
  </section>`;
}

function domainTitle(domain) {
  return domain === "d3a" ? "D3A Fixed Workflow" : domain === "custom" ? (get("domain.custom.id") || "Custom Domain") : "General Coding";
}

function domainDescription(domain) {
  if (domain === "d3a") return "D3A 是当前团队独有能力。它不经过 Lane Resolver，执行顺序和 Completion Gate 由 Harness 固定。";
  if (domain === "custom") return "团队内联注册 Planner、Workflow、Completion，并选择是否复用 Lane。";
  return "大多数团队的默认路径。Domain 负责边界，Fast / Lite / Complex Lane 负责执行强度和 Skill 编排。";
}

function renderGeneralDomain() {
  return `<div class="execution-map general-map">
      <div class="execution-node domain-node"><span>DOMAIN</span><strong>General Coding</strong><small>lane_policy: dynamic</small></div>
      <div class="execution-arrow">-&gt;</div>
      <div class="execution-node router-node"><span>ROUTER</span><strong>Lane Resolver</strong><small>fast / lite / complex</small></div>
      <div class="execution-arrow">-&gt;</div>
      <div class="execution-node skill-node"><span>EXECUTION</span><strong>Lane steps</strong><small>在 Lane 页面编排</small></div>
      <div class="execution-arrow">-&gt;</div>
      <div class="execution-node gate-node"><span>GATE</span><strong>Evidence Gate</strong><small>tests / build</small></div>
    </div>
    <div class="subsection-head"><div><h3>General Registries</h3><p>非空列表会整体替换 Harness 默认 registry。</p></div><button class="button secondary" type="button" data-jump-section="lanes">配置 Lane 编排</button></div>
    <div class="form-grid">
    ${registryBlock("general.components", "Components（编码层 / 组件）", get("general.components", []), "声明这个域覆盖哪些代码模块或分层，每行 = id + 该层的知识文档引用。运行时按受影响的 layer <strong>渐进加载</strong>知识（不是全量塞给 agent）。留空沿用 Harness 默认 registry；填了就是<strong>整体替换</strong>（不与默认合并）。")}
    ${registryBlock("general.test_domains", "Test Domains（验证域）", get("general.test_domains", []), "声明任务完成需要哪些测试域提供证据，每行 = id + 该测试域如何运行的知识文档引用。Completion Gate 按这里检查 required 测试域是否通过。")}
  </div>`;
}

function renderD3aDomain() {
  return `<div class="locked-policy"><strong>Lane: Not Applicable</strong><span>D3A 使用 d3a_fixed_workflow，不能把它误配成 Fast / Lite / Complex。</span></div>
    <div class="execution-map d3a-map">
      ${d3aExecutionNode("dt_design", "DT Design")}<div class="execution-arrow">-&gt;</div>
      ${d3aExecutionNode("dt_writer", "DT Writer")}<div class="execution-arrow">-&gt;</div>
      ${d3aExecutionNode("dt_build", "DT GREEN")}<div class="execution-arrow">-&gt;</div>
      ${d3aExecutionNode("tran_build", "tran_build PASS")}<div class="execution-arrow">-&gt;</div>
      <div class="execution-node gate-node"><span>FIXED GATE</span><strong>Done</strong><small>required DT GREEN</small></div>
    </div>
    <div class="subsection-head"><div><h3>D3A Execution Skill Bindings</h3><p>可以替换 Skill 实现，但固定顺序和 Gate 不可改。</p></div></div>
    <div class="binding-list compact-bindings">${["dt_design", "dt_writer", "dt_build", "tran_build"].map((key) => bindingCard(`bindings.${key}.skill_ref`, key, "d3a_fixed_workflow")).join("")}</div>
    <div class="subsection-head"><div><h3>D3A Test Domains（DT Domains）</h3><p>D3A Coding Layer 固定为 TRAN_CFG / DO / VISP_ADP / TFC_TFI / TFE / ADP / DRV（不可增删）；这里的 test_domains 就是 DT Domain（默认 TPRINT / FW / DPF placeholder），非空即整体替换默认 DT registry。完成标准 = 所有 required DT domain GREEN + tran_build PASS。</p></div></div>
    <div>
    ${registryBlock("domain.d3a.dt_domains", "DT Domains", get("domain.d3a.dt_domains", []), "每行 = DT Domain id + 该域知识文档引用。Coding Layer → DT Domain 是多对多映射，由 Harness 决定，不在这里配置。")}
  </div>`;
}

function d3aExecutionNode(binding, label) {
  const bound = get(`bindings.${binding}.skill_ref`);
  return `<div class="execution-node skill-node ${bound ? "bound" : "unbound"}"><span>SKILL</span><strong>${label}</strong><small>${bound ? binding : "not bound"}</small></div>`;
}

function renderCustomDomain() {
  const policy = get("domain.custom.lane_policy.mode", "dynamic");
  const laneLabel = policy === "fixed" ? `Fixed ${get("domain.custom.lane_policy.selected_lane", "lite")}` : policy === "dynamic" ? "Lane Resolver" : "Lane N/A";
  return `<div class="execution-map custom-map">
      ${customExecutionNode("planner_skill_ref", "Planner")}<div class="execution-arrow">-&gt;</div>
      <div class="execution-node router-node"><span>LANE POLICY</span><strong>${laneLabel}</strong><small>${policy}</small></div><div class="execution-arrow">-&gt;</div>
      ${customExecutionNode("workflow_skill_ref", "Workflow")}<div class="execution-arrow">-&gt;</div>
      ${customExecutionNode("completion_skill_ref", "Completion")}
    </div>
    <div class="subsection-head"><div><h3>Inline Custom Domain</h3><p>Resolver 会从本段动态注册 Domain Module，不需要修改共享 registry。</p></div></div>
    <div class="form-grid">
    ${input("domain.custom.id", "Domain ID", { valueType: "nullable", placeholder: "payment" })}
    ${input("domain.custom.trigger_rules", "Trigger Rules", { valueType: "csv", placeholder: "payment_change, billing_api" })}
    ${input("domain.custom.lane_policy.mode", "Lane Policy", { type: "select", options: ["dynamic", "fixed", "not_applicable"] })}
    ${get("domain.custom.lane_policy.mode") === "fixed" ? input("domain.custom.lane_policy.selected_lane", "Selected Lane", { type: "select", options: ["fast", "lite", "complex"] }) : ""}
    ${input("domain.custom.required_contracts", "Required Contracts", { valueType: "csv", full: true })}
    ${input("domain.custom.workflow_skill_ref", "Workflow Skill", { valueType: "nullable", placeholder: "team://skills/workflow/SKILL.md" })}
    ${input("domain.custom.planner_skill_ref", "Planner Skill", { valueType: "nullable" })}
    ${input("domain.custom.completion_skill_ref", "Completion Skill", { valueType: "nullable", full: true })}
    ${registryBlock("domain.custom.coding_layers", "Coding Layers（编码层）", get("domain.custom.coding_layers", []), "自建 Domain 没有固定分层，团队自己声明（例如 api / service / storage），每行 = id + 该层知识文档引用。执行时只加载受影响 layer 的知识。Resolver 要求至少一行。")}
    ${registryBlock("domain.custom.test_domains", "Test Domains（验证域）", get("domain.custom.test_domains", []), "自建 Domain 的验证域：Completion Gate 检查这些域的测试证据后才算完成。每行 = id + 该域如何运行的知识文档引用。Resolver 要求至少一行。")}
  </div>`;
}

function customExecutionNode(key, label) {
  const ref = get(`domain.custom.${key}`);
  return `<div class="execution-node skill-node ${ref ? "bound" : "unbound"}"><span>DOMAIN SKILL</span><strong>${label}</strong><small>${ref ? ref.split("/").slice(-2, -1)[0] || "bound" : "not bound"}</small></div>`;
}

function registryBlock(path, title, rows, hint = "") {
  const rowMarkup = rows.length ? rows.map((row, index) => `<div class="registry-row">
    <input data-registry-path="${path}" data-index="${index}" data-key="id" value="${escapeHtml(row.id || "")}" placeholder="ID" />
    <input data-registry-path="${path}" data-index="${index}" data-key="knowledge_ref" value="${escapeHtml(row.knowledge_ref || "")}" placeholder="knowledge_ref" />
    <button class="row-remove" type="button" data-remove-registry="${path}" data-index="${index}" title="删除" aria-label="删除">x</button>
  </div>`).join("") : `<div class="empty-row">未覆盖，使用 Harness 默认值</div>`;
  return `<div class="field full"><label>${title}</label>${hint ? `<p class="registry-hint">${hint}</p>` : ""}<div class="registry">${rowMarkup}</div><div><button class="button secondary" type="button" data-add-registry="${path}">Add row</button></div></div>`;
}

function renderAlignment() {
  const steps = get("alignment.orchestration.steps", []);
  const activePreset = detectAlignmentPreset(state);
  return `<section class="surface"><div class="surface-head"><div><h3>对齐策略：团队输入通常长什么样？</h3><p>框架定义三类输入成熟度：raw idea 先经 Discovery 发散，structured requirement 跳过发散直接收敛，TR3 设计文档由 TR3 Adapter 解析后按缺口收敛。选一个策略预设，再按需微调步骤。</p></div><div class="head-actions"><span class="status good">ordered</span></div></div>
    <div class="preset-grid">
      ${Object.entries(ALIGNMENT_PRESETS).map(([key, preset]) => `
        <button type="button" class="preset-card ${activePreset === key ? "on" : ""}" data-align-preset="${key}">
          <div class="preset-badge">${activePreset === key ? "当前策略" : "应用"}</div>
          <strong>${preset.label}</strong>
          <span>${preset.tagline}</span>
        </button>`).join("")}
      <div class="preset-card custom ${activePreset ? "" : "on"}">
        <div class="preset-badge">${activePreset ? "自定义" : "当前策略"}</div>
        <strong>自定义编排</strong>
        <span>直接增删改下方步骤；不匹配任何预设即视为自定义策略</span>
      </div>
    </div>
    <div class="signal-preview-bar">
      <span class="signal-preview-label">路径预览</span>
      ${PREVIEW_SIGNALS.map((signal) => `<button type="button" class="signal-preview-toggle ${previewSignal === signal.id ? "on" : ""}" data-signal-preview="${signal.id}">${signal.label}</button>`).join("")}
      ${previewSignal ? `<button type="button" class="signal-preview-clear" data-signal-preview-clear>清除</button><span class="signal-preview-note">高亮 = 该输入下会执行的步骤（按信号精确匹配；运行时由 Requirement Assessor 综合判定）</span>` : `<span class="signal-preview-note">点击一种输入，高亮查看它会走的链路</span>`}
    </div>
    <div class="pipeline-toolbar"><button class="button secondary" data-add-alignment type="button">+ Add step</button><span>新增步骤会插入 Human Alignment Gate 之前</span></div>
    <div class="pipeline" id="alignmentPipeline">
      ${steps.map((step, index) => {
        const fires = stepFiresOn(step, previewSignal);
        const dimClass = previewSignal && fires === false ? " dimmed" : "";
        const fireClass = previewSignal && fires === true ? " fires" : "";
        return `${index ? `<div class="pipeline-arrow ${previewSignal && (stepFiresOn(steps[index - 1], previewSignal) === false || fires === false) ? "dimmed" : ""}">-&gt;</div>` : ""}${alignmentStep(step, index, dimClass + fireClass)}`;
      }).join("")}
    </div>
  </section>
  <section class="surface"><div class="surface-head"><div><h3>Alignment Skill Bindings</h3><p>可替换实现，但 skill_ref 必须保持 idc-*/SKILL.md 形态。</p></div></div>
    <div class="surface-body binding-list">${Object.keys(get("alignment.bindings", {})).map((key) => bindingCard(`alignment.bindings.${key}.skill_ref`, key, "pre-alignment")).join("")}</div>
  </section>`;
}

function alignmentStep(step, index, extraClass = "") {
  const gate = step.stage === "alignment_check";
  return `<article class="pipeline-step ${gate ? "gate" : ""}${extraClass}" data-align-index="${index}">
    <div class="step-card-head"><span class="drag-handle">DRAG ${String(index + 1).padStart(2, "0")}</span>${gate ? `<span class="locked-label">LOCKED</span>` : `<button class="mini-remove" type="button" data-remove-alignment="${index}" aria-label="删除步骤">x</button>`}</div>
    <strong>${escapeHtml(step.id)}</strong>
    <select data-align-field="stage" data-index="${index}" ${gate ? "disabled" : ""}>${["discovery", "divergence", "clarification", "alignment_check"].map((stage) => `<option ${step.stage === stage ? "selected" : ""}>${stage}</option>`).join("")}</select>
    <select data-align-field="skill_ids" data-index="${index}">${Object.keys(get("alignment.bindings", {})).map((key) => `<option ${step.skill_ids[0] === key ? "selected" : ""}>${key}</option>`).join("")}</select>
    <input data-align-field="trigger_signals" data-index="${index}" value="${escapeHtml(step.trigger_signals.join(", "))}" placeholder="always" />
    <span class="step-signal">${step.trigger_signals.length ? `if ${escapeHtml(step.trigger_signals.join(" + "))}` : "always / framework gate"}</span>
  </article>`;
}

function renderLanes() {
  const allSkills = availableSkillIds();
  const d3aNotice = get("domain.mode") === "d3a"
    ? `<div class="locked-policy d3a-lane-note"><strong>D3A 模式下 Lane 不适用</strong><span>当前 Domain 是 D3A 固定工作流，执行顺序由 Harness 锁定（DT GREEN → tran_build PASS）。可以直接跳过此步；下方 Lane 配置仅在未来切回通用/自定义 Domain 时生效。</span></div>`
    : "";
  return `${d3aNotice}<section class="surface"><div class="surface-head"><div><h3>Available Skill Palette</h3><p>拖动能力到 Lane。空 allow 表示该 Lane 可使用全部符合 registry 条件的已绑定能力。</p></div><span class="status neutral">Default: ${escapeHtml(get("lane.default", "lite"))}</span></div>
    <div class="surface-body"><div class="skill-zone" data-lane="palette">${allSkills.length ? allSkills.map((skill) => skillChip(skill, "palette", false)).join("") : `<span class="empty-row">先到“原子能力绑定”填写 skill_ref</span>`}</div></div>
  </section>
  <section class="surface"><div class="surface-head"><div><h3>Lane Profiles</h3><p>Required 必须在 allow 中（allow 非空时），deny 的优先级最高。</p></div>
    <div class="field"><select data-bind="lane.default">${["fast", "lite", "complex"].map((lane) => `<option ${get("lane.default") === lane ? "selected" : ""}>${lane}</option>`).join("")}</select></div></div>
    <div class="lane-board">${["fast", "lite", "complex"].map((lane) => laneColumn(lane)).join("")}</div>
  </section>`;
}

function laneColumn(lane) {
  const profile = get(`lane.profiles.${lane}`);
  const allowed = profile.skills.allow || [];
  const required = profile.skills.required || [];
  return `<div class="lane-column ${lane}"><div class="lane-head"><strong>${lane}</strong><p>${lane === "fast" ? "小闭环 / low risk" : lane === "lite" ? "标准闭环 / normal delivery" : "强闭环 / high risk"}</p></div>
    <div class="lane-body">
      <div class="field"><label>Allowed Skills</label><div class="skill-zone" data-lane="${lane}">${allowed.length ? allowed.map((skill) => skillChip(skill, lane, required.includes(skill))).join("") : `<span class="empty-row">Empty = all eligible</span>`}</div></div>
      <div class="lane-fields">
        ${input(`lane.profiles.${lane}.skills.required`, "Required", { valueType: "csv", placeholder: "tech_design" })}
        ${input(`lane.profiles.${lane}.skills.deny`, "Deny", { valueType: "csv", placeholder: "git_commit" })}
        ${input(`lane.profiles.${lane}.orchestration.mode`, "Orchestration", { type: "select", options: ["autonomous", "ordered"] })}
        <div class="field"><label>Execution Steps</label><div class="lane-step-list" data-lane-step-list="${lane}">${profile.orchestration.steps.length ? profile.orchestration.steps.map((step, index) => laneStepCard(lane, step, index)).join("") : `<div class="empty-row">Autonomous selection / no fixed steps</div>`}</div><button class="button secondary add-step-button" type="button" data-add-lane-step="${lane}">Add execution step</button></div>
        ${input(`capability_selection.lane_profiles.${lane}.max_optional_skills`, "Max optional", { valueType: "nullable-number", placeholder: "null" })}
      </div>
    </div></div>`;
}

function laneStepCard(lane, step, index) {
  return `<article class="lane-step-card" data-lane-step-lane="${lane}" data-lane-step-index="${index}">
    <div class="step-card-head"><span class="drag-handle">STEP ${String(index + 1).padStart(2, "0")}</span><button class="mini-remove" type="button" data-remove-lane-step="${lane}" data-index="${index}" aria-label="删除步骤">x</button></div>
    <input data-lane-step-field="id" data-lane="${lane}" data-index="${index}" value="${escapeHtml(step.id)}" placeholder="step-id" />
    <select data-lane-step-field="stage" data-lane="${lane}" data-index="${index}">${["discovery", "planning", "implementation", "review", "verification", "fix", "completion"].map((stage) => `<option ${step.stage === stage ? "selected" : ""}>${stage}</option>`).join("")}</select>
    <input data-lane-step-field="skill_ids" data-lane="${lane}" data-index="${index}" value="${escapeHtml((step.skill_ids || []).join(", "))}" placeholder="drop skill or enter IDs" />
    <input data-lane-step-field="trigger_signals" data-lane="${lane}" data-index="${index}" value="${escapeHtml((step.trigger_signals || []).join(", "))}" placeholder="trigger signals (optional)" />
  </article>`;
}

function skillChip(skill, lane, required) {
  return `<span class="skill-chip ${required ? "required" : ""}" draggable="true" data-skill="${escapeHtml(skill)}" data-source-lane="${lane}" title="拖动到 Lane；双击移除">${escapeHtml(skill)}</span>`;
}

function renderSkills() {
  const filter = bindingFilter.toLowerCase();
  const referenced = referencedBindingKeys();
  const keys = Object.keys(get("bindings", {})).filter((key) => key.includes(filter));
  const cards = keys.map((key) => bindingCard(`bindings.${key}.skill_ref`, key, skillGroup(key), referenced.has(key))).join("");
  return `<section class="surface"><div class="surface-head"><div><h3>Capability Bindings</h3><p>Capability key 是稳定接口，Skill 实现可以来自团队仓或 Harness。框架 key 之外可以添加团队自己的 capability，也可以删除未绑定 / 未被引用的条目。</p></div><input class="filter-input" id="bindingFilter" value="${escapeHtml(bindingFilter)}" placeholder="Filter capability" /></div>
    <div class="surface-body binding-list">${cards}</div>
    <div class="add-binding-row">
      <input id="newBindingKey" placeholder="新 capability key，例如 api_review" />
      <button class="button secondary" type="button" data-add-binding>+ 添加 capability</button>
      <small>key 用小写字母 / 数字 / 下划线；填好 skill_ref 后即可被 Lane 引用。</small>
    </div>
  </section>
  <section class="surface"><div class="surface-head"><div><h3>Adapter Extensions</h3><p>每行：id | capability keys | stages | skill_ref | role。扩展不能接管 Domain、Lane、Contract、Alignment 或 Completion。</p></div></div>
    <div class="surface-body">${input("_extensions_editor", "Team-owned capabilities", { type: "textarea", full: true, placeholder: "idc-team-api-review | api_review | review | team://skills/api-review/SKILL.md | atomic_capability" })}</div>
  </section>`;
}

function skillGroup(key) {
  if (!CORE_BINDINGS.includes(key)) return "custom";
  if (key.startsWith("dt_") || key === "tran_build") return "D3A";
  if (["static_scan", "system_test", "impl_review"].includes(key)) return "verification";
  if (["brainstorming", "asis_miner", "scene_challenge", "req_check"].includes(key)) return "intent / design";
  return "general coding";
}

function bindingCard(path, key, group, referenced) {
  const value = get(path, null);
  return `<div class="binding-card ${value ? "bound" : ""}"><div class="binding-title"><strong>${escapeHtml(key)}</strong><span>${escapeHtml(group)}</span></div><input data-bind="${path}" data-value-type="nullable" value="${escapeHtml(value || "")}" placeholder="team://skills/.../SKILL.md" />${referenced ? `<span class="remove-binding disabled" title="仍被 Lane 引用，先解除引用">🔒</span>` : `<button class="remove-binding" type="button" data-remove-binding="${escapeHtml(key)}" aria-label="删除 ${escapeHtml(key)}" title="删除该 capability">✕</button>`}</div>`;
}

function renderKnowledge() {
  const layerDocs = Object.entries(get("knowledge.layer_docs", {}));
  const enabled = enabledModes();
  const usesLayers = enabled.some((id) => id !== "general");
  const mappedIds = layerDocs.map(([id]) => id);
  const suggestions = [...D3A_LAYER_IDS, ...(get("domain.custom.coding_layers", []) || []).map((row) => row.id).filter(Boolean)]
    .filter((id, index, list) => id && !mappedIds.includes(id) && list.indexOf(id) === index);
  const linkBanner = usesLayers
    ? `<div class="knowledge-link"><strong>已联动 ${enabled.filter((id) => id !== "general").join(" + ")}</strong><span>Layer Docs 是 Domain 执行时的渐进加载映射：只加载受影响的 coding layer（D3A Layer 固定为 TRAN_CFG / DO / VISP_ADP / TFC_TFI / TFE / ADP / DRV，不可增删层，只能增删映射行）。</span></div>`
    : `<div class="knowledge-link off"><strong>当前只启用通用域</strong><span>Layer 文档映射只在 D3A / 自定义域执行时加载；纯通用团队可以跳过，留空即可。</span></div>`;
  return `<section class="surface"><div class="surface-head"><div><h3>Knowledge Sources</h3><p>这里声明引用，不放企业知识正文。</p></div></div><div class="surface-body form-grid">
    ${input("knowledge.architecture_doc_ref", "Architecture Doc", { valueType: "nullable", placeholder: "docs/architecture.md" })}
    ${input("knowledge.feature_docs_root_ref", "Feature Docs Root", { valueType: "nullable", placeholder: "docs" })}
    ${input("knowledge.verification_mapping_ref", "Verification Mapping", { valueType: "nullable" })}
    ${input("knowledge.repo_context.provider_skill_ref", "Repo Context Provider", { valueType: "nullable" })}
    ${input("knowledge.repo_context.policy_ref", "Repo Context Policy", { valueType: "nullable" })}
    ${input("knowledge.repo_context.fallback", "Fallback", { type: "select", options: ["bounded_grep", "none"] })}
    <div class="field full ${usesLayers ? "" : "dimmed"}">
      <label>Layer Docs（按 Domain Layer 渐进加载）</label>
      ${linkBanner}
      <datalist id="layerDocIds">${suggestions.map((id) => `<option value="${escapeHtml(id)}"></option>`).join("")}</datalist>
      ${suggestions.length && usesLayers ? `<div class="layer-chips">${suggestions.map((id) => `<button type="button" class="layer-chip" data-add-layer-doc="${escapeHtml(id)}">+ ${escapeHtml(id)}</button>`).join("")}</div>` : ""}
      <div class="registry">${layerDocs.length ? layerDocs.map(([id, ref], index) => `<div class="registry-row"><input data-layer-doc-index="${index}" data-key="id" value="${escapeHtml(id)}" placeholder="LAYER" list="layerDocIds" /><input data-layer-doc-index="${index}" data-key="ref" value="${escapeHtml(ref)}" placeholder="knowledge_ref" /><button class="row-remove" data-remove-layer-doc="${escapeHtml(id)}" type="button">x</button></div>`).join("") : `<div class="empty-row">${usesLayers ? "还没有 Layer 映射；点上方 chip 快速添加，或 Add row 手填" : "No layer-specific overrides"}</div>`}</div>
      <div><button class="button secondary" id="addLayerDoc" type="button">Add row</button></div>
    </div>
  </div></section>`;
}

function renderPolicy() {
  return `<section class="surface"><div class="surface-head"><div><h3>Capability Selection</h3><p>Selector 仍会输出 selected / skipped reasons，并只补齐最小充分能力集合。</p></div><span class="status good">framework-owned</span></div><div class="surface-body form-grid three">
    ${input("capability_selection.lane_profiles.fast.max_optional_skills", "Fast optional budget", { valueType: "nullable-number" })}
    ${input("capability_selection.lane_profiles.lite.max_optional_skills", "Lite optional budget", { valueType: "nullable-number" })}
    ${input("capability_selection.lane_profiles.complex.max_optional_skills", "Complex optional budget", { valueType: "nullable-number", placeholder: "null" })}
    ${input("capability_selection.d3a_profile.max_optional_skills", "D3A optional budget", { valueType: "nullable-number", placeholder: "null" })}
  </div></section>
  <section class="surface"><div class="surface-head"><div><h3>Self Optimization</h3><p>observe 只记录；propose_only 只产出候选 overlay。人工对齐与禁止自动修改 Core 是固定约束。</p></div></div><div class="surface-body form-grid">
    ${input("self_optimization.mode", "Mode", { type: "select", options: ["disabled", "observe", "propose_only"] })}
    ${input("self_optimization.event_store_ref", "Event Store Ref", { valueType: "nullable" })}
    ${input("self_optimization.replay_cases_ref", "Replay Cases Ref", { valueType: "nullable" })}
    ${input("self_optimization.team_overlay_ref", "Team Overlay Ref", { valueType: "nullable" })}
    <div class="field full"><small>Locked: promotion_requires_human_alignment = true; auto_modify_core = false</small></div>
  </div></section>`;
}

function renderOverview() {
  const selected = get("domain.mode", "general");
  const alignmentSteps = get("alignment.orchestration.steps", []);
  const boundCount = availableSkillIds().length;
  return `<section class="strategy-summary">
    <div><span class="eyebrow">ACTIVE DOMAIN</span><strong>${escapeHtml(domainTitle(selected))}</strong><small>${selected === "d3a" ? "fixed workflow" : selected === "custom" ? get("domain.custom.lane_policy.mode", "dynamic") : "dynamic lanes"}</small></div>
    <div><span class="eyebrow">ALIGNMENT</span><strong>${alignmentSteps.length} steps</strong><small>ordered pipeline</small></div>
    <div><span class="eyebrow">CAPABILITIES</span><strong>${boundCount} bound</strong><small>core + extensions</small></div>
    <div><span class="eyebrow">OUTPUT</span><strong>${validateConfig().checks.every((check) => check.ok) ? "Resolver ready" : "Needs attention"}</strong><small>team-config.yaml</small></div>
  </section>
  <section class="surface strategy-surface">
    <div class="surface-head"><div><h3>Compiled Harness Strategy</h3><p>这张图来自当前配置，不是另一份配置。修改任意步骤后会同步更新。</p></div><span class="status ${validateConfig().checks.every((check) => check.ok) ? "good" : "bad"}">${validateConfig().checks.every((check) => check.ok) ? "READY" : "INVALID"}</span></div>
    <div class="strategy-board">
      <div class="strategy-stage-label">01 PRE-ALIGNMENT</div>
      <div class="strategy-flow alignment-overview">
        <div class="strategy-node source"><strong>User Intent</strong><span>raw idea / TR3 / task</span></div>
        ${alignmentSteps.map((step) => `<div class="strategy-connector">-&gt;</div><div class="strategy-node alignment ${step.stage === "alignment_check" ? "gate" : ""}"><strong>${escapeHtml(step.skill_ids.join(" + "))}</strong><span>${step.trigger_signals.length ? escapeHtml(step.trigger_signals.join(" / ")) : "always"}</span></div>`).join("")}
      </div>
      <div class="strategy-down">|<br>v</div>
      <div class="strategy-stage-label">02 DOMAIN ROUTING</div>
      <div class="domain-overview-grid">
        <div class="strategy-node router active-route"><strong>Domain Router</strong><span>selected: ${escapeHtml(selected)}</span></div>
        ${domainOverviewBranch("general", selected)}
        ${domainOverviewBranch("d3a", selected)}
        ${domainOverviewBranch("custom", selected)}
      </div>
      <div class="strategy-down">|<br>v</div>
      <div class="strategy-stage-label">03 COMPLETION</div>
      <div class="completion-overview">
        <div class="strategy-node gate"><strong>${selected === "d3a" ? "DT GREEN + tran_build PASS" : selected === "custom" ? "Custom Completion Skill" : "Lane Evidence Gate"}</strong><span>tool evidence only</span></div>
        <div class="strategy-connector">-&gt;</div>
        <div class="strategy-node output"><strong>DONE</strong><span>completion_verification_result</span></div>
      </div>
    </div>
  </section>`;
}

function domainOverviewBranch(domain, selected) {
  const active = domain === selected;
  if (domain === "d3a") {
    return `<div class="domain-overview-branch ${active ? "active" : ""}"><div class="branch-head"><strong>D3A</strong><span>Lane N/A</span></div><div class="mini-flow">${["dt_design", "dt_writer", "dt_build", "tran_build"].map((skill) => `<span class="mini-step ${get(`bindings.${skill}.skill_ref`) ? "bound" : ""}">${skill}</span>`).join(`<i>-&gt;</i>`)}</div></div>`;
  }
  if (domain === "custom") {
    const policy = get("domain.custom.lane_policy.mode", "dynamic");
    return `<div class="domain-overview-branch ${active ? "active" : ""}"><div class="branch-head"><strong>${escapeHtml(get("domain.custom.id") || "Custom")}</strong><span>${policy}</span></div><div class="mini-flow"><span class="mini-step ${get("domain.custom.planner_skill_ref") ? "bound" : ""}">planner</span><i>-&gt;</i>${policy !== "not_applicable" ? `<span class="mini-step bound">${policy === "fixed" ? get("domain.custom.lane_policy.selected_lane", "lite") : "lane"}</span><i>-&gt;</i>` : ""}<span class="mini-step ${get("domain.custom.workflow_skill_ref") ? "bound" : ""}">workflow</span><i>-&gt;</i><span class="mini-step ${get("domain.custom.completion_skill_ref") ? "bound" : ""}">completion</span></div></div>`;
  }
  return `<div class="domain-overview-branch ${active ? "active" : ""}"><div class="branch-head"><strong>General</strong><span>dynamic Lane</span></div><div class="lane-mini-grid">${["fast", "lite", "complex"].map((lane) => `<div><b>${lane}</b>${overviewLaneSteps(lane)}</div>`).join("")}</div></div>`;
}

function overviewLaneSteps(lane) {
  const steps = get(`lane.profiles.${lane}.orchestration.steps`, []);
  if (!steps.length) return `<span>autonomous</span>`;
  return steps.map((step) => `<span>${escapeHtml(step.id)}</span>`).join("");
}

function availableSkillIds() {
  const bound = Object.entries(get("bindings", {})).filter(([, value]) => value && value.skill_ref).map(([key]) => key);
  const extensions = get("adapter_extensions", []).map((entry) => entry.id).filter(Boolean);
  return [...new Set([...bound, ...extensions])].sort();
}

function extensionsToText() {
  return get("adapter_extensions", []).map((entry) => [entry.id, (entry.capability_keys || []).join(","), (entry.allowed_stages || []).join(","), entry.skill_ref || "", entry.execution_role || "atomic_capability"].join(" | ")).join("\n");
}

function textToExtensions(text) {
  return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => {
    const parts = line.split("|").map((part) => part.trim());
    return {
      id: parts[0], execution_role: parts[4] || "atomic_capability",
      capability_keys: csv(parts[1]), allowed_stages: csv(parts[2]), eligible_lanes: ["fast", "lite", "complex"],
      execution_profiles: [], trigger_signals: [], skill_ref: parts[3] || null,
      input_contract_ref: null, output_contract_ref: null, evidence_required: true,
      requires: [], blocks_when: [], composes_with: [], supersedes: []
    };
  });
}

function csv(value) { return value ? value.split(/[,，]/).map((item) => item.trim()).filter(Boolean) : []; }

function commit(options = {}) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  const save = document.getElementById("saveStatus");
  if (save) save.textContent = "草稿已保存";
  if (options.fullRender) render();
  else renderYamlAndValidation();
}

function loadDraft() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch (_) { return null; }
}

function renderYamlAndValidation() {
  if (activeSection === "skills") {
    const editor = document.querySelector('[data-bind="_extensions_editor"]');
    if (editor && !editor.dataset.loaded) { editor.value = extensionsToText(); editor.dataset.loaded = "true"; }
  }
  const yaml = buildYaml(state);
  yamlOutput.textContent = yaml;
  const result = validateConfig();
  const errors = result.checks.filter((check) => !check.ok);
  document.getElementById("validationBadge").textContent = errors.length ? `${errors.length} Issues` : "Ready";
  document.getElementById("validationBadge").className = `status ${errors.length ? "bad" : "good"}`;
  document.getElementById("checkCount").textContent = `${result.checks.length} checks`;
  document.getElementById("validationList").innerHTML = result.checks.map((check) => `<div class="validation-item ${check.ok ? "good" : "bad"}">${escapeHtml(check.message)}</div>`).join("");
}

function validateConfig() {
  const checks = [];
  const sectionErrors = {};
  const add = (ok, message, section) => { checks.push({ ok, message, section }); if (!ok) sectionErrors[section] = true; };
  add(get("config_version") === 1, "config_version 必须为 1", "setup");
  add(Boolean(get("team.id")), "team.id 已填写", "setup");
  add(Boolean(get("team.repo_path")), "team.repo_path 已填写", "setup");
  const mode = get("domain.mode");
  add(["general", "d3a", "custom"].includes(mode), "Domain mode 合法", "setup");
  if (mode === "custom") {
    add(Boolean(get("domain.custom.id")), "Custom Domain 有唯一 ID", "setup");
    add(get("domain.custom.trigger_rules", []).length > 0, "Custom Domain 至少有一个 trigger rule", "setup");
    ["workflow_skill_ref", "planner_skill_ref", "completion_skill_ref"].forEach((key) => add(Boolean(get(`domain.custom.${key}`)), `Custom Domain ${key} 已绑定`, "setup"));
    add(get("domain.custom.coding_layers", []).length > 0, "Custom Domain 至少有一个 coding layer", "setup");
    add(get("domain.custom.test_domains", []).length > 0, "Custom Domain 至少有一个 test domain", "setup");
    const policy = get("domain.custom.lane_policy");
    add(policy.mode !== "fixed" || ["fast", "lite", "complex"].includes(policy.selected_lane), "Fixed Lane 已选择", "setup");
  }
  const steps = get("alignment.orchestration.steps", []);
  const stages = steps.map((step) => step.stage);
  ["discovery", "divergence", "clarification", "alignment_check"].forEach((stage) => add(stages.includes(stage), `Alignment 保留 ${stage} 阶段`, "alignment"));
  const signals = steps.flatMap((step) => step.trigger_signals || []);
  ["raw_idea", "critical_gaps_remain"].forEach((signal) => add(signals.includes(signal), `Alignment 覆盖 ${signal} 信号`, "alignment"));
  const clarificationSignals = steps.filter((step) => step.stage === "clarification").flatMap((step) => step.trigger_signals || []);
  ["structured_requirement_input", "tr3_input"].forEach((signal) => add(clarificationSignals.includes(signal), `Clarification 覆盖强制信号 ${signal}`, "alignment"));
  steps.forEach((step) => add((step.skill_ids || []).every((id) => get(`alignment.bindings.${id}.skill_ref`)), `${step.id} 的 Skill 已绑定`, "alignment"));
  const availableSkillPool = availableSkillIds();
  ["fast", "lite", "complex"].forEach((lane) => {
    const profile = get(`lane.profiles.${lane}`);
    const allow = profile.skills.allow || [];
    const required = profile.skills.required || [];
    const deny = profile.skills.deny || [];
    add(!required.some((id) => deny.includes(id)), `${lane}: required 与 deny 不冲突`, "lanes");
    add(!allow.length || required.every((id) => allow.includes(id)), `${lane}: required 包含在 allow 中`, "lanes");
    add(profile.orchestration.mode !== "ordered" || (profile.orchestration.steps || []).length > 0, `${lane}: ordered 模式包含 steps`, "lanes");
    const referenced = [...new Set([...allow, ...deny, ...required, ...(profile.orchestration.steps || []).flatMap((step) => step.skill_ids || [])])];
    add(referenced.every((id) => availableSkillPool.includes(id)), `${lane}: allow/required/deny/steps 只引用已绑定的 Skill`, "lanes");
  });
  get("adapter_extensions", []).forEach((entry) => {
    add(Boolean(entry.id && entry.id.startsWith("idc-")), `Extension ${entry.id || "(missing)"} 使用 idc- 前缀`, "skills");
    add(Boolean(entry.skill_ref), `Extension ${entry.id || "(missing)"} 已绑定 Skill`, "skills");
  });
  const optimization = get("self_optimization");
  add(optimization.auto_modify_core === false, "禁止自动修改 IDC Core", "policy");
  add(optimization.promotion_requires_human_alignment === true, "优化提升必须经过 Human Alignment", "policy");
  const enabledList = enabledModes();
  add(enabledList.length > 0, "domain.enabled 至少包含一个域", "setup");
  add(enabledList.every((id) => ["d3a", "general", "custom"].includes(id)), "domain.enabled 只含 d3a / general / custom", "setup");
  add(new Set(enabledList).size === enabledList.length, "domain.enabled 无重复", "setup");
  add(enabledList.includes(get("domain.mode", "general")), "domain.mode 包含在 domain.enabled 中", "setup");
  return { checks, sectionErrors };
}

function buildYaml(config) {
  const lines = ["config_version: 1", "team:", `  id: ${yamlScalar(config.team.id)}`, `  repo_path: ${yamlScalar(config.team.repo_path)}`, "domain:"];
  /* enabled 只在显式多选时输出；缺省时 resolver 默认 [mode]，导入旧配置不受污染 */
  if (Array.isArray(config.domain.enabled) && config.domain.enabled.length) lines.push(`  enabled: ${flow(config.domain.enabled)}`);
  lines.push(`  mode: ${config.domain.mode}`, "  d3a:");
  pushRegistry(lines, "    dt_domains", config.domain.d3a.dt_domains, 4);
  const d3aOrchestration = config.domain.d3a.orchestration || { mode: "framework_default", steps: [] };
  lines.push("    orchestration:", `      mode: ${d3aOrchestration.mode}`);
  pushSteps(lines, "      steps", d3aOrchestration.steps, 6);
  lines.push("  custom:", `    id: ${yamlScalar(config.domain.custom.id)}`, `    trigger_rules: ${flow(config.domain.custom.trigger_rules)}`, "    lane_policy:", `      mode: ${config.domain.custom.lane_policy.mode}`, `      selected_lane: ${yamlScalar(config.domain.custom.lane_policy.selected_lane)}`);
  pushRegistry(lines, "    coding_layers", config.domain.custom.coding_layers, 4);
  pushRegistry(lines, "    test_domains", config.domain.custom.test_domains, 4);
  lines.push(`    required_contracts: ${flow(config.domain.custom.required_contracts)}`, `    workflow_skill_ref: ${yamlScalar(config.domain.custom.workflow_skill_ref)}`, `    planner_skill_ref: ${yamlScalar(config.domain.custom.planner_skill_ref)}`, `    completion_skill_ref: ${yamlScalar(config.domain.custom.completion_skill_ref)}`, "    orchestration:", `      mode: ${(config.domain.custom.orchestration || {}).mode || "workflow_skill"}`);
  pushSteps(lines, "      steps", (config.domain.custom.orchestration || {}).steps || [], 6);
  lines.push("general:");
  pushRegistry(lines, "  components", config.general.components, 2);
  pushRegistry(lines, "  test_domains", config.general.test_domains, 2);
  lines.push("bindings:");
  Object.keys(config.bindings).forEach((key) => lines.push(`  ${key}: {skill_ref: ${yamlScalar(config.bindings[key] && config.bindings[key].skill_ref)}}`));
  if (!config.adapter_extensions.length) lines.push("adapter_extensions: []");
  else {
    lines.push("adapter_extensions:");
    config.adapter_extensions.forEach((entry) => {
      lines.push(`  - id: ${yamlScalar(entry.id)}`, `    execution_role: ${entry.execution_role || "atomic_capability"}`, `    capability_keys: ${flow(entry.capability_keys)}`, `    allowed_stages: ${flow(entry.allowed_stages)}`, `    eligible_lanes: ${flow(entry.eligible_lanes)}`, `    execution_profiles: ${flow(entry.execution_profiles)}`, `    trigger_signals: ${flow(entry.trigger_signals)}`, `    skill_ref: ${yamlScalar(entry.skill_ref)}`, `    input_contract_ref: ${yamlScalar(entry.input_contract_ref)}`, `    output_contract_ref: ${yamlScalar(entry.output_contract_ref)}`, `    evidence_required: ${entry.evidence_required !== false}`, `    requires: ${flow(entry.requires)}`, `    blocks_when: ${flow(entry.blocks_when)}`, `    composes_with: ${flow(entry.composes_with)}`, `    supersedes: ${flow(entry.supersedes)}`);
    });
  }
  const knowledge = config.knowledge;
  lines.push("knowledge:", `  architecture_doc_ref: ${yamlScalar(knowledge.architecture_doc_ref)}`, `  feature_docs_root_ref: ${yamlScalar(knowledge.feature_docs_root_ref)}`);
  const docs = Object.entries(knowledge.layer_docs || {});
  if (!docs.length) lines.push("  layer_docs: {}");
  else { lines.push("  layer_docs:"); docs.forEach(([key, value]) => lines.push(`    ${key}: ${yamlScalar(value)}`)); }
  lines.push("  lane_docs:");
  ["fast", "lite", "complex"].forEach((lane) => lines.push(`    ${lane}: ${flow((knowledge.lane_docs || {})[lane] || [])}`));
  lines.push(`  verification_mapping_ref: ${yamlScalar(knowledge.verification_mapping_ref)}`, "  repo_context:", `    provider_skill_ref: ${yamlScalar(knowledge.repo_context.provider_skill_ref)}`, `    policy_ref: ${yamlScalar(knowledge.repo_context.policy_ref)}`, `    fallback: ${knowledge.repo_context.fallback || "bounded_grep"}`, "lane:", `  default: ${config.lane.default}`, "  profiles:");
  ["fast", "lite", "complex"].forEach((lane) => {
    const profile = config.lane.profiles[lane];
    lines.push(`    ${lane}:`, "      skills:", `        allow: ${flow(profile.skills.allow)}`, `        deny: ${flow(profile.skills.deny)}`, `        required: ${flow(profile.skills.required)}`, "      orchestration:", `        mode: ${profile.orchestration.mode}`);
    pushSteps(lines, "        steps", profile.orchestration.steps, 8);
  });
  lines.push("capability_selection:", "  mode: autonomous_minimal_sufficient", "  lane_profiles:");
  ["fast", "lite", "complex"].forEach((lane) => lines.push(`    ${lane}: {max_optional_skills: ${yamlScalar(config.capability_selection.lane_profiles[lane].max_optional_skills)}}`));
  lines.push(`  d3a_profile: {max_optional_skills: ${yamlScalar(config.capability_selection.d3a_profile.max_optional_skills)}}`, "  require_selected_and_skipped_reasons: true", "self_optimization:", `  mode: ${config.self_optimization.mode}`, `  event_store_ref: ${yamlScalar(config.self_optimization.event_store_ref)}`, `  replay_cases_ref: ${yamlScalar(config.self_optimization.replay_cases_ref)}`, `  team_overlay_ref: ${yamlScalar(config.self_optimization.team_overlay_ref)}`, "  promotion_requires_human_alignment: true", "  auto_modify_core: false", "alignment:", "  bindings:");
  Object.entries(config.alignment.bindings).forEach(([key, binding]) => lines.push(`    ${key}: {skill_ref: ${yamlScalar(binding.skill_ref)}}`));
  lines.push("  orchestration:", "    mode: ordered");
  pushSteps(lines, "    steps", config.alignment.orchestration.steps, 4);
  return `${lines.join("\n")}\n`;
}

function pushRegistry(lines, key, rows, indent) {
  if (!rows || !rows.length) { lines.push(`${key}: []`); return; }
  lines.push(`${key}:`);
  const pad = " ".repeat(indent + 2);
  rows.forEach((row) => lines.push(`${pad}- id: ${yamlScalar(row.id)}`, `${pad}  knowledge_ref: ${yamlScalar(row.knowledge_ref)}`));
}

function pushSteps(lines, key, steps, indent) {
  if (!steps || !steps.length) { lines.push(`${key}: []`); return; }
  lines.push(`${key}:`);
  const pad = " ".repeat(indent + 2);
  steps.forEach((step) => lines.push(`${pad}- id: ${yamlScalar(step.id)}`, `${pad}  stage: ${yamlScalar(step.stage)}`, `${pad}  skill_ids: ${flow(step.skill_ids)}`, `${pad}  trigger_signals: ${flow(step.trigger_signals)}`));
}

function yamlScalar(value) {
  if (value === null || value === undefined || value === "") return "null";
  if (typeof value === "boolean" || typeof value === "number") return String(value);
  const text = String(value);
  if (/^[A-Za-z0-9_./:-]+$/.test(text) && !["null", "true", "false"].includes(text)) return text;
  return JSON.stringify(text);
}

function flow(values) { return `[${(values || []).map(yamlScalar).join(", ")}]`; }

// Small YAML subset parser for this repository's mapping/list/flow-style config.
function parseYaml(source) {
  const lines = source.split(/\r?\n/).map((raw) => ({ indent: raw.match(/^ */)[0].length, text: stripComment(raw.trim()) })).filter((line) => line.text);
  function block(start, indent) {
    const isArray = lines[start] && lines[start].indent === indent && lines[start].text.startsWith("- ");
    const result = isArray ? [] : {};
    let index = start;
    while (index < lines.length && lines[index].indent === indent && lines[index].text.startsWith("- ") === isArray) {
      const text = isArray ? lines[index].text.slice(2).trim() : lines[index].text;
      if (isArray) {
        if (text.includes(":")) {
          const item = {};
          const [key, rest] = splitKey(text);
          item[key] = rest ? parseScalar(rest) : null;
          index += 1;
          if (index < lines.length && lines[index].indent > indent) {
            const [extra, next] = block(index, lines[index].indent);
            Object.assign(item, extra);
            index = next;
          }
          result.push(item);
        } else { result.push(parseScalar(text)); index += 1; }
      } else {
        const [key, rest] = splitKey(text);
        index += 1;
        if (rest) result[key] = parseScalar(rest);
        else if (index < lines.length && lines[index].indent > indent) {
          const [child, next] = block(index, lines[index].indent);
          result[key] = child; index = next;
        } else result[key] = {};
      }
    }
    return [result, index];
  }
  return lines.length ? block(0, lines[0].indent)[0] : {};
}

function stripComment(text) {
  let quote = null;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if ((char === "\"" || char === "'") && text[i - 1] !== "\\") quote = quote === char ? null : quote || char;
    if (char === "#" && !quote && (i === 0 || /\s/.test(text[i - 1]))) return text.slice(0, i).trim();
  }
  return text;
}

function splitKey(text) {
  let depth = 0; let quote = null;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if ((char === "\"" || char === "'") && text[i - 1] !== "\\") quote = quote === char ? null : quote || char;
    if (!quote && "[{".includes(char)) depth += 1;
    if (!quote && "]}".includes(char)) depth -= 1;
    if (char === ":" && !quote && depth === 0) return [text.slice(0, i).trim(), text.slice(i + 1).trim()];
  }
  throw new Error(`无法解析 YAML 行: ${text}`);
}

function splitFlow(text) {
  const parts = []; let start = 0; let depth = 0; let quote = null;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if ((char === "\"" || char === "'") && text[i - 1] !== "\\") quote = quote === char ? null : quote || char;
    if (!quote && "[{".includes(char)) depth += 1;
    if (!quote && "]}".includes(char)) depth -= 1;
    if (char === "," && !quote && depth === 0) { parts.push(text.slice(start, i).trim()); start = i + 1; }
  }
  parts.push(text.slice(start).trim());
  return parts.filter(Boolean);
}

function parseScalar(text) {
  if (text === "null" || text === "~") return null;
  if (text === "true") return true;
  if (text === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(text)) return Number(text);
  if ((text.startsWith("\"") && text.endsWith("\"")) || (text.startsWith("'") && text.endsWith("'"))) {
    return text.startsWith("\"") ? JSON.parse(text) : text.slice(1, -1).replace(/''/g, "'");
  }
  if (text.startsWith("[") && text.endsWith("]")) return splitFlow(text.slice(1, -1)).map(parseScalar);
  if (text.startsWith("{") && text.endsWith("}")) {
    const object = {};
    splitFlow(text.slice(1, -1)).forEach((part) => { const [key, rest] = splitKey(part); object[key] = parseScalar(rest); });
    return object;
  }
  return text;
}

function mergeDefaults(base, incoming) {
  if (Array.isArray(incoming)) return clone(incoming);
  if (!incoming || typeof incoming !== "object") return incoming;
  const result = clone(base && typeof base === "object" ? base : {});
  Object.keys(incoming).forEach((key) => { result[key] = mergeDefaults(result[key], incoming[key]); });
  return result;
}

document.addEventListener("click", (event) => {
  const wizardPrev = event.target.closest("[data-wizard-prev]");
  if (wizardPrev && !wizardPrev.disabled) { wizardGo(-1); return; }
  const wizardNext = event.target.closest("[data-wizard-next]");
  if (wizardNext && !wizardNext.disabled) { wizardGo(1); return; }
  const wizardSkipButton = event.target.closest("[data-wizard-skip]");
  if (wizardSkipButton) { wizardSkip(); return; }
  const wizardStart = event.target.closest("[data-wizard-start]");
  if (wizardStart) { wizardJump("setup"); return; }
  const wizardDownload = event.target.closest("[data-wizard-download]");
  if (wizardDownload) { document.getElementById("downloadBtn").click(); return; }
  const importOpen = event.target.closest("[data-import-open]");
  if (importOpen) { document.getElementById("yamlFile").click(); return; }
  const taskPrimary = event.target.closest("[data-task-primary]");
  if (taskPrimary) {
    event.stopPropagation();
    setPrimaryDomain(taskPrimary.dataset.taskPrimary);
    toast(`主路由已切换为 ${taskPrimary.dataset.taskPrimary}`);
    return;
  }
  const taskSelect = event.target.closest("[data-task-select]");
  if (taskSelect) {
    const requested = taskSelect.dataset.taskSelect;
    const turningOn = !enabledModes().includes(requested);
    if (turningOn && requested === "custom") {
      const custom = state.domain.custom;
      if (!custom.id) custom.id = "my-domain";
      if (!custom.trigger_rules.length) custom.trigger_rules = ["my_team_trigger"];
      if (!custom.workflow_skill_ref) custom.workflow_skill_ref = ".claude/skills/idc-gc-sop-adapter/SKILL.md";
      if (!custom.planner_skill_ref) custom.planner_skill_ref = ".claude/skills/idc-gc-sop-adapter/SKILL.md";
      if (!custom.completion_skill_ref) custom.completion_skill_ref = ".claude/skills/idc-gc-sop-adapter/SKILL.md";
    }
    setModeEnabled(requested, turningOn);
    toast(turningOn
      ? `已启用 ${requested === "d3a" ? "D3A 专用域" : requested === "custom" ? "自定义 Domain" : "通用开发"}（enabled: ${enabledModes().join(" + ")}）`
      : `已停用 ${requested}（enabled: ${enabledModes().join(" + ")}）`);
    return;
  }
  const addBinding = event.target.closest("[data-add-binding]");
  if (addBinding) {
    const field = document.getElementById("newBindingKey");
    const key = (field && field.value || "").trim();
    if (!/^[a-z][a-z0-9_]*$/.test(key)) { toast("capability key 需为小写字母/数字/下划线，且以字母开头"); return; }
    if (state.bindings[key]) { toast(`capability ${key} 已存在`); return; }
    state.bindings[key] = { skill_ref: null };
    delete wizard.skipped.skills; wizard.visited.skills = true; saveWizard();
    commit({ fullRender: true });
    toast(`已添加 capability ${key}，填入 skill_ref 后即可被 Lane 引用`);
    return;
  }
  const removeBinding = event.target.closest("[data-remove-binding]");
  if (removeBinding) {
    const key = removeBinding.dataset.removeBinding;
    if (referencedBindingKeys().has(key)) { toast(`${key} 仍被 Lane 引用，先解除引用再删除`); return; }
    delete state.bindings[key];
    commit({ fullRender: true });
    toast(`已删除 capability ${key}`);
    return;
  }
  const addLayerDoc = event.target.closest("[data-add-layer-doc]");
  if (addLayerDoc) {
    state.knowledge.layer_docs[addLayerDoc.dataset.addLayerDoc] = "";
    delete wizard.skipped.knowledge; wizard.visited.knowledge = true; saveWizard();
    commit({ fullRender: true });
    return;
  }
  const alignPreset = event.target.closest("[data-align-preset]");
  if (alignPreset) { applyAlignmentPreset(state, alignPreset.dataset.alignPreset); delete wizard.skipped.alignment; commit({ fullRender: true }); toast(`已应用对齐策略：${ALIGNMENT_PRESETS[alignPreset.dataset.alignPreset].label}`); return; }
  const signalPreview = event.target.closest("[data-signal-preview]");
  if (signalPreview) { previewSignal = previewSignal === signalPreview.dataset.signalPreview ? null : signalPreview.dataset.signalPreview; render(); return; }
  if (event.target.closest("[data-signal-preview-clear]")) { previewSignal = null; render(); return; }
  const sectionButton = event.target.closest("[data-section]");
  if (sectionButton) { activeSection = sectionButton.dataset.section; render(); return; }
  const jumpButton = event.target.closest("[data-jump-section]");
  if (jumpButton) { activeSection = jumpButton.dataset.jumpSection; render(); return; }
  const domainButton = event.target.closest("[data-domain]");
  if (domainButton) { domainEditor = domainButton.dataset.domain; setPrimaryDomain(domainButton.dataset.domain); return; }
  const domainEditorButton = event.target.closest("[data-domain-editor]");
  if (domainEditorButton) { domainEditor = domainEditorButton.dataset.domainEditor; render(); return; }
  const activateDomain = event.target.closest("[data-activate-domain]");
  if (activateDomain) { setPrimaryDomain(activateDomain.dataset.activateDomain); toast(`主路由已切换为 ${activateDomain.dataset.activateDomain}`); return; }
  const segment = event.target.closest("[data-segment] button");
  if (segment) { set(segment.parentElement.dataset.segment, segment.dataset.value); render(); return; }
  const addRegistry = event.target.closest("[data-add-registry]");
  if (addRegistry) { const rows = get(addRegistry.dataset.addRegistry, []); rows.push({ id: "", knowledge_ref: "" }); commit({ fullRender: true }); return; }
  const removeRegistry = event.target.closest("[data-remove-registry]");
  if (removeRegistry) { get(removeRegistry.dataset.removeRegistry, []).splice(Number(removeRegistry.dataset.index), 1); commit({ fullRender: true }); return; }
  const removeLayer = event.target.closest("[data-remove-layer-doc]");
  if (removeLayer) { delete state.knowledge.layer_docs[removeLayer.dataset.removeLayer]; commit({ fullRender: true }); return; }
  const removeAlignment = event.target.closest("[data-remove-alignment]");
  if (removeAlignment) { state.alignment.orchestration.steps.splice(Number(removeAlignment.dataset.removeAlignment), 1); commit({ fullRender: true }); return; }
  const addLaneStep = event.target.closest("[data-add-lane-step]");
  if (addLaneStep) {
    const lane = addLaneStep.dataset.addLaneStep; const steps = state.lane.profiles[lane].orchestration.steps;
    steps.push({ id: `${lane}-step-${steps.length + 1}`, stage: "implementation", skill_ids: [], trigger_signals: [] });
    commit({ fullRender: true }); return;
  }
  const removeLaneStep = event.target.closest("[data-remove-lane-step]");
  if (removeLaneStep) { state.lane.profiles[removeLaneStep.dataset.removeLaneStep].orchestration.steps.splice(Number(removeLaneStep.dataset.index), 1); commit({ fullRender: true }); return; }
  if (event.target.id === "addLayerDoc") { state.knowledge.layer_docs[`LAYER_${Object.keys(state.knowledge.layer_docs).length + 1}`] = ""; commit({ fullRender: true }); }
});

document.addEventListener("input", (event) => {
  const target = event.target;
  if (wizard.skipped[activeSection] && (target.dataset.bind || target.dataset.alignField || target.dataset.laneStepField || target.dataset.registryPath)) {
    delete wizard.skipped[activeSection]; wizard.visited[activeSection] = true; saveWizard(); renderNav();
  }
  if (target.id === "bindingFilter") { bindingFilter = target.value; render(); return; }
  if (target.dataset.bind === "_extensions_editor") { state.adapter_extensions = textToExtensions(target.value); commit(); return; }
  if (target.dataset.laneStepField) {
    const step = state.lane.profiles[target.dataset.lane].orchestration.steps[Number(target.dataset.index)];
    step[target.dataset.laneStepField] = ["skill_ids", "trigger_signals"].includes(target.dataset.laneStepField) ? csv(target.value) : target.value;
    commit(); return;
  }
  if (target.dataset.bind === "domain.custom.lane_policy.mode") {
    state.domain.custom.lane_policy.mode = target.value;
    state.domain.custom.lane_policy.selected_lane = target.value === "fixed" ? (state.domain.custom.lane_policy.selected_lane || "lite") : null;
    commit({ fullRender: true }); return;
  }
  if (target.dataset.bind) { set(target.dataset.bind, parseInputValue(target)); return; }
  if (target.dataset.registryPath) {
    get(target.dataset.registryPath)[Number(target.dataset.index)][target.dataset.key] = target.value;
    commit(); return;
  }
  if (target.dataset.alignField) {
    const step = get("alignment.orchestration.steps")[Number(target.dataset.index)];
    step[target.dataset.alignField] = target.dataset.alignField === "stage" ? target.value : csv(target.value);
    commit(); return;
  }
  if (target.dataset.layerDocIndex !== undefined) {
    const entries = Object.entries(state.knowledge.layer_docs);
    const index = Number(target.dataset.layerDocIndex);
    if (target.dataset.key === "ref") entries[index][1] = target.value;
    else entries[index][0] = target.value;
    state.knowledge.layer_docs = Object.fromEntries(entries);
    commit();
  }
});

document.addEventListener("change", (event) => {
  if (event.target.dataset.bind) set(event.target.dataset.bind, parseInputValue(event.target));
  if (event.target.dataset.alignField) {
    const step = get("alignment.orchestration.steps")[Number(event.target.dataset.index)];
    step[event.target.dataset.alignField] = event.target.dataset.alignField === "stage" ? event.target.value : [event.target.value];
    commit({ fullRender: true });
  }
  if (event.target.dataset.laneStepField === "stage") {
    state.lane.profiles[event.target.dataset.lane].orchestration.steps[Number(event.target.dataset.index)].stage = event.target.value;
    commit();
  }
});

let draggedAlignmentIndex = null;
let draggedSkill = null;
let draggedLaneStep = null;
let pointerSkillDrag = null;
let pointerFlowDrag = null;

function moveAlignmentStep(sourceIndex, targetIndex) {
  if (sourceIndex === targetIndex) return false;
  const steps = state.alignment.orchestration.steps;
  const [moved] = steps.splice(sourceIndex, 1);
  const adjusted = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
  steps.splice(adjusted, 0, moved);
  commit({ fullRender: true }); return true;
}

function moveLaneStep(sourceLane, sourceIndex, targetLane, targetIndex) {
  if (sourceLane === targetLane && sourceIndex === targetIndex) return false;
  const sourceSteps = state.lane.profiles[sourceLane].orchestration.steps;
  const [moved] = sourceSteps.splice(sourceIndex, 1);
  const adjusted = sourceLane === targetLane && sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
  state.lane.profiles[targetLane].orchestration.steps.splice(adjusted, 0, moved);
  commit({ fullRender: true }); return true;
}

function applySkillDrop(skillDrag, target) {
  const laneStepTarget = target && target.closest("[data-lane-step-lane]");
  if (laneStepTarget) {
    const lane = laneStepTarget.dataset.laneStepLane; const index = Number(laneStepTarget.dataset.laneStepIndex);
    const stepSkills = state.lane.profiles[lane].orchestration.steps[index].skill_ids;
    if (!stepSkills.includes(skillDrag.id)) stepSkills.push(skillDrag.id);
    const allowed = state.lane.profiles[lane].skills.allow;
    if (!allowed.includes(skillDrag.id)) allowed.push(skillDrag.id);
    commit({ fullRender: true }); return true;
  }
  const zone = target && target.closest(".skill-zone[data-lane]");
  if (zone && zone.dataset.lane !== "palette") {
    const targetLane = zone.dataset.lane;
    const targetSkills = get(`lane.profiles.${targetLane}.skills.allow`);
    if (!targetSkills.includes(skillDrag.id)) targetSkills.push(skillDrag.id);
    if (skillDrag.source !== "palette" && skillDrag.source !== targetLane) {
      const sourceSkills = get(`lane.profiles.${skillDrag.source}.skills.allow`);
      const sourceIndex = sourceSkills.indexOf(skillDrag.id);
      if (sourceIndex >= 0) sourceSkills.splice(sourceIndex, 1);
    }
    commit({ fullRender: true }); return true;
  }
  return false;
}

document.addEventListener("mousedown", (event) => {
  const chip = event.target.closest("[data-skill]");
  if (chip) pointerSkillDrag = { id: chip.dataset.skill, source: chip.dataset.sourceLane };
  const handle = event.target.closest(".drag-handle");
  const alignmentCard = handle && handle.closest("[data-align-index]");
  const laneCard = handle && handle.closest("[data-lane-step-lane]");
  if (alignmentCard) pointerFlowDrag = { kind: "alignment", index: Number(alignmentCard.dataset.alignIndex) };
  if (laneCard) pointerFlowDrag = { kind: "lane", lane: laneCard.dataset.laneStepLane, index: Number(laneCard.dataset.laneStepIndex) };
});
document.addEventListener("mouseup", (event) => {
  if (pointerFlowDrag) {
    const flowDrag = pointerFlowDrag; pointerFlowDrag = null;
    const dropTarget = document.elementFromPoint(event.clientX, event.clientY);
    const alignmentTarget = dropTarget && dropTarget.closest("[data-align-index]");
    const laneTarget = dropTarget && dropTarget.closest("[data-lane-step-lane]");
    if (flowDrag.kind === "alignment" && alignmentTarget) moveAlignmentStep(flowDrag.index, Number(alignmentTarget.dataset.alignIndex));
    if (flowDrag.kind === "lane" && laneTarget) moveLaneStep(flowDrag.lane, flowDrag.index, laneTarget.dataset.laneStepLane, Number(laneTarget.dataset.laneStepIndex));
  }
  if (!pointerSkillDrag) return;
  const currentDrag = pointerSkillDrag; pointerSkillDrag = null;
  applySkillDrop(currentDrag, document.elementFromPoint(event.clientX, event.clientY));
});

document.addEventListener("dragstart", (event) => {
  const step = event.target.closest("[data-align-index]");
  if (step) { draggedAlignmentIndex = Number(step.dataset.alignIndex); step.classList.add("dragging"); }
  const chip = event.target.closest("[data-skill]");
  if (chip) draggedSkill = { id: chip.dataset.skill, source: chip.dataset.sourceLane };
  const laneStep = event.target.closest("[data-lane-step-lane]");
  if (laneStep) draggedLaneStep = { lane: laneStep.dataset.laneStepLane, index: Number(laneStep.dataset.laneStepIndex) };
});
document.addEventListener("dragend", (event) => {
  event.target.classList.remove("dragging"); draggedAlignmentIndex = null; draggedSkill = null; draggedLaneStep = null;
  document.querySelectorAll(".skill-zone.over").forEach((zone) => zone.classList.remove("over"));
});
document.addEventListener("dragover", (event) => {
  const step = event.target.closest("[data-align-index]");
  const zone = event.target.closest(".skill-zone[data-lane]");
  const laneStep = event.target.closest("[data-lane-step-lane]");
  if (step || zone || laneStep) { event.preventDefault(); if (zone) zone.classList.add("over"); }
});
document.addEventListener("dragleave", (event) => { const zone = event.target.closest(".skill-zone[data-lane]"); if (zone) zone.classList.remove("over"); });
document.addEventListener("drop", (event) => {
  const step = event.target.closest("[data-align-index]");
  if (step && draggedAlignmentIndex !== null) {
    event.preventDefault(); moveAlignmentStep(draggedAlignmentIndex, Number(step.dataset.alignIndex)); return;
  }
  const laneStepTarget = event.target.closest("[data-lane-step-lane]");
  if (laneStepTarget && draggedSkill) {
    event.preventDefault(); applySkillDrop(draggedSkill, laneStepTarget); return;
  }
  if (laneStepTarget && draggedLaneStep) {
    event.preventDefault(); moveLaneStep(draggedLaneStep.lane, draggedLaneStep.index, laneStepTarget.dataset.laneStepLane, Number(laneStepTarget.dataset.laneStepIndex)); return;
  }
  const zone = event.target.closest(".skill-zone[data-lane]");
  if (zone && draggedSkill) {
    event.preventDefault(); applySkillDrop(draggedSkill, zone);
  }
});
document.addEventListener("dblclick", (event) => {
  const chip = event.target.closest("[data-skill]");
  if (chip && chip.dataset.sourceLane !== "palette") {
    const skills = get(`lane.profiles.${chip.dataset.sourceLane}.skills.allow`);
    const index = skills.indexOf(chip.dataset.skill); if (index >= 0) skills.splice(index, 1);
    commit({ fullRender: true });
  }
});

function applyImportedYaml(text) {
  try {
    state = mergeDefaults(defaultConfig(), parseYaml(text));
    domainEditor = get("domain.mode", "general");
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    // 导入即「已有编排」：直接展示策略总览图，向导标记为已走完
    SECTIONS.forEach((item) => { if (SKIPPABLE_SECTIONS.has(item.id) || item.id === "setup") wizard.visited[item.id] = true; });
    saveWizard();
    activeSection = "overview";
    render();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

document.getElementById("yamlFile").addEventListener("change", (event) => {
  const file = event.target.files[0]; if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const result = applyImportedYaml(reader.result);
    toast(result.ok ? `已导入 ${file.name}，当前编排见策略总览` : `导入失败: ${result.error}`);
  };
  reader.readAsText(file); event.target.value = "";
});

document.getElementById("resetBtn").addEventListener("click", () => { state = defaultConfig(); domainEditor = "general"; wizard = { current: 0, visited: {}, skipped: {} }; saveWizard(); localStorage.removeItem(STORAGE_KEY); activeSection = "welcome"; render(); toast("已恢复初始示例，重新开始向导"); });
document.getElementById("copyBtn").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(yamlOutput.textContent); toast("YAML 已复制"); }
  catch (_) { const range = document.createRange(); range.selectNodeContents(yamlOutput); window.getSelection().removeAllRanges(); window.getSelection().addRange(range); toast("已选中 YAML，可手动复制"); }
});
document.getElementById("downloadBtn").addEventListener("click", () => {
  const blob = new Blob([yamlOutput.textContent], { type: "text/yaml;charset=utf-8" });
  const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
  anchor.href = url; anchor.download = "team-config.yaml"; anchor.click(); URL.revokeObjectURL(url); toast("team-config.yaml 已生成");
});

function toast(message) {
  const element = document.getElementById("toast"); element.textContent = message; element.classList.add("show");
  clearTimeout(toast.timer); toast.timer = setTimeout(() => element.classList.remove("show"), 1800);
}

// 支持 #section 锚点直达（如 index.html#alignment），便于分享与回归截图
if (typeof location !== "undefined") {
  const hashSection = String(location.hash || "").replace("#", "");
  if (SECTIONS.some((item) => item.id === hashSection)) activeSection = hashSection;
}

render();
