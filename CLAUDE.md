# Intent-Driven Coding Harness

这个仓库定义一个 Claude Code 原生的 Intent-Driven Coding 骨架。

## 运行原则

1. 编辑代码前，所有任务都必须先经过 workflow entrypoint。
2. 只有任务属于 D3A domain 时，才使用 D3A workflow。
3. 其他 coding 任务使用 General Coding 工作流。
4. D3A architecture 是固定的，不能创建或删除 D3A Layer。
5. D3A knowledge 必须渐进加载，只加载受影响的 coding layer 和 DT domain。
6. 企业特定细节在进入保密区前都必须保持 placeholder。
7. API Contract 和 task contract 形成前，不要实现 production code。
8. 没有 RED / GREEN evidence，不要标记 implementation complete。
9. required DT domain 全部 GREEN 且 `tran_build` PASS 后，才能标记 D3A task done。

## D3A Layer Registry

- `TRAN_CFG`
- `DO`
- `VISP_ADP`
- `TFC_TFI`
- `TFE`
- `ADP`
- `DRV`

## DT Domain Registry

- `TPRINT`
- `FW`
- `DPF`

## 角色边界

- Main agent 负责编排 workflow 和 evidence。
- `d3a-layer-coder` 一次只负责一个 coding layer。
- `dt-test-writer` 负责 DT test preparation 和 RED evidence。
- `build-error-analyzer` 把 build failure 转成 targeted fix task。
