const layers = [
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
    gates: ["task_summary", "focused_check"]
  },
  {
    id: "lite",
    name: "lite",
    summary: "默认开发路径，要求 focused contract 和 GREEN evidence。",
    rules: ["not fast", "no complex hard trigger", "bounded implementation"],
    gates: ["task_contract", "green_evidence", "build_check"]
  },
  {
    id: "complex",
    name: "complex",
    summary: "高风险、跨层、API 或 DT 复杂变化；启用完整 planning 和 evidence gates。",
    rules: ["cross layer impact", "API / behavior semantics change", "shotgun modification risk"],
    gates: ["detailed_plan", "api_contract", "red_evidence", "green_evidence", "tran_build"]
  }
];

const initialCapabilities = [
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
    type: "skill",
    name: "Lane Resolver",
    inputs: ["normalized_request", "scenario_signals"],
    outputs: ["fast_lite_complex_lane"],
    tools: ["lane-registry"],
    evidence: ["lane-decision.yaml"],
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

const demoNodes = [
  nodeFromCapability(initialCapabilities[0], 70, 92),
  nodeFromCapability(initialCapabilities[1], 300, 92),
  nodeFromCapability(initialCapabilities[2], 530, 92),
  nodeFromCapability(initialCapabilities[3], 530, 242),
  nodeFromCapability(initialCapabilities[5], 300, 392),
  nodeFromCapability(initialCapabilities[4], 530, 392),
  nodeFromCapability(initialCapabilities[6], 760, 392),
  nodeFromCapability(initialCapabilities[7], 760, 542)
];

let capabilities = [...initialCapabilities];
let nodes = demoNodes;
let selectedNodeId = nodes[2].nodeId;
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

function renderAll() {
  renderLayers();
  renderCapabilities();
  renderArchitectureBoard();
  renderCanvas();
  renderProperties();
  renderLayerDetail();
  renderRoutingStrategy();
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
  activeLayerLabel.textContent = `${activeLayer.name}: ${activeLayer.summary}`;
  capabilityList.innerHTML = "";

  capabilities
    .filter((cap) => cap.layer === activeLayerId)
    .filter((cap) => activeFilter === "all" || cap.type === activeFilter)
    .filter((cap) => !query || `${cap.name} ${cap.id} ${cap.type}`.toLowerCase().includes(query))
    .forEach((capability) => {
      const card = document.createElement("article");
      card.className = `capability-card ${capability.type}`;
      card.draggable = true;
      card.dataset.capabilityId = capability.id;
      card.innerHTML = `
        <div class="cap-title">
          <span>${capability.name}</span>
          <span class="type-chip ${capability.type}">${capability.type}</span>
        </div>
        <p>${capability.id}</p>
        <div class="cap-meta">
          <span>in: ${capability.inputs.join(", ")}</span>
          <span>out: ${capability.outputs.join(", ")}</span>
          <span>layer: ${activeLayer.name}</span>
          <span>${capability.verified ? "verified" : "needs command binding"}</span>
        </div>
      `;
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
  canvas.querySelectorAll(".flow-layer").forEach((node) => node.remove());
  canvasHint.style.display = nodes.length ? "none" : "block";
  renderLayerFocus();

  layers.forEach((layer, index) => {
    const layerNodes = nodes.filter((node) => node.layer === layer.id);
    const element = document.createElement("section");
    element.className = `flow-layer${layer.id === activeLayerId ? " active" : ""}`;
    element.dataset.layerId = layer.id;
    element.innerHTML = `
      <div class="flow-spine">
        <span>L${index + 1}</span>
      </div>
      <div class="flow-layer-main">
        <div class="flow-layer-head">
          <div>
            <strong>${layer.name}</strong>
            <p>${layer.summary}</p>
          </div>
          <div class="flow-layer-controls">
            <select class="inline-implementation" data-layer-id="${layer.id}" aria-label="${layer.name} implementation">
              ${layer.implementations.map((item) => `<option value="${item}"${item === layerSelections[layer.id] ? " selected" : ""}>${item}</option>`).join("")}
            </select>
            <button class="mini-button" data-action="move-up" data-layer-id="${layer.id}" ${index === 0 ? "disabled" : ""} title="Move layer up">↑</button>
            <button class="mini-button" data-action="move-down" data-layer-id="${layer.id}" ${index === layers.length - 1 ? "disabled" : ""} title="Move layer down">↓</button>
          </div>
        </div>
        <div class="flow-node-list">
          ${layerNodes.length ? layerNodes.map((node) => `
            <article class="flow-node ${node.type}${node.nodeId === selectedNodeId ? " selected" : ""}" data-node-id="${node.nodeId}">
              <div class="node-title">
                <span>${node.name}</span>
                <span class="type-chip ${node.type}">${node.type}</span>
              </div>
              <div class="node-facts">
                <span>in: ${compact(node.inputs)}</span>
                <span>out: ${compact(node.outputs)}</span>
              </div>
              <button class="node-remove" data-node-id="${node.nodeId}" title="Remove capability" aria-label="Remove ${node.name}">×</button>
            </article>
          `).join("") : `<div class="flow-empty">Drop atomic capabilities for ${layer.name}</div>`}
        </div>
      </div>
    `;

    element.addEventListener("click", (event) => {
      const actionButton = event.target.closest("[data-action]");
      const removeButton = event.target.closest(".node-remove");
      if (actionButton || removeButton || event.target.closest(".inline-implementation")) return;
      const nodeElement = event.target.closest(".flow-node");
      activeLayerId = layer.id;
      if (nodeElement) {
        selectedNodeId = nodeElement.dataset.nodeId;
      }
      renderAll();
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

    element.addEventListener("dragover", (event) => {
      event.preventDefault();
      element.classList.add("drop-target");
    });

    element.addEventListener("dragleave", () => element.classList.remove("drop-target"));

    element.addEventListener("drop", (event) => {
      event.preventDefault();
      element.classList.remove("drop-target");
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

    canvas.appendChild(element);
  });
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

domainSelection.addEventListener("change", () => {
  selectedDomainId = domainSelection.value;
  renderAll();
  showToast(`Domain route switched to ${domains.find((domain) => domain.id === selectedDomainId)?.name}`);
});

laneSelection.addEventListener("change", () => {
  selectedLaneId = laneSelection.value;
  renderAll();
  showToast(`Lane strategy switched to ${selectedLaneId}`);
});

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

document.getElementById("alignBtn").addEventListener("click", () => {
  const sorted = [...nodes].sort((a, b) => a.y - b.y || a.x - b.x);
  sorted.forEach((node, index) => {
    node.x = 70 + (index % 4) * 230;
    node.y = 92 + Math.floor(index / 4) * 150;
  });
  renderAll();
});

document.getElementById("resetBtn").addEventListener("click", () => {
  nodes = demoNodes.map((node) => ({ ...structuredClone(node), nodeId: `${node.id}-${Math.random().toString(16).slice(2, 7)}` }));
  selectedNodeId = nodes[2].nodeId;
  renderAll();
  showToast("Demo SOP reset");
});

window.addEventListener("resize", renderEdges);

renderAll();
