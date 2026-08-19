# 保密区迁移 Checklist

这份 checklist 用来判断：当前非敏感 harness 能不能进入公司保密区，以及进入后第一步应该做什么。

企业已有资产与 `team-config.yaml` 插槽的逐项匹配关系，见图 `docs/enterprise-adoption-map.html`；也可以用浏览器打开 `docs/team-config-generator.html`，填表交互式生成 `team-config.yaml`。

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

多团队复用时，默认不要 fork IDC Core。每个团队只填写自己的 Domain
Module 和 Team Config：

- IDC Core：共享 `/id-workflow`、router、lane、gate、schema、human views、adapter eligibility registry。
- Domain Module：团队维护自己的 `<team-domain>/module.yaml`、领域 registry、领域 workflow / knowledge references。
- Team Config：团队在保密区维护 `team-config.yaml`，填写真实 repo path、内部 skill ref（含 DT 设计 / 编写 / 构建能力）、knowledge index、evidence parser 和 pass/fail 规则；DT domain / GC component / test domain 通过非空列表整体替换仓库默认注册表（不合并）。

仓库内注册表（`dt-domains.yaml`、`general-components.yaml`、`general-test-domains.yaml`）对企业接入方只读。

这些内容只能在公司保密区填写：

- 真实 D3A Layer 职责 / 边界。
- 真实 Layer API rules / coding patterns。
- 真实 forbidden patterns / common errors。
- 真实 DT Domain 目的 / 编写规则 / evidence 要求。
- 真实 Coding Layer 到 DT Domain 的 verification mapping。
- 真实 DT build 能力（企业 skill，命令封装在 skill 内部；没有现成 skill 就先包一个极小 wrapper skill 再绑定）。
- 真实 `tran_build` 能力和环境（企业 skill，含 PASS 判定）。
- 真实 repository path。
- 真实 CodeGraph / Wiki / grep / repository search provider。
- 真实 build error 到 responsible layer 的分析规则。
- 公司已有 Brainstorming 能力：通过 Team Binding 绑定到 `idc-brainstorming`，并归一化到 IDC draft spec 输出。
- 公司没有 Grill Me / Grill With Docs：直接带入 GitHub 仓库里的 `idc-intent-grilling`、`idc-intent-grilling-with-docs`、`grill-me-method.md`、`grill-with-docs-method.md` 和 `question-card-template.md`。
- 真实 GC 全家桶 SOP atomic ability mapping。
- 真实原代码仓 skill contract：`idc-dt-design`、`idc-dt-writer`、`<ENTERPRISE_GC_THIRD_SKILL_NAME>`。
- 真实 GC / DT adapter binding：基于 `team-config.yaml.template` 在保密区复制出 `team-config.yaml` 并填写团队自己的参数。

公共 `.claude/skills/idc-workflow/references/registries/skill-adapters.yaml`
只作为 adapter eligibility registry，不放任何团队真实路径、命令或内部 skill 名。

`.claude/skills/idc-workflow/references/registries/team-adapter-bindings.template.yaml`
保留为兼容参考；新团队优先使用根目录 `team-config.yaml.template`。

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
- DT Domain registry 仍然只包含 V0 placeholder domain；真实 DT domain 只通过 `team-config.yaml.domain.d3a_dt_domains` 覆盖，不直接改注册表。
- 没有 `.DS_Store` 等无关元数据文件。

## 入区后的第一条 Vertical Slice

不要一上来填所有 Layer。

先跑 Vertical Slice Readiness Gate：

```text
.claude/skills/idc-workflow/references/workflows/vertical-slice-readiness-gate.md
.claude/skills/idc-workflow/references/schemas/vertical-slice-readiness.schema.yaml
```

完整前端流程：通过 `/id-workflow` 输入真实需求或 TR3，走 Discovery →
Human Alignment（有 critical gap 先走 Grill Me）→ 用户 approve → freeze
API Contract → Layer Context Packet → RED → GREEN → `tran_build` →
Completion Summary。绑定哪些任务走 `dt-design`、哪些走 `dt-writer`、哪些
只需要 DT build / tran build，由 task contract 决定，不靠猜。

第一轮建议只做一条最小闭环：

1. 在 `team-config.yaml.knowledge.layer_docs` 绑一个 Layer knowledge ref（正文留在企业本地）。
2. 在 `team-config.yaml.domain.d3a_dt_domains` 填一个 DT domain 条目（含 `knowledge_ref`）。
3. 替换一个 mock context provider 为真实 repo search。
4. 如果需要 DT 设计，先通过 `idc-gc-sop-adapter -> idc-dt-design` 产出 DT design ref。
5. 如果需要 DT 编写，再通过 `idc-gc-sop-adapter -> idc-dt-writer` 产出 DT change 和 RED/GREEN evidence refs。
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

## 打通真实 Repo Context

- 配置真实 repo path 与 grep / CodeGraph / Wiki / repository search provider。
- 定义有 anchor 时用什么 provider、无 anchor 但有领域语义时用什么 provider。
- 定义 context packet 最大范围，Layer Context Packet 一次只包含当前 D3A Layer。
- 验收：给一个真实任务能生成 bounded context packet，而不是靠模型猜代码结构。

## 失败时补闭环

- DT build / `tran_build` 失败时保留 failure evidence ref，交给 `build-error-analyzer` 生成 targeted fix task。
- 判断失败属于哪个 Layer / DT Domain / adapter binding，只加载相关 Layer Context Packet。
- 修复后重新跑 RED / GREEN / `tran_build`；连续失败触发 Escalation，不靠模型硬猜。

## 扩展到多团队复用

其他团队复用 IDC Core、只换自己的 `team-config.yaml`（自定义 domain 走
`template-domain/`），操作细节见 `.claude/skills/idc-workflow/TEAM_CUSTOMIZATION.md`
与 `docs/adoption-guide.md`。
