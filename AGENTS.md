# 仓库指令

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

## 验证

运行：

```sh
python3 tests/test_harness.py
```

测试会验证 schema 示例、registry 约束、workflow gate 和 placeholder hygiene。
