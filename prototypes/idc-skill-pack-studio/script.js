let layers = [
  {
    id: "intake",
    name: "Input & Intent",
    summary: "统一输入形态，形成 normalized_request。",
    mode: "core",
    contract: ["raw intent -> normalized_request", "TR3 / 一句话输入适配", "不得写入 completion evidence"],
    implementations: ["IDC Core Intake", "Team Intake Adapter", "<PLACEHOLDER_CUSTOM_INTAKE>"]
  },
  {
    id: "routing",
    name: "Scenario Routing",
    summary: "选择 dynamic / domain / general 路径。",
    mode: "core",
    contract: ["Scenario Router", "Domain Module Router", "Lane Resolver"],
    implementations: ["IDC Core Router", "Team Domain Router", "<PLACEHOLDER_ROUTER>"]
  },
  {
    id: "contract",
    name: "Contract Gate",
    summary: "决定 required contracts 和前置对齐。",
    mode: "core",
    contract: ["API Contract 先于 implementation", "Human Alignment 默认唯一人工对齐点", "scope / completion gate 明确"],
    implementations: ["IDC Contract Gate", "Strict API Contract Gate", "<PLACEHOLDER_CONTRACT_GATE>"]
  },
  {
    id: "domain",
    name: "Domain Module",
    summary: "接入 D3A 或其他团队 domain module。",
    mode: "replaceable",
    contract: ["D3A layer registry 固定", "DT domain 使用 placeholder", "Coding Layer 到 DT Domain 不猜 mapping"],
    implementations: ["D3A Module", "General Coding Module", "<TEAM_DOMAIN_MODULE>"]
  },
  {
    id: "knowledge",
    name: "Knowledge Gate",
    summary: "选择静态知识和动态 repo context。",
    mode: "replaceable",
    contract: ["context bounded", "evidence_ref required", "不得注入企业 secret"],
    implementations: ["IDC Knowledge Gate", "Team Wiki Adapter", "<PLACEHOLDER_CODEGRAPH_ADAPTER>"]
  },
  {
    id: "execution",
    name: "Execution Runtime",
    summary: "编排 agents、skills、handoff 和执行单元。",
    mode: "replaceable",
    contract: ["execution unit <= 500 LOC", "subagent / session handoff 可追踪", "自动闭环直到 gate 或 escalation"],
    implementations: ["Codex Runtime", "Claude Code Runtime", "<PLACEHOLDER_TEAM_RUNTIME>"]
  },
  {
    id: "evidence",
    name: "Evidence & Completion",
    summary: "用工具证据决定 RED/GREEN、DT GREEN、tran_build。",
    mode: "core",
    contract: ["RED evidence 先于 GREEN", "required DT domain GREEN", "tran_build PASS 才能 DONE"],
    implementations: ["IDC Evidence Gate", "Team Build Gate", "<PLACEHOLDER_TRAN_BUILD_GATE>"]
  }
];

const transitionGates = [
  {
    from: "intake",
    to: "routing",
    nameZh: "输入已标准化",
    nameEn: "Normalized Input",
    question: "用户输入是否已经变成 normalized_request？",
    passTo: "进入路由判断",
    failTo: "回到 Input 补齐输入",
    checks: ["normalized_request", "placeholder hygiene"]
  },
  {
    from: "routing",
    to: "contract",
    nameZh: "路由已确定",
    nameEn: "Route Decided",
    question: "是否已选出 Domain 和 Lane？",
    passTo: "进入契约阶段",
    failTo: "回到 Routing 重判",
    checks: ["domain selected", "lane selected"]
  },
  {
    from: "contract",
    to: "domain",
    nameZh: "契约已冻结",
    nameEn: "Contract Frozen",
    question: "API Contract / Scope 是否已确认？",
    passTo: "进入领域模块",
    failTo: "回到 Contract 修改",
    checks: ["API contract", "human alignment"]
  },
  {
    from: "domain",
    to: "knowledge",
    nameZh: "领域计划可执行",
    nameEn: "Domain Plan Ready",
    question: "Layer / DT Domain 规划是否可执行？",
    passTo: "进入知识加载",
    failTo: "回到 Domain 重规划",
    checks: ["layer plan", "DT domain candidates"]
  },
  {
    from: "knowledge",
    to: "execution",
    nameZh: "上下文已就绪",
    nameEn: "Context Ready",
    question: "是否拿到有边界的上下文和 evidence_ref？",
    passTo: "进入执行运行时",
    failTo: "回到 Knowledge 重新加载",
    checks: ["bounded context", "evidence_ref"]
  },
  {
    from: "execution",
    to: "evidence",
    nameZh: "证据已就绪",
    nameEn: "Evidence Ready",
    question: "RED/GREEN 和变更证据是否齐全？",
    passTo: "进入完成判定",
    failTo: "回到 Execution 修复",
    checks: ["RED before GREEN", "changed files"]
  }
];

const domains = [
  {
    id: "d3a",
    name: "D3A Module",
    summary: "固定 TRAN_CFG / DO / VISP_ADP / TFC_TFI / TFE / ADP / DRV，DT domain 使用 TPRINT / FW / DPF placeholder。",
    rules: ["task matches D3A semantics", "requires D3A specification", "coding layer registry cannot drift"],
    requiredGates: ["api_contract", "dt_domain_green", "tran_build"]
  },
  {
    id: "team-domain",
    name: "Custom Team Domain",
    summary: "团队自己的 Domain Module，必须满足 IDC Domain Module Contract。",
    rules: ["registered in domain registry", "owns workflow entrypoint", "declares completion gate"],
    requiredGates: ["domain_contract", "team_verification", "completion_evidence"]
  },
  {
    id: "general",
    name: "General Coding",
    summary: "非 D3A、非团队专属领域的通用 coding fallback。",
    rules: ["no active domain match", "bounded general task", "focused verification is enough"],
    requiredGates: ["task_contract", "focused_verification"]
  }
];

const lanes = [
  {
    id: "fast",
    name: "fast",
    summary: "低风险、范围小、验收明确；最少 contract 和最短闭环。",
    rules: ["clear acceptance", "small change surface", "no API contract change"],
    gates: ["task_summary", "focused_check"],
    orchestration: {
      plan: "inline",
      agent: "same session",
      loop: "x1 quick fix",
      evidence: "focused"
    }
  },
  {
    id: "lite",
    name: "lite",
    summary: "默认开发路径，要求 focused contract 和 GREEN evidence。",
    rules: ["not fast", "no complex hard trigger", "bounded implementation"],
    gates: ["task_contract", "green_evidence", "build_check"],
    orchestration: {
      plan: "task contract",
      agent: "single executor",
      loop: "until GREEN",
      evidence: "GREEN + build"
    }
  },
  {
    id: "complex",
    name: "complex",
    summary: "高风险、跨层、API 或 DT 复杂变化；启用完整 planning 和 evidence gates。",
    rules: ["cross layer impact", "API / behavior semantics change", "shotgun modification risk"],
    gates: ["detailed_plan", "api_contract", "red_evidence", "green_evidence", "tran_build"],
    orchestration: {
      plan: "API + plan",
      agent: "split + handoff",
      loop: "RED → GREEN",
      evidence: "DT + tran_build"
    }
  }
];

const typeMeta = {
  skill: { icon: "SK", label: "Skill", hint: "atomic capability" },
  agent: { icon: "AG", label: "Agent", hint: "executor" },
  gate: { icon: "GT", label: "Gate", hint: "must pass" },
  router: { icon: "RT", label: "Router", hint: "branching rule" },
  lane: { icon: "LN", label: "Lane", hint: "execution strategy" },
  domain: { icon: "DM", label: "Domain", hint: "domain module" },
  knowledge: { icon: "KG", label: "Knowledge", hint: "context gate" },
  runtime: { icon: "RN", label: "Runtime", hint: "execution runtime" },
  handoff: { icon: "HO", label: "Handoff", hint: "state transfer" },
  adapter: { icon: "AD", label: "Adapter", hint: "input adapter" }
};

