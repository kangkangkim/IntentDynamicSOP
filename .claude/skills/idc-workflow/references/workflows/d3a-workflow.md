# D3A Workflow

D3A 场景的 workflow 是 harness 固定的流程。IDC 可以检测输入是否足够进入 D3A、选择哪些固定 layer / DT domain、拆 execution unit、收集 evidence，但不能重新设计 D3A 主流程。

D3A 使用固定 architecture space，并在这个固定空间内做动态 planning。

D3A 与 General Coding 共享同一条执行骨架：

```text
Planner
  -> Knowledge Preparation
  -> Execution Unit Split
  -> TDD Execution
  -> Verification / Completion
```

区别不在于是否经过 Planner、Knowledge 或 TDD，而在于这些阶段读取什么约束：

- General Coding 由 Lane 和通用 component / test-domain registry 调节执行强度。
- D3A 由企业定义的固定 workflow、Coding Layer registry、DT Domain mapping 和 completion gate 约束。

D3A 不使用 Lane 分类：

```yaml
lane_policy:
  mode: not_applicable
  selected_lane: null
  bypass_lane_resolver: true
  execution_profile: d3a_fixed_workflow
```

一旦 Domain Module Router 选择 `d3a`，直接进入 harness 固定的 D3A workflow，
不再调用通用 Lane Resolver。任务大小、Layer 数量和风险信号仍会影响流程内部的
planning、DAG、execution unit、agent delegation 和 evidence plan，但不产生 Lane。

## 固定流程的起点

命中 D3A 只确认 Domain 和 `lane_applicability: not_applicable`，不代表输入已经
成熟。D3A 固定执行流程只能在 Human Alignment approved 后启动；其前置发现与
澄清规则和 IDC Core 一致：

```text
D3A hint / D3A task
  -> Input Maturity Gate
  -> raw_idea
       -> idc-intent-discovery
       -> idc-brainstorming
       -> idc-intent-grilling
  -> structured requirement / TR3 with critical gaps
       -> idc-intent-grilling
  -> Human Alignment Check
  -> AskUserTool approval
  -> approved
  -> D3A Fixed Workflow
```

关键缺口包括无法在不猜测的情况下确定 goal、core behavior、API semantics、
scope、Layer boundary、DT requirement、verification mapping 或 completion gate。
所有澄清、方向选择和 approval 必须通过 `AskUserTool`。Requirement Assessor
可以作为 Human Alignment Check 的被动检查器在批准前运行；未完成
Brainstorming / Grill Me 或仍有 open questions 时，不得进入 D3A Specification、
Planner 或 execution。

## 固定 Architecture Space

Coding Layer（架构固定，不提供配置覆盖）：

```text
TRAN_CFG
DO
VISP_ADP
TFC_TFI
TFE
ADP
DRV
```

DT Domain 只能从生效 registry 选择：`.idc/effective-team-config.yaml` 的
`knowledge_catalog.d3a.test_domains`。仓库默认 placeholder registry 是
TPRINT、FW、DPF；当 `team-config.yaml` 的 `domain.d3a.dt_domains` 非空时
整体替换默认 registry（不合并两个来源）；禁止选择生效 registry 之外的
DT Domain。

## 主流程

主流程顺序固定：

```text
用户任务
  -> Scenario Router
  -> Domain Module Router selects d3a candidate and Lane N/A policy
  -> Input Maturity Gate
  -> Discovery / Brainstorming if raw_idea
  -> Requirement Assessor + Human Alignment Check
  -> Grill Me if critical gaps remain
  -> AskUserTool approval
  -> D3A Fixed Workflow (Lane not applicable)
  -> D3A Specification
  -> API Contract
  -> Planner
       -> Impact Analysis
       -> Coding Layer 选择
       -> DT Domain 选择
       -> Dependency DAG
       -> Verification Mapping
       -> Knowledge Requirements
  -> Knowledge Gate
  -> Knowledge Preparation
  -> 按 Layer 拆 Layer Context Packet
  -> 每个 Layer 执行 TDD
       -> DT RED
       -> Implementation
       -> DT GREEN
  -> 所有 Required DT GREEN
  -> tran_build
  -> DONE
```

动态部分只允许发生在固定流程内部：Planner 选择命中的 Coding Layer、需要的
DT Domain、dependency DAG 和每个 Layer 的 knowledge requirements；Knowledge
Gate 准备对应上下文；随后按 Layer 拆 execution unit，并为每个 Layer 运行 TDD。
provider / adapter 绑定和 evidence refs 也按本次计划动态生成。

如果 `tran_build` 失败：

```text
TRAN_BUILD_FAIL
  -> ERROR_ANALYSIS
  -> TARGET_LAYER_FIX
  -> DT_REVERIFY
  -> TRAN_BUILD
```

## Planner 输出

```yaml
d3a_plan:
  coding_layers: [DO, TFE, DRV]
  dt_domains: [TPRINT, FW]
  dependency_dag:
    - from: DO
      to: TFE
    - from: TFE
      to: DRV
  verification_mapping:
    DO:
      required_dt_domains: [TPRINT]
    TFE:
      required_dt_domains: [TPRINT, FW]
    DRV:
      required_dt_domains: [FW]
  knowledge_requirements:
    DO: [layer_rules, api_contract, repo_anchors]
    TFE: [layer_rules, dependency_contracts, repo_anchors]
    DRV: [layer_rules, dt_constraints, repo_anchors]
  execution_strategy: Serial
```

上面的 mapping 只是 dummy example。真实 Coding Layer 到 DT Domain 的 mapping 必须在团队配置内填写。

## Execution Unit 约束

D3A 多 Layer 任务必须拆 Layer Context Packet：

```text
max_layers_per_packet = 1
max_change_loc_per_execution_unit = 500
```

拆分顺序：

```text
先按 Layer 拆
再按 execution unit 拆
最后按 500 LOC 拆
```

每个 Layer Context Packet 只携带该 Layer 实现和 TDD 所需的最小 knowledge，
每个 execution unit 都必须有独立 RED / GREEN evidence。
