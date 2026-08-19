# To Do Next: Confidential Adoption

这份清单用于进入企业保密区后的下一步落地。目标不是重做 IDC Core，而是把公共 harness 绑定到真实 D3A、GC SOP、DT skill、repo 和 evidence 系统上。

## 0. 入区前确认

目标：确认 public harness 本身是干净、可迁移的。

- [ ] 在本地 public 仓库运行 `python3 tests/test_harness.py`。
- [ ] 确认 `CLAUDE.md` 是唯一仓库规则入口。
- [ ] 确认没有企业 secret、真实内部路径、真实命令、真实日志。
- [ ] 确认 D3A Layer registry 仍是固定 7 层：`TRAN_CFG`、`DO`、`VISP_ADP`、`TFC_TFI`、`TFE`、`ADP`、`DRV`。
- [ ] 确认 V0 DT Domain registry 仍是 placeholder：`TPRINT`、`FW`、`DPF`。

验收：public harness 测试全绿，且可以安全带入保密区。

## 1. 建立保密区副本

目标：让企业内部有一份可填真实 binding 的 IDC workspace。

- [ ] 把仓库复制到企业保密环境。
- [ ] 保留 IDC Core 不变：`/id-workflow`、router、lane、gate、schema、human views、adapter eligibility registry。
- [ ] 在保密区复制根目录配置模板并填写真实参数：

```text
team-config.yaml.template -> team-config.yaml
```

- [ ] 不把真实路径、真实命令、内部 skill 名写进 public `skill-adapters.yaml`。

验收：保密区 workspace 能跑通 harness，且真实企业信息只出现在 confidential binding / domain module 中。

## 2. 填 D3A Domain Module

目标：把你设计的固定 D3A 流程接上真实企业知识。真实值只进 `team-config.yaml`（DT domain 条目带 `knowledge_ref`、`knowledge.layer_docs` 绑 Layer 知识 ref），知识正文留在企业本地文档，不搬运进 harness。

- [ ] 补 7 个 Coding Layer 的真实职责、边界、常见输入输出。
- [ ] 补每个 Layer 的 API rules、coding patterns、forbidden patterns、common errors。
- [ ] 补 `TPRINT`、`FW`、`DPF` 的真实 DT 编写规则和 evidence 要求。
- [ ] 补 Coding Layer 到 DT Domain 的真实多对多 verification mapping。
- [ ] 补 D3A workflow 中真实但非 secret 的流程约束说明。
- [ ] 明确哪些任务需要 `dt-design`，哪些任务需要 `dt-writer`，哪些只需要 DT build / tran build。

验收：D3A 仍是固定用户设计流程；动态部分只发生在 layer / DT domain / execution unit / adapter / evidence 选择。

## 3. 绑定企业能力

目标：让 IDC 能调用公司已有能力，而不是重新发明。

- [ ] 绑定公司 Brainstorming 到 `idc-brainstorming`。
- [ ] 保留本仓库内置的 `idc-intent-grilling` 作为 Grill Me。
- [ ] 保留 `idc-intent-grilling-with-docs` 处理需要沉淀文档的澄清。
- [ ] 绑定 GC 全家桶 SOP atomic abilities 到 `idc-gc-sop-adapter`。
- [ ] 绑定原代码仓 `dt-design` 到 `idc-dt-design`。
- [ ] 绑定原代码仓 `dt-writer` 到 `idc-dt-writer`。
- [ ] 绑定真实 DT build / run 到 `idc-dt-build`。
- [ ] 绑定真实 `tran_build` 到 `idc-tran-build`。

验收：每个 adapter 都有 capability key、allowed stage、required inputs、blocks_when、evidence rule 和真实 team binding。

## 4. 打通真实 repo context

目标：让 Knowledge Gate 能拿到真实代码事实。

- [ ] 配置真实 repo path。
- [ ] 配置 grep / CodeGraph / Wiki / repository search provider。
- [ ] 定义有 anchor 时用什么 provider。
- [ ] 定义无 anchor 但有领域语义时用什么 provider。
- [ ] 定义 context packet 最大范围，避免一次性塞满 repo。
- [ ] 确认 Layer Context Packet 一次只包含当前 D3A Layer。

验收：给一个真实任务时，可以生成 bounded context packet，而不是靠模型猜代码结构。

## 5. 跑第一条 Vertical Slice

目标：先证明最小闭环成立，不要一天内铺满所有 D3A 知识。

- [ ] 选择一个小 D3A 任务，最好只涉及 1 个 Coding Layer。
- [ ] 通过 `/id-workflow` 输入真实需求或 TR3。
- [ ] 让 Discovery 产出 normalized request / draft intent。
- [ ] 让 Human Alignment Check 检测 readiness、critical gap、docs needed、approval validity。
- [ ] 如有 critical gap，先走 Grill Me。
- [ ] 用户 approve Alignment View 后才进入 execution。
- [ ] Freeze API Contract。
- [ ] 生成 Layer Context Packet。
- [ ] 通过 `dt-design` / `dt-writer` 或已有 DT 路径跑出 RED evidence。
- [ ] 完成最小代码变更。
- [ ] 跑出 GREEN evidence。
- [ ] 跑真实 `tran_build`。
- [ ] 输出 Completion Summary。

验收：同一条任务具备 API Contract、RED evidence、GREEN evidence、`tran_build PASS` 和 Completion Summary。

## 6. 失败时补闭环

目标：把失败变成可定位、可修复、可复跑。

- [ ] 如果 DT build 失败，记录 failure evidence ref。
- [ ] 如果 `tran_build` 失败，交给 build error analyzer 生成 targeted fix task。
- [ ] 判断失败属于哪个 Layer / DT Domain / adapter binding。
- [ ] 只加载相关 Layer Context Packet。
- [ ] 修复后重新跑 RED / GREEN / tran_build。
- [ ] 连续失败时触发 Escalation，不靠模型硬猜。

验收：失败不会直接变成“问人怎么办”，而是先经过 evidence-based targeted fix。

## 7. 扩展到多团队复用

目标：让其他团队复用 Core，只替换自己的 domain module 和 binding。

- [ ] 抽出哪些是 IDC Core 共享能力。
- [ ] 明确哪些是 D3A-only。
- [ ] 为其他团队准备 `<team-domain>/module.yaml` 模板。
- [ ] 为其他团队准备独立 `team-config.yaml`（老团队 `team_adapter_binding_ref` 仅作兼容）。
- [ ] 保证不同团队不会互相污染真实路径、命令、skill 名。

验收：新团队接入时只新增 domain module / team binding，不 fork IDC Core。

## 当前最推荐的下一步

先做第 5 步的一条 Vertical Slice。

选择一个最小真实 D3A 任务，然后只填完成这条任务必需的：

- 1 个 Layer knowledge。
- 1 个 DT Domain knowledge。
- 1 条 Layer -> DT verification mapping。
- 1 组 repo context provider。
- 1 组 DT / tran build binding。

跑通后再扩展，不要先补完整企业知识库。