const initialCapabilities = [
  {
    id: "idc.input-adapter",
    layer: "intake",
    type: "adapter",
    name: "Input Adapter",
    inputs: ["raw_user_intent", "tr3_design_doc", "raw_idea"],
    outputs: ["normalized_request"],
    tools: ["input-parser", "intent-normalizer"],
    evidence: ["normalized-request.yaml"],
    verified: true
  },
  {
    id: "idc.intent-intake",
    layer: "intake",
    type: "skill",
    name: "Intent Intake",
    inputs: ["raw_user_intent"],
    outputs: ["normalized_request"],
    tools: ["placeholder-safe-parser"],
    evidence: ["normalized-request.yaml"],
    verified: true
  },
  {
    id: "idc.intent-discovery",
    layer: "intake",
    type: "skill",
    name: "Intent Discovery",
    inputs: ["raw_idea"],
    outputs: ["draft_spec"],
    tools: ["idc-brainstorming-adapter"],
    evidence: ["draft-spec.md"],
    verified: true
  },
  {
    id: "idc.brainstorming",
    layer: "intake",
    type: "skill",
    name: "Brainstorming",
    inputs: ["raw_idea", "open_questions"],
    outputs: ["candidate_directions", "draft_spec_options"],
    tools: ["divergent-option-generator"],
    evidence: ["brainstorm-options.md"],
    verified: true
  },
  {
    id: "idc.grill-me",
    layer: "intake",
    type: "skill",
    name: "Grill Me",
    inputs: ["draft_spec", "assumptions", "open_questions"],
    outputs: ["challenged_spec", "risk_questions"],
    tools: ["assumption-challenger"],
    evidence: ["challenge-notes.md"],
    verified: true
  },
  {
    id: "team.requirement-clarify",
    layer: "contract",
    type: "skill",
    name: "Requirement Clarify",
    inputs: ["normalized_request"],
    outputs: ["clarified_requirement"],
    tools: ["question-set"],
    evidence: ["alignment-pack.yaml"],
    verified: true
  },
  {
    id: "team.api-contract",
    layer: "contract",
    type: "skill",
    name: "API Contract",
    inputs: ["clarified_requirement"],
    outputs: ["api_contract"],
    tools: ["schema-writer", "contract-checker"],
    evidence: ["api-contract.yaml"],
    laneProfiles: [
      {
        lane: "fast",
        name: "Fast Contract",
        strictness: "light",
        checks: ["task summary", "acceptance clear", "small impact"],
        evidence: ["focused_check"]
      },
      {
        lane: "lite",
        name: "Lite Contract",
        strictness: "standard",
        checks: ["task contract", "scope boundary", "verification plan"],
        evidence: ["green_evidence", "build_check"]
      },
      {
        lane: "complex",
        name: "Complex Contract",
        strictness: "strong",
        checks: ["API contract", "human alignment", "RED evidence first"],
        evidence: ["api_contract", "red_evidence", "completion_gate"]
      }
    ],
    verified: true
  },
  {
    id: "team.domain-router",
    layer: "routing",
    type: "router",
    name: "Domain Router",
    inputs: ["api_contract"],
    outputs: ["dt_domain_decision"],
    tools: ["registry-lookup"],
    evidence: ["domain-lane-decision.yaml"],
    verified: true
  },
  {
    id: "idc.lane-resolver",
    layer: "routing",
    type: "lane",
    name: "Lane Resolver",
    inputs: ["normalized_request", "scenario_signals"],
    outputs: ["fast_lite_complex_lane"],
    tools: ["lane-registry"],
    evidence: ["lane-decision.yaml"],
    verified: true
  },
  {
    id: "idc.domain-module",
    layer: "domain",
    type: "domain",
    name: "Domain Module",
    inputs: ["api_contract", "domain_route", "selected_lane"],
    outputs: ["domain_plan", "required_evidence"],
    tools: ["domain-registry"],
    evidence: ["domain-plan.yaml"],
    verified: true
  },
  {
    id: "team.coding-agent",
    layer: "execution",
    type: "agent",
    name: "Coding Agent",
    inputs: ["api_contract", "layer_context_packet"],
    outputs: ["changed_files", "implementation_notes"],
    tools: ["file_read", "file_edit", "test_runner"],
    evidence: ["changed_files", "green_evidence"],
    verified: true
  },
  {
    id: "idc.execution-runtime",
    layer: "execution",
    type: "runtime",
    name: "Execution Runtime",
    inputs: ["domain_plan", "layer_context_packet"],
    outputs: ["changed_files", "green_evidence"],
    tools: ["agent-orchestrator", "test-runner"],
    evidence: ["execution-report.yaml"],
    verified: true
  },
  {
    id: "team.idc-dt-writer",
    layer: "domain",
    type: "skill",
    name: "DT Writer",
    inputs: ["api_contract", "dt_domain_decision"],
    outputs: ["red_evidence", "dt_cases"],
    tools: ["test_authoring"],
    evidence: ["red_evidence.yaml"],
    verified: true
  },
  {
    id: "idc.knowledge-gate",
    layer: "knowledge",
    type: "skill",
    name: "Knowledge Gate",
    inputs: ["approved_alignment", "selected_layer"],
    outputs: ["layer_context_packet"],
    tools: ["grep", "repo-context-provider"],
    evidence: ["context-packet-summary.yaml"],
    verified: true
  },
  {
    id: "idc.knowledge-module",
    layer: "knowledge",
    type: "knowledge",
    name: "Knowledge Module",
    inputs: ["domain_plan", "approved_alignment"],
    outputs: ["layer_context_packet", "evidence_ref"],
    tools: ["context-bundler"],
    evidence: ["context-packet-summary.yaml"],
    verified: true
  },
  {
    id: "team.wiki-adapter",
    layer: "knowledge",
    type: "skill",
    name: "Team Wiki Adapter",
    inputs: ["domain_question"],
    outputs: ["bounded_reference"],
    tools: ["<PLACEHOLDER_WIKI_SEARCH>"],
    evidence: ["evidence_ref"],
    verified: false
  },
  {
    id: "idc.completion-module",
    layer: "evidence",
    type: "gate",
    name: "Completion Module",
    inputs: ["changed_files", "red_evidence", "green_evidence"],
    outputs: ["completion_decision"],
    tools: ["evidence-checker"],
    evidence: ["completion-summary.yaml"],
    verified: true
  },
  {
    id: "idc.red-green-gate",
    layer: "evidence",
    type: "gate",
    name: "RED / GREEN Gate",
    inputs: ["red_evidence", "green_evidence"],
    outputs: ["dt_green_status"],
    tools: ["test_harness"],
    evidence: ["red_evidence", "green_evidence"],
    verified: true
  },
  {
    id: "idc.evidence-gate",
    layer: "evidence",
    type: "gate",
    name: "Evidence Gate",
    inputs: ["tool_output", "expected_gate"],
    outputs: ["gate_decision"],
    tools: ["test_harness"],
    evidence: ["evidence-summary.yaml"],
    verified: true
  },
  {
    id: "idc.idc-tran-build",
    layer: "evidence",
    type: "gate",
    name: "tran_build PASS",
    inputs: ["dt_green_status"],
    outputs: ["completion_evidence"],
    tools: ["<PLACEHOLDER_TRAN_BUILD_COMMAND>"],
    evidence: ["tran-build-pass.yaml"],
    verified: false
  },
  {
    id: "idc.handoff",
    layer: "execution",
    type: "handoff",
    name: "Session Handoff",
    inputs: ["runtime_state"],
    outputs: ["handoff_packet"],
    tools: ["checkpoint-writer"],
    evidence: ["runtime-state.yaml"],
    verified: true
  }
];

lanes.forEach((lane) => {
  initialCapabilities.push({
    id: `idc.lane.${lane.id}`,
    layer: "routing",
    type: "lane",
    name: `${lane.name} Lane`,
    inputs: ["scenario_signals"],
    outputs: [`${lane.id}_lane_decision`],
    tools: ["lane-registry"],
    evidence: lane.gates,
    verified: true
  });
});

const initialLayers = structuredClone(layers);
const initialDemoState = createDemoState();

let capabilities = [...initialCapabilities];
let nodes = initialDemoState.nodes;
let selectedNodeId = initialDemoState.selectedNodeId;
let moduleAssignments = initialDemoState.moduleAssignments;
let activeFilter = "all";
let activeLayerId = "contract";
let layerSelections = Object.fromEntries(layers.map((layer) => [layer.id, layer.implementations[0]]));
let selectedDomainId = "d3a";
let selectedLaneId = "lite";
let dragState = null;

const NODE_WIDTH = 186;
const NODE_HEIGHT = 86;

const capabilityList = document.getElementById("capabilityList");
const canvas = document.getElementById("canvas");
const edges = document.getElementById("edges");
const canvasHint = document.getElementById("canvasHint");
const architectureBoard = document.getElementById("architectureBoard");
const propertiesEmpty = document.getElementById("propertiesEmpty");
const propertiesForm = document.getElementById("propertiesForm");
const selectedSummary = document.getElementById("selectedSummary");
const selectedType = document.getElementById("selectedType");
const yamlPreview = document.getElementById("yamlPreview");
const gateGrid = document.getElementById("gateGrid");
const validationStatus = document.getElementById("validationStatus");
const toast = document.getElementById("toast");
const layerStack = document.getElementById("layerStack");
const activeLayerLabel = document.getElementById("activeLayerLabel");
const layerTitle = document.getElementById("layerTitle");
const layerDescription = document.getElementById("layerDescription");
const layerMode = document.getElementById("layerMode");
const layerImplementation = document.getElementById("layerImplementation");
const layerContract = document.getElementById("layerContract");
const focusLayerName = document.getElementById("focusLayerName");
const focusLayerSummary = document.getElementById("focusLayerSummary");
const focusCapabilityCount = document.getElementById("focusCapabilityCount");
const focusNodeCount = document.getElementById("focusNodeCount");
const domainSelection = document.getElementById("domainSelection");
const laneSelection = document.getElementById("laneSelection");
const domainRouteName = document.getElementById("domainRouteName");
const domainRouteSummary = document.getElementById("domainRouteSummary");
const laneRouteName = document.getElementById("laneRouteName");
const laneRouteSummary = document.getElementById("laneRouteSummary");
const routeRules = document.getElementById("routeRules");

function nodeFromCapability(capability, x, y) {
  return {
    ...structuredClone(capability),
    nodeId: `${capability.id}-${Math.random().toString(16).slice(2, 7)}`,
    x,
    y,
    required: true,
    newSession: capability.type === "agent"
  };
}

