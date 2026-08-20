# Intent-Driven Coding Harness

这个仓库保存 Intent-Driven Coding 工作流的非敏感骨架。

## 范围

- 仓库内不得包含企业 secret。
- 不得编造内部 D3A 实现细节。
- 涉及专有 API、路径、命令、日志、测试名、构建系统、架构事实时，必须使用显式 placeholder。
- 优先使用小而可组合的 Markdown / YAML 文件，不引入自定义 agent framework。

## 开发规则

- D3A architecture 在这个 harness 中是固定的：
  `TRAN_CFG`、`DO`、`VISP_ADP`、`TFC_TFI`、`TFE`、`ADP`、`DRV`。
- V0 DT domain 是 placeholder：
  `TPRINT`、`FW`、`DPF`。
- Coding Layer 到 DT Domain 是多对多关系，不能猜。
- API Contract 必须先于 implementation。
- TDD completion 必须先有 RED evidence，再有 GREEN evidence。
- D3A completion 要求所有 required DT domain GREEN，并且 `tran_build` PASS。
- Completion 必须基于工具证据，而不是模型自信。

## 运行原则

1. 用户侧统一入口是 `idc-workflow` skill；可显式使用 `$idc-workflow`，也可由自然语言自动匹配，不维护 `.claude/commands`。
2. 所有可执行 IDC 能力都必须沉淀为 `.claude/skills/idc-*/SKILL.md`，名字必须以 `idc-` 开头。
3. 编辑代码前，所有 IDC-run 任务都必须先经过 `idc-workflow` skill。
4. Scenario Router 先动态分流：Domain Module、Dynamic Scenario、General Coding fallback 或 NEED_TRIAGE。
5. 只有任务属于 D3A domain module 时，才使用 D3A workflow。
6. D3A architecture 和主 workflow 是固定的：不能创建或删除 D3A Layer；Lane 对 D3A 不适用，并跳过通用 Lane Resolver。
7. D3A knowledge 必须渐进加载，只加载受影响的 coding layer 和 DT domain。
8. 企业特定细节在进入保密区前都必须保持 placeholder。
9. API Contract 和 task contract 形成前，不要实现 production code。
10. 没有 RED / GREEN evidence，不要标记 implementation complete。
11. required DT domain 全部 GREEN 且 `tran_build` PASS 后，才能标记 D3A task done。
12. 所有问用户的问题、确认、approval、re-alignment 和 escalation 决策，都必须通过 `AskUserTool` 发出；不要用普通文本直接追问用户。
13. Main agent 是 `planning_and_delegation_only`。任何 Lane 的 repository mutation（代码、测试、构建文件、验证产物、targeted fix）都必须经过 Execution Authorization，并真实派发给 subagent / agent team / official dynamic workflow。
14. General Domain 必须由 executor 加载 `idc-general-coding` 作为外层执行协议；`idc-gc-sop-adapter` 只能作为 Capability Selector 选中的内层原子能力。
15. delegation tool 不可用时返回 `BLOCKED_DELEGATION_REQUIRED`，不得由 main agent 直接实现；Completion 必须检查 authorization ID、dispatch tool-call ref 和 executor session ref。

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

- Main agent 负责编排 workflow、delegation 和 evidence，不直接修改仓库。
- `d3a-layer-coder` 一次只负责一个 coding layer。
- `dt-test-writer` 负责 DT test preparation 和 RED evidence。
- `build-error-analyzer` 把 build failure 转成 targeted fix task。

## 验证

运行：

```sh
python3 tests/test_harness.py
```

测试会验证 schema 示例、registry 约束、workflow gate 和 placeholder hygiene。
