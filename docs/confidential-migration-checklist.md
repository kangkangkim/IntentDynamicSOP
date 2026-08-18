# 保密区迁移 Checklist

这份 checklist 用来判断：当前非敏感 harness 能不能进入公司保密区，以及进入后第一步应该做什么。

## 外部环境保持通用的内容

这些内容不应该绑定真实企业信息：

- 工作流状态机。
- Contract schema。
- Scenario Router 边界。
- Requirement Assessor 决策规则。
- Subagent 职责 prompt。
- Placeholder skill 接口。
- Mock examples。
- Harness tests。

## 进入保密区后需要填写的内容

这些内容只能在公司保密区填写：

- 真实 D3A Layer 职责 / 边界。
- 真实 Layer API rules / coding patterns。
- 真实 forbidden patterns / common errors。
- 真实 DT Domain 目的 / 编写规则 / evidence 要求。
- 真实 Coding Layer 到 DT Domain 的 verification mapping。
- 真实 DT build / run 命令。
- 真实 `tran_build` 命令和环境。
- 真实 repository path。
- 真实 CodeGraph / Wiki / grep / repository search provider。
- 真实 build error 到 responsible layer 的分析规则。
- 真实 GC 全家桶 SOP atomic ability mapping。
- 真实原代码仓 skill contract：`dt-design`、`dt-writer`、`<ENTERPRISE_GC_THIRD_SKILL_NAME>`。

## 入区前检查

入区前先跑：

```sh
python3 tests/test_harness.py
```

需要确认：

- 测试全部通过。
- Placeholder hygiene 通过。
- 仓库里没有企业 secret。
- D3A Layer registry 仍然匹配固定架构。
- DT Domain registry 仍然只包含 V0 placeholder domain，除非保密区内明确扩展。
- 没有 `.DS_Store` 等无关元数据文件。

## 入区后的第一条 Vertical Slice

不要一上来填所有 Layer。

先跑 Vertical Slice Readiness Gate：

```text
.claude/skills/idc-workflow/references/workflows/vertical-slice-readiness-gate.md
.claude/skills/idc-workflow/references/schemas/vertical-slice-readiness.schema.yaml
```

第一轮建议只做一条最小闭环：

1. 填一个 Layer knowledge 文件。
2. 填一个 DT Domain knowledge 文件。
3. 替换一个 mock context provider 为真实 repo search。
4. 如果需要 DT 设计，先通过 `gc-sop-adapter -> dt-design` 产出 DT design ref。
5. 如果需要 DT 编写，再通过 `gc-sop-adapter -> dt-writer` 产出 DT change 和 RED/GREEN evidence refs。
6. 跑出一条真实 RED evidence。
7. 跑出一条真实 GREEN evidence。
8. 跑一次真实 `tran_build`。
9. 如果失败，把错误交给 `build-error-analyzer` 生成 targeted fix task。

目标是先证明 workflow 闭环成立，再逐步扩展到更多 Layer / DT Domain。

Readiness Gate 只能证明真实绑定已经足够启动执行，不能替代：

- RED evidence。
- GREEN evidence。
- `tran_build` PASS evidence。
- Completion Summary。

## 入区后不要做的事

- 不要重新设计 D3A architecture。
- 不要把 Coding Layer 和 DT Domain 简化成一对一。
- 不要跳过 API Contract。
- 不要跳过 RED evidence。
- 不要把 DT GREEN 当成任务完成。
- 不要在 `tran_build` 未 PASS 时标记 DONE。