function capabilityById(id) {
  const capability = initialCapabilities.find((item) => item.id === id);
  if (!capability) {
    throw new Error(`Missing demo capability: ${id}`);
  }
  return capability;
}

function createDemoState() {
  const adapter = nodeFromCapability(capabilityById("idc.input-adapter"), 0, 0);
  const intake = nodeFromCapability(capabilityById("idc.intent-intake"), 0, 0);
  const discovery = nodeFromCapability(capabilityById("idc.intent-discovery"), 0, 0);
  const brainstorming = nodeFromCapability(capabilityById("idc.brainstorming"), 0, 0);
  const grillMe = nodeFromCapability(capabilityById("idc.grill-me"), 0, 0);
  const requirement = nodeFromCapability(capabilityById("team.requirement-clarify"), 0, 0);
  const apiContract = nodeFromCapability(capabilityById("team.api-contract"), 0, 0);
  const domainRouter = nodeFromCapability(capabilityById("team.domain-router"), 0, 0);
  const laneResolver = nodeFromCapability(capabilityById("idc.lane-resolver"), 0, 0);
  const fastLane = nodeFromCapability(capabilityById("idc.lane.fast"), 0, 0);
  const liteLane = nodeFromCapability(capabilityById("idc.lane.lite"), 0, 0);
  const complexLane = nodeFromCapability(capabilityById("idc.lane.complex"), 0, 0);
  const domainModule = nodeFromCapability(capabilityById("idc.domain-module"), 0, 0);
  const dtWriter = nodeFromCapability(capabilityById("team.idc-dt-writer"), 0, 0);
  const knowledgeModule = nodeFromCapability(capabilityById("idc.knowledge-module"), 0, 0);
  const knowledgeGate = nodeFromCapability(capabilityById("idc.knowledge-gate"), 0, 0);
  const executionRuntime = nodeFromCapability(capabilityById("idc.execution-runtime"), 0, 0);
  const codingAgent = nodeFromCapability(capabilityById("team.coding-agent"), 0, 0);
  const completionModule = nodeFromCapability(capabilityById("idc.completion-module"), 0, 0);
  const redGreenGate = nodeFromCapability(capabilityById("idc.red-green-gate"), 0, 0);
  const moduleAssignments = {
    [intake.nodeId]: adapter.nodeId,
    [discovery.nodeId]: adapter.nodeId,
    [brainstorming.nodeId]: adapter.nodeId,
    [grillMe.nodeId]: adapter.nodeId,
    [fastLane.nodeId]: laneResolver.nodeId,
    [liteLane.nodeId]: laneResolver.nodeId,
    [complexLane.nodeId]: laneResolver.nodeId,
    [dtWriter.nodeId]: domainModule.nodeId,
    [knowledgeGate.nodeId]: knowledgeModule.nodeId,
    [codingAgent.nodeId]: executionRuntime.nodeId,
    [redGreenGate.nodeId]: completionModule.nodeId
  };

  return {
    nodes: [
      adapter,
      intake,
      discovery,
      brainstorming,
      grillMe,
      domainRouter,
      laneResolver,
      fastLane,
      liteLane,
      complexLane,
      requirement,
      apiContract,
      domainModule,
      dtWriter,
      knowledgeModule,
      knowledgeGate,
      executionRuntime,
      codingAgent,
      completionModule,
      redGreenGate
    ],
    selectedNodeId: adapter.nodeId,
    moduleAssignments
  };
}

function renderAll() {
  renderLayers();
  renderCapabilities();
  renderCanvas();
  renderProperties();
  renderLayerDetail();
  renderValidation();
  renderYaml();
}

function renderArchitectureBoard() {
  architectureBoard.innerHTML = "";

  layers.forEach((layer, index) => {
    const layerCapabilities = capabilities.filter((cap) => cap.layer === layer.id);
    const layerNodes = nodes.filter((node) => node.layer === layer.id);
    const selectedImplementation = layerSelections[layer.id];
    const element = document.createElement("article");
    element.className = `architecture-layer${layer.id === activeLayerId ? " active" : ""}`;
    element.dataset.layerId = layer.id;
    element.innerHTML = `
      <div class="architecture-index">
        <span>L${index + 1}</span>
      </div>
      <div class="architecture-main">
        <div class="architecture-head">
          <div>
            <strong>${layer.name}</strong>
            <p>${layer.summary}</p>
          </div>
          <div class="architecture-actions">
            <span class="status-pill ${layer.mode === "core" ? "good" : "warn"}">${layer.mode}</span>
            <span class="status-pill">${layerNodes.length} selected</span>
          </div>
        </div>
        <div class="architecture-impl">
          <span>Implementation</span>
          <strong>${selectedImplementation}</strong>
        </div>
        <div class="architecture-slots">
          ${layerNodes.length ? layerNodes.map((node) => `
            <button class="slot-chip ${node.type}" data-node-id="${node.nodeId}">
              ${node.name}
              <span>${node.type}</span>
            </button>
          `).join("") : `<div class="empty-slot">Drop ${layerCapabilities.length} available atomic capabilities here</div>`}
        </div>
      </div>
    `;

    element.addEventListener("click", (event) => {
      const slot = event.target.closest(".slot-chip");
      activeLayerId = layer.id;
      if (slot) {
        selectedNodeId = slot.dataset.nodeId;
      }
      renderAll();
    });

    element.addEventListener("dragover", (event) => {
      event.preventDefault();
      element.classList.add("drop-target");
    });

    element.addEventListener("dragleave", () => element.classList.remove("drop-target"));

    element.addEventListener("drop", (event) => {
      event.preventDefault();
      event.stopPropagation();
      element.classList.remove("drop-target");
      const capabilityId = event.dataTransfer.getData("text/plain");
      const capability = capabilities.find((cap) => cap.id === capabilityId);
      if (!capability) return;
      const layerIndex = layers.findIndex((item) => item.id === layer.id);
      const sameLayerCapability = capability.layer === layer.id
        ? capability
        : { ...capability, layer: layer.id, id: `${capability.id}.as-${layer.id}` };
      const node = nodeFromCapability(sameLayerCapability, 70 + (layerIndex % 4) * 230, 80 + layerIndex * 74);
      nodes.push(node);
      activeLayerId = layer.id;
      selectedNodeId = node.nodeId;
      renderAll();
      showToast(`${capability.name} added to ${layer.name}`);
    });

    architectureBoard.appendChild(element);
  });
}

function renderLayers() {
  layerStack.innerHTML = "";
  document.getElementById("layerCount").textContent = `${layers.length} layers`;

  layers.forEach((layer, index) => {
    const layerNodeCount = nodes.filter((node) => node.layer === layer.id).length;
    const element = document.createElement("article");
    element.className = `layer-card${layer.id === activeLayerId ? " active" : ""}`;
    element.innerHTML = `
      <div class="layer-index">L${index + 1}</div>
      <div class="layer-name">
        <strong>${layer.name}</strong>
        <span>${layer.summary}</span>
      </div>
      <span class="status-pill">${layerNodeCount}</span>
    `;
    element.addEventListener("click", () => {
      activeLayerId = layer.id;
      renderAll();
      showToast(`${layer.name}: showing ${capabilities.filter((cap) => cap.layer === layer.id).length} atomic capabilities`);
    });
    layerStack.appendChild(element);
  });
}

function renderCapabilities() {
  const query = document.getElementById("catalogSearch").value.trim().toLowerCase();
  const activeLayer = layers.find((layer) => layer.id === activeLayerId);
  activeLayerLabel.textContent = "Drag any capability into a layer row.";
  capabilityList.innerHTML = "";

  capabilities
    .filter((cap) => activeFilter === "all" || cap.type === activeFilter)
    .filter((cap) => !query || `${cap.name} ${cap.id} ${cap.type}`.toLowerCase().includes(query))
    .forEach((capability) => {
      const card = document.createElement("article");
      card.className = `capability-card ${capability.type}`;
      card.draggable = true;
      card.dataset.capabilityId = capability.id;
      card.innerHTML = capabilityCardMarkup(capability, true);
      card.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", capability.id);
      });
      capabilityList.appendChild(card);
    });
}

function renderLayerDetail() {
  const layer = layers.find((item) => item.id === activeLayerId);
  if (!layer) return;

  layerTitle.textContent = layer.name;
  layerDescription.textContent = layer.summary;
  layerMode.textContent = layer.mode;
  layerMode.className = `status-pill ${layer.mode === "core" ? "good" : "warn"}`;
  layerImplementation.innerHTML = layer.implementations.map((item) => `<option>${item}</option>`).join("");
  layerImplementation.value = layerSelections[layer.id];
  layerContract.innerHTML = layer.contract.map((item) => `
    <div class="contract-item">
      <strong>${item}</strong>
      <span>exported into layer_contracts.${layer.id}</span>
    </div>
  `).join("");
}

