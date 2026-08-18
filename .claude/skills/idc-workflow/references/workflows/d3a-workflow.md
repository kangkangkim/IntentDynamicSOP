# D3A Workflow

D3A 场景的 workflow 是固定的用户设计流程。IDC 可以检测输入是否足够进入 D3A、选择哪些固定 layer / DT domain、拆 execution unit、收集 evidence，但不能重新设计 D3A 主流程。

D3A 使用固定 architecture space，并在这个固定空间内做动态 planning。

## 固定 Architecture Space

Coding Layer：

```text
TRAN_CFG
DO
VISP_ADP
TFC_TFI
TFE
ADP
DRV
```

V0 DT Domain：

```text
TPRINT
FW
DPF
```

## 主流程

主流程顺序固定：

```text
用户任务
  -> Scenario Router
  -> Requirement Assessor
  -> D3A Specification
  -> API Contract
  -> Impact Analysis
  -> Coding Layer 选择
  -> DT Domain 选择
  -> Dependency DAG
  -> Verification Mapping
  -> Layer Context Packet Split
  -> Knowledge Gate
  -> Layer Context Packet
  -> DT RED
  -> Implementation
  -> DT GREEN
  -> 所有 Required DT GREEN
  -> tran_build
  -> DONE
```

动态部分只允许发生在固定流程内部：选择命中的 Coding Layer、需要的 DT Domain、dependency DAG、execution unit 拆分、provider / adapter 绑定和 evidence refs。

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
  execution_strategy: Serial
```

上面的 mapping 只是 dummy example。真实 Coding Layer 到 DT Domain 的 mapping 必须在保密区填写。

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

每个 execution unit 都必须有独立 evidence。