function renderRoutingStrategy() {
  const selectedDomain = domains.find((domain) => domain.id === selectedDomainId);
  const selectedLane = lanes.find((lane) => lane.id === selectedLaneId);
  if (!selectedDomain || !selectedLane) return;

  domainSelection.innerHTML = domains.map((domain) => `<option value="${domain.id}">${domain.name}</option>`).join("");
  laneSelection.innerHTML = lanes.map((lane) => `<option value="${lane.id}">${lane.name}</option>`).join("");
  domainSelection.value = selectedDomainId;
  laneSelection.value = selectedLaneId;

  domainRouteName.textContent = selectedDomain.name;
  domainRouteSummary.textContent = selectedDomain.summary;
  laneRouteName.textContent = selectedLane.name;
  laneRouteSummary.textContent = selectedLane.summary;

  routeRules.innerHTML = `
    <div class="route-rule-group">
      <strong>Domain decision rules</strong>
      ${selectedDomain.rules.map((rule) => `<span>${rule}</span>`).join("")}
    </div>
    <div class="route-rule-group">
      <strong>Lane decision rules</strong>
      ${selectedLane.rules.map((rule) => `<span>${rule}</span>`).join("")}
    </div>
    <div class="route-rule-group">
      <strong>Required gates</strong>
      ${[...new Set([...selectedDomain.requiredGates, ...selectedLane.gates])].map((gate) => `<span>${gate}</span>`).join("")}
    </div>
  `;
}

function renderCanvas() {
  canvas.querySelectorAll(".pipeline-board").forEach((node) => node.remove());
  canvasHint.style.display = nodes.length ? "none" : "block";

  const board = document.createElement("div");
  board.className = "pipeline-board";

  layers.forEach((layer, index) => {
    const layerNodes = nodes.filter((node) => node.layer === layer.id);
    const moduleNodes = layerNodes.filter((node) => isModuleType(node.type) && !moduleAssignments[node.nodeId]);
    const looseSkills = layerNodes.filter((node) => node.type === "skill" && !moduleAssignments[node.nodeId]);
    const element = document.createElement("section");
    element.className = `pipeline-column${layer.id === activeLayerId ? " active" : ""}`;
    element.dataset.layerId = layer.id;
    element.draggable = true;
    element.innerHTML = `
      <div class="pipeline-head">
        <span title="Drag column to reorder">L${index + 1}</span>
        <button class="layer-remove" data-layer-id="${layer.id}" title="Remove layer" aria-label="Remove ${layer.name}">×</button>
        <strong>${layer.name}</strong>
        <p>${layer.summary}</p>
        <select class="inline-implementation" data-layer-id="${layer.id}" aria-label="${layer.name} implementation">
          ${layer.implementations.map((item) => `<option value="${item}"${item === layerSelections[layer.id] ? " selected" : ""}>${item}</option>`).join("")}
        </select>
      </div>
      <div class="pipeline-dropzone">
        ${moduleNodes.map((node) => moduleCardMarkup(node)).join("")}
        ${looseSkills.length ? `
          <div class="loose-skill-zone">
            <span>Loose skills</span>
            ${looseSkills.map((node) => skillNodeMarkup(node)).join("")}
          </div>
        ` : ""}
        ${!moduleNodes.length && !looseSkills.length ? `<div class="flow-empty">Drop a module or skill here</div>` : ""}
      </div>
    `;

    element.addEventListener("click", (event) => {
      const actionButton = event.target.closest("[data-action]");
      const removeButton = event.target.closest(".node-remove");
      const layerRemoveButton = event.target.closest(".layer-remove");
      if (actionButton || removeButton || layerRemoveButton || event.target.closest(".inline-implementation")) return;
      const nodeElement = event.target.closest(".flow-node");
      activeLayerId = layer.id;
      if (nodeElement) {
        selectedNodeId = nodeElement.dataset.nodeId;
      }
      renderAll();
    });

    element.querySelectorAll(".flow-node, .module-card, .module-skill-pill, .brainstorm-skill-step").forEach((nodeElement) => {
      nodeElement.addEventListener("dragstart", (event) => {
        event.stopPropagation();
        event.dataTransfer.setData("application/x-idc-node", nodeElement.dataset.nodeId);
        event.dataTransfer.effectAllowed = "move";
        nodeElement.classList.add("dragging");
      });

      nodeElement.addEventListener("dragend", () => {
        nodeElement.classList.remove("dragging");
      });
    });

    element.querySelectorAll(".module-card").forEach((moduleElement) => {
      moduleElement.addEventListener("dragover", (event) => {
        event.preventDefault();
        event.stopPropagation();
        moduleElement.classList.add("module-drop-target");
      });

      moduleElement.addEventListener("dragleave", () => {
        moduleElement.classList.remove("module-drop-target");
      });

      moduleElement.addEventListener("drop", (event) => {
        event.preventDefault();
        event.stopPropagation();
        moduleElement.classList.remove("module-drop-target");
        const draggedNodeId = event.dataTransfer.getData("application/x-idc-node");
        const capabilityId = event.dataTransfer.getData("text/plain");
        if (draggedNodeId) {
          assignNodeToModule(draggedNodeId, moduleElement.dataset.moduleId);
          return;
        }
        if (capabilityId) {
          addCapabilityToModule(capabilityId, moduleElement.dataset.moduleId);
        }
      });
    });

    element.addEventListener("dragstart", (event) => {
      if (event.target.closest(".flow-node") || event.target.closest("select") || event.target.closest("button")) return;
      event.dataTransfer.setData("application/x-idc-layer", layer.id);
      event.dataTransfer.effectAllowed = "move";
      element.classList.add("dragging-layer");
    });

    element.addEventListener("dragend", () => {
      element.classList.remove("dragging-layer");
      document.querySelectorAll(".drop-before, .drop-after").forEach((item) => item.classList.remove("drop-before", "drop-after"));
    });

    element.addEventListener("change", (event) => {
      const implementationSelect = event.target.closest(".inline-implementation");
      if (!implementationSelect) return;
      activeLayerId = implementationSelect.dataset.layerId;
      layerSelections[activeLayerId] = implementationSelect.value;
      renderAll();
      showToast(`${layer.name} implementation updated`);
    });

    element.addEventListener("click", (event) => {
      const actionButton = event.target.closest("[data-action]");
      if (!actionButton) return;
      event.stopPropagation();
      moveLayer(actionButton.dataset.layerId, actionButton.dataset.action);
    });

    element.addEventListener("click", (event) => {
      const removeButton = event.target.closest(".node-remove");
      if (!removeButton) return;
      event.stopPropagation();
      removeNode(removeButton.dataset.nodeId);
    });

    element.addEventListener("click", (event) => {
      const removeLayerButton = event.target.closest(".layer-remove");
      if (!removeLayerButton) return;
      event.stopPropagation();
      removeLayer(removeLayerButton.dataset.layerId);
    });

    element.addEventListener("dragover", (event) => {
      event.preventDefault();
      const draggedLayerId = event.dataTransfer.types.includes("application/x-idc-layer")
        ? event.dataTransfer.getData("application/x-idc-layer")
        : "";
      element.classList.add("drop-target");
      element.classList.toggle("drop-before", Boolean(draggedLayerId) && event.offsetX < element.offsetWidth / 2);
      element.classList.toggle("drop-after", Boolean(draggedLayerId) && event.offsetX >= element.offsetWidth / 2);
    });

    element.addEventListener("dragleave", () => element.classList.remove("drop-target", "drop-before", "drop-after"));

    element.addEventListener("drop", (event) => {
      event.preventDefault();
      event.stopPropagation();
      element.classList.remove("drop-target", "drop-before", "drop-after");
      const draggedLayerId = event.dataTransfer.getData("application/x-idc-layer");
      const draggedNodeId = event.dataTransfer.getData("application/x-idc-node");
      if (draggedLayerId) {
        reorderLayerByDrop(draggedLayerId, layer.id, event.offsetX >= element.offsetWidth / 2);
        return;
      }
      if (draggedNodeId) {
        moveNodeToLayer(draggedNodeId, layer.id);
        return;
      }
      const capabilityId = event.dataTransfer.getData("text/plain");
      const capability = capabilities.find((cap) => cap.id === capabilityId);
      if (!capability) return;
      const sameLayerCapability = capability.layer === layer.id
        ? capability
        : { ...capability, layer: layer.id, id: `${capability.id}.as-${layer.id}` };
      const node = nodeFromCapability(sameLayerCapability, 0, index);
      nodes.push(node);
      activeLayerId = layer.id;
      selectedNodeId = node.nodeId;
      renderAll();
      showToast(`${capability.name} added to ${layer.name}`);
    });

    board.appendChild(element);
    if (index < layers.length - 1) {
      board.appendChild(gateDividerMarkup(layer.id, layers[index + 1].id));
    }
  });

  canvas.appendChild(board);
}

function gateDividerMarkup(fromLayerId, toLayerId) {
  const gate = transitionGates.find((item) => item.from === fromLayerId && item.to === toLayerId) ?? {
    nameZh: "通过门禁",
    nameEn: "Gate",
    question: "是否满足进入下一层的条件？",
    passTo: "进入下一层",
    failTo: "回到上一层修复",
    checks: ["required evidence"]
  };
  const element = document.createElement("aside");
  element.className = "gate-divider";
  element.innerHTML = `
    <div class="gate-line"></div>
    <article class="gate-door">
      <span class="gate-badge">GT</span>
      <strong>${gate.nameZh}</strong>
      <em>${gate.nameEn}</em>
      <p>${gate.question}</p>
      <div>
        ${gate.checks.map((check) => `<span>${check}</span>`).join("")}
      </div>
      <div class="gate-outcomes">
        <small class="pass-path">PASS → ${gate.passTo}</small>
        <small class="fail-path">FAIL ↩ ${gate.failTo}</small>
      </div>
    </article>
    <div class="gate-arrow">PASS →</div>
  `;
  return element;
}

function reorderLayerByDrop(draggedLayerId, targetLayerId, placeAfter) {
  if (draggedLayerId === targetLayerId) return;
  const fromIndex = layers.findIndex((layer) => layer.id === draggedLayerId);
  const targetIndex = layers.findIndex((layer) => layer.id === targetLayerId);
  if (fromIndex < 0 || targetIndex < 0) return;
  const [draggedLayer] = layers.splice(fromIndex, 1);
  const adjustedTargetIndex = layers.findIndex((layer) => layer.id === targetLayerId);
  layers.splice(placeAfter ? adjustedTargetIndex + 1 : adjustedTargetIndex, 0, draggedLayer);
  activeLayerId = draggedLayerId;
  renderAll();
  showToast(`${draggedLayer.name} reordered by drag`);
}

function addLayer() {
  const nextNumber = layers.filter((layer) => layer.id.startsWith("custom-layer")).length + 1;
  const id = `custom-layer-${Date.now().toString(36)}`;
  const layer = {
    id,
    name: `Custom Layer ${nextNumber}`,
    summary: "团队自定义流程阶段，可拖入 module 和 skills。",
    mode: "replaceable",
    contract: ["custom gate required", "evidence must be declared"],
    implementations: ["Custom Layer Adapter", "<PLACEHOLDER_LAYER_IMPL>"]
  };
  layers.push(layer);
  layerSelections[id] = layer.implementations[0];
  activeLayerId = id;
  renderAll();
  showToast(`${layer.name} added`);
}

function removeLayer(layerId) {
  if (layers.length <= 2) {
    showToast("At least two layers are required");
    return;
  }
  const layer = layers.find((item) => item.id === layerId);
  layers = layers.filter((item) => item.id !== layerId);
  const removedNodeIds = nodes.filter((node) => node.layer === layerId).map((node) => node.nodeId);
  nodes = nodes.filter((node) => node.layer !== layerId);
  delete layerSelections[layerId];
  removedNodeIds.forEach((nodeId) => delete moduleAssignments[nodeId]);
  Object.keys(moduleAssignments).forEach((nodeId) => {
    if (removedNodeIds.includes(moduleAssignments[nodeId])) {
      delete moduleAssignments[nodeId];
    }
  });
  activeLayerId = layers[0].id;
  selectedNodeId = nodes[0]?.nodeId ?? null;
  renderAll();
  showToast(`${layer?.name ?? "Layer"} removed`);
}

function moveNodeToLayer(nodeId, targetLayerId) {
  const node = nodes.find((item) => item.nodeId === nodeId);
  const targetLayer = layers.find((layer) => layer.id === targetLayerId);
  if (!node || !targetLayer) return;
  node.layer = targetLayerId;
  delete moduleAssignments[nodeId];
  if (!node.id.endsWith(`.as-${targetLayerId}`) && !capabilities.some((cap) => cap.id === node.id && cap.layer === targetLayerId)) {
    node.id = `${node.id}.as-${targetLayerId}`;
  }
  activeLayerId = targetLayerId;
  selectedNodeId = nodeId;
  renderAll();
  showToast(`${node.name} moved to ${targetLayer.name}`);
}

function assignNodeToModule(nodeId, moduleId) {
  const node = nodes.find((item) => item.nodeId === nodeId);
  const module = nodes.find((item) => item.nodeId === moduleId);
  if (!node || !module || node.nodeId === module.nodeId) return;
  node.layer = module.layer;
  moduleAssignments[nodeId] = moduleId;
  activeLayerId = module.layer;
  selectedNodeId = moduleId;
  renderAll();
  showToast(`${node.name} assigned to ${module.name}`);
}

function addCapabilityToModule(capabilityId, moduleId) {
  const capability = capabilities.find((cap) => cap.id === capabilityId);
  const module = nodes.find((item) => item.nodeId === moduleId);
  if (!capability || !module) return;
  const node = nodeFromCapability(
    capability.layer === module.layer ? capability : { ...capability, layer: module.layer, id: `${capability.id}.as-${module.layer}` },
    0,
    0
  );
  nodes.push(node);
  moduleAssignments[node.nodeId] = moduleId;
  activeLayerId = module.layer;
  selectedNodeId = moduleId;
  renderAll();
  showToast(`${capability.name} added inside ${module.name}`);
}

function isModuleType(type) {
  return ["adapter", "router", "agent", "gate", "lane", "domain", "knowledge", "runtime", "handoff"].includes(type);
}

function skillNodeMarkup(node) {
  if (node.layer === "contract" && node.laneProfiles) {
    return contractProfileNodeMarkup(node);
  }
  return `
    <article class="flow-node ${node.type}${node.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${node.nodeId}" draggable="true">
      ${capabilityCardMarkup(node, false)}
      <button class="node-remove" data-node-id="${node.nodeId}" title="Remove capability" aria-label="Remove ${node.name}">×</button>
    </article>
  `;
}

function contractProfileNodeMarkup(node) {
  return `
    <article class="flow-node contract-profile-node ${node.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${node.nodeId}" draggable="true">
      ${capabilityCardMarkup(node, false)}
      <div class="contract-profile-flow">
        <strong>Lane-aware profiles / 按 Lane 切换 Contract Gate</strong>
        <div class="contract-profile-source">
          <span>from Lane Resolver</span>
          <b>selected_lane</b>
        </div>
        <div class="contract-profile-grid">
          ${node.laneProfiles.map((profile) => contractProfileCardMarkup(profile)).join("")}
        </div>
      </div>
      <button class="node-remove" data-node-id="${node.nodeId}" title="Remove capability" aria-label="Remove ${node.name}">×</button>
    </article>
  `;
}

function contractProfileCardMarkup(profile) {
  return `
    <div class="contract-profile-card ${profile.lane}">
      <span>${profile.name}</span>
      <small>${profile.strictness}</small>
      <div>
        ${profile.checks.slice(0, 3).map((check) => `<em>${check}</em>`).join("")}
      </div>
      <b>${profile.evidence.slice(0, 2).join(" + ")}</b>
    </div>
  `;
}

function moduleCardMarkup(module) {
  const moduleSkills = nodes.filter((node) => moduleAssignments[node.nodeId] === module.nodeId);
  if (module.type === "adapter") {
    return adapterModuleCardMarkup(module, moduleSkills);
  }
  if (module.type === "router" && module.id === "team.domain-router") {
    return domainRouterCardMarkup(module, moduleSkills);
  }
  if (module.type === "lane") {
    return laneModuleCardMarkup(module, moduleSkills);
  }
  if (["domain", "knowledge", "runtime"].includes(module.type) || module.id === "idc.completion-module") {
    return stageModuleCardMarkup(module, moduleSkills);
  }
  return `
    <article class="module-card ${module.type}${module.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${module.nodeId}" data-module-id="${module.nodeId}" draggable="true">
      <div class="module-shell-head">
        ${capabilityCardMarkup(module, false)}
        <button class="node-remove" data-node-id="${module.nodeId}" title="Remove module" aria-label="Remove ${module.name}">×</button>
      </div>
      <div class="module-skill-slot">
        <strong>Uses skills</strong>
        ${moduleSkills.length ? moduleSkills.map((skill) => `
          <div class="module-skill-pill ${skill.type}" data-node-id="${skill.nodeId}" draggable="true">
            <span>${skill.name}</span>
            <small>${moduleSkillRelation(module, skill)}</small>
            <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove skill" aria-label="Remove ${skill.name}">×</button>
          </div>
        `).join("") : `<span class="module-empty">Drop skills into this ${module.type}</span>`}
      </div>
    </article>
  `;
}

function stageModuleCardMarkup(module, moduleSkills) {
  const stage = stageSpec(module);
  return `
    <article class="module-card ${module.type}${module.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${module.nodeId}" data-module-id="${module.nodeId}" draggable="true">
      <div class="module-shell-head">
        ${capabilityCardMarkup(module, false)}
        <button class="node-remove" data-node-id="${module.nodeId}" title="Remove module" aria-label="Remove ${module.name}">×</button>
      </div>
      <div class="stage-flow ${stage.kind}">
        <strong>${stage.title}</strong>
        <div class="stage-step-row">
          ${stage.steps.map((step, index) => `
            <span>${step}</span>
            ${index < stage.steps.length - 1 ? "<i></i>" : ""}
          `).join("")}
        </div>
        <div class="stage-policy-grid">
          ${stage.policies.map((policy) => `<em>${policy}</em>`).join("")}
        </div>
        ${moduleSkills.length ? `
          <div class="module-skill-slot compact">
            <strong>Atomic skills</strong>
            ${moduleSkills.map((skill) => `
              <div class="module-skill-pill ${skill.type}" data-node-id="${skill.nodeId}" draggable="true">
                <span>${skill.name}</span>
                <small>${moduleSkillRelation(module, skill)}</small>
                <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove skill" aria-label="Remove ${skill.name}">×</button>
              </div>
            `).join("")}
          </div>
        ` : `<div class="module-empty">Drop atomic skills into ${module.name}</div>`}
      </div>
    </article>
  `;
}

function stageSpec(module) {
  if (module.type === "domain") {
    return {
      kind: "domain",
      title: "Domain planning / 领域规划",
      steps: ["domain_route", "layer plan", "required evidence"],
      policies: ["D3A uses fixed layer registry", "Custom domain declares own gates", "General keeps bounded scope"]
    };
  }
  if (module.type === "runtime") {
    return {
      kind: "runtime",
      title: "Execution loop / 执行闭环",
      steps: ["plan unit", "agent run", "test feedback"],
      policies: ["lane controls loop depth", "agent/session policy from lane", "handoff when context grows"]
    };
  }
  if (module.type === "knowledge") {
    return {
      kind: "knowledge",
      title: "Context assembly / 上下文装配",
      steps: ["domain needs", "bounded context", "evidence_ref"],
      policies: ["repo context is bounded", "static knowledge is referenced", "no enterprise secrets"]
    };
  }
  return {
    kind: "completion",
    title: "Completion evidence / 完成判定",
    steps: ["RED evidence", "GREEN evidence", "completion decision"],
    policies: ["tool evidence only", "RED before GREEN", "required gates must pass"]
  };
}

function domainRouterCardMarkup(module, moduleSkills) {
  return `
    <article class="module-card router${module.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${module.nodeId}" data-module-id="${module.nodeId}" draggable="true">
      <div class="module-shell-head">
        ${capabilityCardMarkup(module, false)}
        <button class="node-remove" data-node-id="${module.nodeId}" title="Remove module" aria-label="Remove ${module.name}">×</button>
      </div>
      <div class="domain-router-flow">
        <strong>Domain route selector / 领域路线选择</strong>
        <div class="domain-router-line">
          <span>intent + repo signals</span>
          <b>choose domain</b>
        </div>
        <div class="domain-option-grid">
          ${domains.map((domain) => domainOptionMarkup(domain)).join("")}
        </div>
        <div class="domain-output">output: domain_route → Domain Module</div>
        ${moduleSkills.length ? `
          <div class="module-skill-slot compact">
            <strong>Optional router skills</strong>
            ${moduleSkills.map((skill) => `
              <div class="module-skill-pill ${skill.type}" data-node-id="${skill.nodeId}" draggable="true">
                <span>${skill.name}</span>
                <small>${moduleSkillRelation(module, skill)}</small>
                <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove skill" aria-label="Remove ${skill.name}">×</button>
              </div>
            `).join("")}
          </div>
        ` : `<div class="domain-no-skills">No skills required by default / 默认不需要挂载 skill</div>`}
      </div>
    </article>
  `;
}

function domainOptionMarkup(domain) {
  const labels = {
    d3a: "D3A",
    "team-domain": "Custom",
    general: "General"
  };
  return `
    <div class="domain-option-card ${domain.id}">
      <span>${labels[domain.id] ?? domain.name}</span>
      <small>${domain.name}</small>
      <div>
        ${domain.rules.slice(0, 2).map((rule) => `<em>${rule}</em>`).join("")}
      </div>
      <b>${domain.requiredGates.slice(0, 2).join(" + ")}</b>
    </div>
  `;
}

function laneModuleCardMarkup(module, moduleSkills) {
  const laneSkills = lanes
    .map((lane) => moduleSkills.find((skill) => skill.id.includes(`lane.${lane.id}`)))
    .filter(Boolean);
  const extraSkills = moduleSkills.filter((skill) => !laneSkills.includes(skill));

  return `
    <article class="module-card lane${module.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${module.nodeId}" data-module-id="${module.nodeId}" draggable="true">
      <div class="module-shell-head">
        ${capabilityCardMarkup(module, false)}
        <button class="node-remove" data-node-id="${module.nodeId}" title="Remove module" aria-label="Remove ${module.name}">×</button>
      </div>
      <div class="lane-flow">
        <strong>Lane strategy selector / 执行策略选择</strong>
        <div class="lane-router-line">
          <span>scenario_signals</span>
          <b>choose one lane</b>
        </div>
        <div class="lane-strategy-grid">
          ${laneSkills.length ? laneSkills.map((skill) => laneStrategyMarkup(skill)).join("") : `<span class="module-empty">Drop fast / lite / complex lanes here</span>`}
        </div>
        <div class="lane-output">output: fast_lite_complex_lane → downstream gates and execution policy</div>
        ${extraSkills.length ? `
          <div class="module-skill-slot compact">
            <strong>Extra lane skills</strong>
            ${extraSkills.map((skill) => `
              <div class="module-skill-pill ${skill.type}" data-node-id="${skill.nodeId}" draggable="true">
                <span>${skill.name}</span>
                <small>${moduleSkillRelation(module, skill)}</small>
                <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove skill" aria-label="Remove ${skill.name}">×</button>
              </div>
            `).join("")}
          </div>
        ` : ""}
      </div>
    </article>
  `;
}

function laneStrategyMarkup(skill) {
  const lane = lanes.find((item) => skill.id.includes(`lane.${item.id}`));
  const titles = {
    fast: "Fast / 快速",
    lite: "Lite / 默认",
    complex: "Complex / 完整"
  };
  const rules = lane?.rules ?? skill.inputs;
  const gates = lane?.gates ?? skill.evidence;
  const orchestration = lane?.orchestration ?? {
    plan: "custom plan",
    agent: "custom runtime",
    loop: "custom loop",
    evidence: "custom evidence"
  };
  return `
    <div class="module-skill-pill lane-strategy-card ${lane?.id ?? "custom"}" data-node-id="${skill.nodeId}" draggable="true">
      <div>
        <span>${titles[lane?.id] ?? skill.name}</span>
        <small>${lane?.summary ?? moduleSkillRelation({ type: "lane" }, skill)}</small>
      </div>
      <div class="lane-orchestration">
        <strong>Orchestration</strong>
        <em>Plan: ${orchestration.plan}</em>
        <em>Agent: ${orchestration.agent}</em>
        <em>Loop: ${orchestration.loop}</em>
        <em>Evidence: ${orchestration.evidence}</em>
      </div>
      <div class="lane-rule-list">
        <strong>When</strong>
        ${rules.slice(0, 1).map((rule) => `<em>${rule}</em>`).join("")}
      </div>
      <div class="lane-gate-list">
        <strong>Gates</strong>
        ${gates.slice(0, 2).map((gate) => `<b>${gate}</b>`).join("")}
      </div>
      <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove lane" aria-label="Remove ${skill.name}">×</button>
    </div>
  `;
}

function adapterModuleCardMarkup(module, moduleSkills) {
  const intake = moduleSkills.find((skill) => skill.id.includes("intent-intake"));
  const discovery = moduleSkills.find((skill) => skill.id.includes("intent-discovery"));
  const brainstorming = moduleSkills.find((skill) => skill.id.includes("brainstorming"));
  const grillMe = moduleSkills.find((skill) => skill.id.includes("grill-me"));
  const extraSkills = moduleSkills.filter((skill) => skill !== intake && skill !== discovery && skill !== brainstorming && skill !== grillMe);

  return `
    <article class="module-card adapter${module.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${module.nodeId}" data-module-id="${module.nodeId}" draggable="true">
      <div class="module-shell-head">
        ${capabilityCardMarkup(module, false)}
        <button class="node-remove" data-node-id="${module.nodeId}" title="Remove module" aria-label="Remove ${module.name}">×</button>
      </div>
      <div class="adapter-flow">
        <strong>Intent intake decision / 意图接入判定</strong>
        <div class="adapter-trigger-row">
          ${intake ? adapterFlowStep(intake, "IN", "Receives request / 接住输入") : `<span class="module-empty">Drop Intent Intake here</span>`}
          <div class="adapter-trigger-line" aria-label="if vague idea trigger discovery">
            <span>if vague idea / 如果意图模糊</span>
          </div>
          ${discovery ? adapterFlowStep(discovery, "DS", "Clarifies vague idea / 澄清模糊意图") : `<span class="module-empty">Drop Intent Discovery here</span>`}
        </div>
        <div class="brainstorm-flow" aria-label="brainstorming orchestration for unclear intent">
          <strong>Brainstorming orchestration / 意图不清时编排</strong>
          <div class="brainstorm-triggers">
            <span>Call Brainstorming: vague idea, many possible directions</span>
            <span>Call Grill Me: assumptions, missing constraints, weak acceptance</span>
          </div>
          <div class="brainstorm-steps">
            <span>clarify</span>
            <i></i>
            ${brainstorming ? brainstormSkillStep(brainstorming, "explore options") : `<span>Brainstorming</span>`}
            <i></i>
            ${grillMe ? brainstormSkillStep(grillMe, "assumption check") : `<span>Grill Me</span>`}
            <i></i>
            <span>draft_spec</span>
          </div>
          <b>loop until intent is actionable / 循环直到意图可执行</b>
        </div>
        <div class="adapter-direct-row" aria-label="other intake cases normalize directly">
          <span>clear/actionable / 明确可执行输入</span>
          <i></i>
          <b>normalized_request</b>
        </div>
        <div class="adapter-loopback">draft_spec from discovery ↩ back to intake → normalized_request</div>
        ${extraSkills.length ? `
          <div class="module-skill-slot compact">
            <strong>Extra adapter skills</strong>
            ${extraSkills.map((skill) => `
              <div class="module-skill-pill ${skill.type}" data-node-id="${skill.nodeId}" draggable="true">
                <span>${skill.name}</span>
                <small>${moduleSkillRelation(module, skill)}</small>
                <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove skill" aria-label="Remove ${skill.name}">×</button>
              </div>
            `).join("")}
          </div>
        ` : ""}
      </div>
    </article>
  `;
}

function brainstormSkillStep(skill, hint) {
  return `
    <span class="brainstorm-skill-step" data-node-id="${skill.nodeId}" draggable="true">
      ${skill.name}
      <small>${hint}</small>
      <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove skill" aria-label="Remove ${skill.name}">×</button>
    </span>
  `;
}

function adapterFlowStep(skill, index, relation) {
  return `
    <div class="adapter-step module-skill-pill ${skill.type}" data-node-id="${skill.nodeId}" draggable="true">
      <b>${index}</b>
      <span>${skill.name}</span>
      <small>${relation}</small>
      <button class="node-remove" data-node-id="${skill.nodeId}" title="Remove skill" aria-label="Remove ${skill.name}">×</button>
    </div>
  `;
}

function moduleSkillRelation(module, skill) {
  if (module.type === "adapter" && skill.id.includes("intent-intake")) {
    return "入口 / intake: classify clear vs vague";
  }
  if (module.type === "adapter" && skill.id.includes("intent-discovery")) {
    return "发现 / discovery: triggered by vague idea";
  }
  if (module.type === "router") {
    return "routing input";
  }
  if (module.type === "agent") {
    return "tool used by agent";
  }
  if (module.type === "gate") {
    return "constraint check";
  }
  return typeMeta[skill.type]?.hint ?? "contained capability";
}

function capabilityCardMarkup(capability, showSuggestedLayer) {
  const meta = typeMeta[capability.type] ?? typeMeta.skill;
  return `
    <div class="capability-topline">
      <span class="type-badge ${capability.type}">${meta.icon}</span>
      <div class="capability-name">
        <strong>${capability.name}</strong>
        <span>${meta.hint}</span>
      </div>
    </div>
    <div class="capability-body ${capability.type}">
      ${capabilityFacts(capability, showSuggestedLayer)}
    </div>
  `;
}

function capabilityFacts(capability, showSuggestedLayer) {
  if (capability.type === "agent") {
    return `
      <span>tools: ${compact(capability.tools)}</span>
      <span>session: ${capability.newSession ? "new" : "same"}</span>
    `;
  }
  if (capability.type === "gate") {
    return `
      <span>checks: ${compact(capability.evidence)}</span>
      <span>${capability.verified ? "verified evidence" : "bind command"}</span>
    `;
  }
  if (capability.type === "router") {
    return `
      <span>routes from: ${compact(capability.inputs)}</span>
      <span>decides: ${compact(capability.outputs)}</span>
    `;
  }
  if (capability.type === "lane") {
    return `
      <span>strategy: ${capability.name.replace(" Lane", "")}</span>
      <span>gates: ${compact(capability.evidence)}</span>
    `;
  }
  if (capability.type === "domain") {
    return `
      <span>route: ${compact(capability.inputs)}</span>
      <span>plans: ${compact(capability.outputs)}</span>
    `;
  }
  if (capability.type === "knowledge") {
    return `
      <span>context: ${compact(capability.inputs)}</span>
      <span>outputs: ${compact(capability.outputs)}</span>
    `;
  }
  if (capability.type === "runtime") {
    return `
      <span>orchestrates: ${compact(capability.inputs)}</span>
      <span>produces: ${compact(capability.outputs)}</span>
    `;
  }
  if (capability.type === "handoff") {
    return `
      <span>state: ${compact(capability.inputs)}</span>
      <span>handoff: ${compact(capability.outputs)}</span>
    `;
  }
  if (capability.type === "adapter") {
    return `
      <span>normalizes: ${compact(capability.inputs)}</span>
      <span>outputs: ${compact(capability.outputs)}</span>
    `;
  }
  return `
    <span>in: ${compact(capability.inputs)}</span>
    <span>out: ${compact(capability.outputs)}</span>
    ${showSuggestedLayer ? `<span>suggested: ${layerName(capability.layer)}</span>` : ""}
  `;
}

function moveLayer(layerId, direction) {
  const index = layers.findIndex((layer) => layer.id === layerId);
  const targetIndex = direction === "move-up" ? index - 1 : index + 1;
  if (index < 0 || targetIndex < 0 || targetIndex >= layers.length) return;
  const [layer] = layers.splice(index, 1);
  layers.splice(targetIndex, 0, layer);
  activeLayerId = layerId;
  renderAll();
  showToast(`${layer.name} moved ${direction === "move-up" ? "up" : "down"}`);
}

function removeNode(nodeId) {
  const node = nodes.find((item) => item.nodeId === nodeId);
  nodes = nodes.filter((item) => item.nodeId !== nodeId);
  delete moduleAssignments[nodeId];
  Object.keys(moduleAssignments).forEach((skillNodeId) => {
    if (moduleAssignments[skillNodeId] === nodeId) {
      delete moduleAssignments[skillNodeId];
    }
  });
  selectedNodeId = nodes[0]?.nodeId ?? null;
  renderAll();
  showToast(`${node?.name ?? "Capability"} removed from canvas`);
}

function renderLayerFocus() {
  const layer = layers.find((item) => item.id === activeLayerId);
  if (!layer) return;
  const capabilityCount = capabilities.filter((cap) => cap.layer === activeLayerId).length;
  const nodeCount = nodes.filter((node) => node.layer === activeLayerId).length;
  focusLayerName.textContent = layer.name;
  focusLayerSummary.textContent = layer.summary;
  focusCapabilityCount.textContent = `${capabilityCount} capabilities`;
  focusNodeCount.textContent = `${nodeCount} canvas nodes`;
}

function renderEdges() {
  return;
}

function drawEdge(from, to, failed) {
  const x1 = from.x + NODE_WIDTH;
  const y1 = from.y + NODE_HEIGHT / 2;
  const x2 = to.x;
  const y2 = to.y + NODE_HEIGHT / 2;
  const mid = Math.max(x1 + 36, (x1 + x2) / 2);
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`);
  path.setAttribute("class", `edge-line${failed ? " edge-fail" : ""}`);
  path.setAttribute("marker-end", "url(#arrow)");
  edges.appendChild(path);
}

function startNodeDrag(event, node, element) {
  if (event.button !== 0) return;
  event.preventDefault();
  selectedNodeId = node.nodeId;
  document.querySelectorAll(".canvas-node").forEach((item) => item.classList.remove("selected", "dragging"));
  element.classList.add("selected", "dragging");
  element.dataset.dragged = "false";

  const rect = canvas.getBoundingClientRect();
  dragState = {
    node,
    element,
    pointerId: event.pointerId,
    offsetX: event.clientX - rect.left - node.x,
    offsetY: event.clientY - rect.top - node.y,
    startX: node.x,
    startY: node.y
  };

  element.setPointerCapture(event.pointerId);
  element.addEventListener("pointermove", moveNode);
  element.addEventListener("pointerup", endNodeDrag);
  element.addEventListener("pointercancel", endNodeDrag);
  renderProperties();
}

function moveNode(event) {
  if (!dragState) return;
  const rect = canvas.getBoundingClientRect();
  const maxX = rect.width - NODE_WIDTH - 12;
  const maxY = rect.height - NODE_HEIGHT - 12;
  const nextX = event.clientX - rect.left - dragState.offsetX;
  const nextY = event.clientY - rect.top - dragState.offsetY;

  dragState.node.x = Math.max(12, Math.min(nextX, maxX));
  dragState.node.y = Math.max(42, Math.min(nextY, maxY));
  dragState.element.style.left = `${dragState.node.x}px`;
  dragState.element.style.top = `${dragState.node.y}px`;

  if (Math.abs(dragState.node.x - dragState.startX) > 3 || Math.abs(dragState.node.y - dragState.startY) > 3) {
    dragState.element.dataset.dragged = "true";
  }
  renderEdges();
}

function endNodeDrag(event) {
  if (!dragState) return;
  const { element, pointerId } = dragState;
  element.classList.remove("dragging");
  if (element.hasPointerCapture(pointerId)) {
    element.releasePointerCapture(pointerId);
  }
  element.removeEventListener("pointermove", moveNode);
  element.removeEventListener("pointerup", endNodeDrag);
  element.removeEventListener("pointercancel", endNodeDrag);
  dragState = null;
  renderValidation();
  renderYaml();
}

function renderProperties() {
  const node = nodes.find((item) => item.nodeId === selectedNodeId);
  if (!node) {
    propertiesEmpty.classList.remove("hidden");
    propertiesForm.classList.add("hidden");
    selectedSummary.textContent = "选择节点后配置 inputs、outputs、gates。";
    selectedType.textContent = "none";
    return;
  }

  propertiesEmpty.classList.add("hidden");
  propertiesForm.classList.remove("hidden");
  selectedSummary.textContent = `${node.name} 已标准化为 ${node.id}`;
  selectedType.textContent = node.type;
  selectedType.className = "status-pill good";

  document.getElementById("nodeName").value = node.name;
  document.getElementById("capabilityId").value = node.id;
  document.getElementById("nodeInputs").value = node.inputs.join("\n");
  document.getElementById("nodeOutputs").value = node.outputs.join("\n");
  document.getElementById("nodeEvidence").value = node.evidence.join("\n");
  document.getElementById("requiredNode").checked = node.required;
  document.getElementById("newSession").checked = node.newSession;
}

function renderValidation() {
  const names = nodes.map((node) => node.name);
  const hasApiContract = names.includes("API Contract");
  const hasCoding = names.includes("Coding Agent");
  const hasRedGreen = names.includes("RED / GREEN Gate");
  const hasTranBuild = names.includes("tran_build PASS");
  const apiBeforeCoding = indexOfName("API Contract") < indexOfName("Coding Agent");
  const redBeforeGreen = indexOfName("DT Writer") < indexOfName("RED / GREEN Gate");

  const gates = [
    ["Schema valid", nodes.length > 0, "sop.yaml can be generated"],
    ["API Contract first", hasApiContract && hasCoding && apiBeforeCoding, "contract before implementation"],
    ["RED evidence", nodes.some((node) => node.evidence.includes("red_evidence.yaml")) && redBeforeGreen, "RED before GREEN"],
    ["GREEN evidence", hasRedGreen, "DT gate configured"],
    ["Required DT GREEN", hasRedGreen, "TPRINT / FW / DPF placeholders"],
    ["tran_build PASS", hasTranBuild, "command uses placeholder"],
    ["No secret leakage", true, "placeholder hygiene enforced"]
  ];

  gateGrid.innerHTML = gates.map(([label, pass, detail]) => `
    <div class="gate-item ${pass ? "pass" : "fail"}">
      <strong>${pass ? "✓" : "!"} ${label}</strong>
      <span>${detail}</span>
    </div>
  `).join("");

  const allPass = gates.every((gate) => gate[1]);
  validationStatus.textContent = allPass ? "validated" : "needs fixes";
  validationStatus.className = `status-pill ${allPass ? "good" : "warn"}`;
}

function renderYaml() {
  const sorted = [...nodes].sort((a, b) => a.y - b.y || a.x - b.x);
  yamlPreview.textContent = [
    "package:",
    "  name: '@your-org/payment-team-idc-pack'",
    "  version: '0.3.0'",
    "  install:",
    "    command: 'npx @your-org/payment-team-idc-pack init'",
    "workflow:",
    "  id: payment-feature-delivery",
    "  source_of_truth: templates/sop.yaml",
    "routing_strategy:",
    `  scenario: dynamic-scenario`,
    `  domain: ${selectedDomainId}`,
    `  lane: ${selectedLaneId}`,
    "  domain_rules:",
    ...domains.find((domain) => domain.id === selectedDomainId).rules.map((rule) => `    - ${rule}`),
    "  lane_rules:",
    ...lanes.find((lane) => lane.id === selectedLaneId).rules.map((rule) => `    - ${rule}`),
    "layer_stack:",
    ...layers.flatMap((layer) => [
      `  ${layer.id}:`,
      `    name: ${layer.name}`,
      `    implementation: ${layerSelections[layer.id]}`,
      `    mode: ${layer.mode}`
    ]),
    "nodes:",
    ...sorted.flatMap((node, index) => [
      `  - id: ${slug(node.name)}`,
      `    type: ${node.type}`,
      `    layer: ${node.layer}`,
      `    capability: ${node.id}`,
      `    inputs: [${node.inputs.join(", ")}]`,
      `    outputs: [${node.outputs.join(", ")}]`,
      `    evidence: [${node.evidence.join(", ")}]`,
      `    session: ${node.newSession ? "new" : "same"}`,
      `    required: ${node.required}`,
      `    next: ${sorted[index + 1] ? slug(sorted[index + 1].name) : "completion"}`
    ]),
    "completion_gate:",
    "  required:",
    "    - api_contract_exists",
    "    - red_evidence_exists",
    "    - green_evidence_exists",
    "    - required_dt_domains_green",
    "    - tran_build_pass",
    "    - placeholder_hygiene_pass"
  ].join("\n");
}

function compact(values) {
  if (values.length <= 2) return values.join(", ");
  return `${values.slice(0, 2).join(", ")} +${values.length - 2}`;
}

function layerName(layerId) {
  return layers.find((layer) => layer.id === layerId)?.name ?? layerId;
}

function slug(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function indexOfName(name) {
  const sorted = [...nodes].sort((a, b) => a.y - b.y || a.x - b.x);
  const index = sorted.findIndex((node) => node.name === name);
  return index === -1 ? Number.POSITIVE_INFINITY : index;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2200);
}

function updateSelectedFromForm() {
  const node = nodes.find((item) => item.nodeId === selectedNodeId);
  if (!node) return;
  node.name = document.getElementById("nodeName").value;
  node.id = document.getElementById("capabilityId").value;
  node.inputs = document.getElementById("nodeInputs").value.split("\n").map((item) => item.trim()).filter(Boolean);
  node.outputs = document.getElementById("nodeOutputs").value.split("\n").map((item) => item.trim()).filter(Boolean);
  node.evidence = document.getElementById("nodeEvidence").value.split("\n").map((item) => item.trim()).filter(Boolean);
  node.required = document.getElementById("requiredNode").checked;
  node.newSession = document.getElementById("newSession").checked;
  renderAll();
}

document.getElementById("skillUpload").addEventListener("change", (event) => {
  const files = [...event.target.files];
  files.forEach((file) => {
    const baseName = file.name.replace(/\.(md|zip|yaml|yml|json)$/i, "");
    capabilities.unshift({
      id: `uploaded.${slug(baseName) || "skill"}`,
      layer: activeLayerId,
      type: "skill",
      name: baseName || "Uploaded Skill",
      inputs: ["<PLACEHOLDER_INPUT>"],
      outputs: ["<PLACEHOLDER_OUTPUT>"],
      tools: ["<PLACEHOLDER_TOOL>"],
      evidence: ["<PLACEHOLDER_EVIDENCE>"],
      verified: false
    });
  });
  event.target.value = "";
  renderAll();
  showToast(`${files.length} skill(s) normalized into Capability Catalog`);
});

layerImplementation.addEventListener("change", () => {
  layerSelections[activeLayerId] = layerImplementation.value;
  renderYaml();
  showToast(`${layers.find((layer) => layer.id === activeLayerId)?.name} layer swapped`);
});

if (domainSelection) {
  domainSelection.addEventListener("change", () => {
    selectedDomainId = domainSelection.value;
    renderAll();
    showToast(`Domain route switched to ${domains.find((domain) => domain.id === selectedDomainId)?.name}`);
  });
}

if (laneSelection) {
  laneSelection.addEventListener("change", () => {
    selectedLaneId = laneSelection.value;
    renderAll();
    showToast(`Lane strategy switched to ${selectedLaneId}`);
  });
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    activeFilter = tab.dataset.filter;
    renderCapabilities();
  });
});

document.getElementById("catalogSearch").addEventListener("input", renderCapabilities);

canvas.addEventListener("dragover", (event) => {
  event.preventDefault();
  canvas.classList.add("drag-over");
});

canvas.addEventListener("dragleave", () => canvas.classList.remove("drag-over"));

canvas.addEventListener("drop", (event) => {
  if (event.target.closest(".flow-layer")) return;
  event.preventDefault();
  canvas.classList.remove("drag-over");
  const capabilityId = event.dataTransfer.getData("text/plain");
  const capability = capabilities.find((cap) => cap.id === capabilityId);
  if (!capability) return;
  const rect = canvas.getBoundingClientRect();
  const node = nodeFromCapability(
    capability,
    Math.max(12, Math.min(event.clientX - rect.left - NODE_WIDTH / 2, rect.width - NODE_WIDTH - 12)),
    Math.max(42, Math.min(event.clientY - rect.top - NODE_HEIGHT / 2, rect.height - NODE_HEIGHT - 12))
  );
  nodes.push(node);
  selectedNodeId = node.nodeId;
  renderAll();
});

document.getElementById("propertiesForm").addEventListener("input", updateSelectedFromForm);

document.getElementById("validateBtn").addEventListener("click", () => {
  renderValidation();
  showToast(validationStatus.textContent === "validated" ? "Harness gates pass" : "Some gates need attention");
});

document.getElementById("previewBtn").addEventListener("click", () => {
  yamlPreview.scrollIntoView({ block: "nearest", behavior: "smooth" });
  showToast("Generated sop.yaml preview refreshed");
});

document.getElementById("exportBtn").addEventListener("click", () => {
  showToast("Export package mock generated: templates, skills, agents, gates, tests");
});

document.getElementById("addLayerBtn").addEventListener("click", addLayer);

document.getElementById("alignBtn").addEventListener("click", () => {
  const sorted = [...nodes].sort((a, b) => a.y - b.y || a.x - b.x);
  sorted.forEach((node, index) => {
    node.x = 70 + (index % 4) * 230;
    node.y = 92 + Math.floor(index / 4) * 150;
  });
  renderAll();
});

document.getElementById("resetBtn").addEventListener("click", () => {
  const demoState = createDemoState();
  layers = structuredClone(initialLayers);
  layerSelections = Object.fromEntries(layers.map((layer) => [layer.id, layer.implementations[0]]));
  moduleAssignments = demoState.moduleAssignments;
  nodes = demoState.nodes;
  selectedNodeId = demoState.selectedNodeId;
  activeLayerId = "intake";
  renderAll();
  showToast("Demo SOP reset");
});

window.addEventListener("resize", renderEdges);

renderAll();
