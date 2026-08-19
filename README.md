# Intent Dynamic Code

Intent Dynamic Code 是一个非敏感的企业 Coding 工作流骨架。

它的目标不是在外部环境实现真实企业 D3A，而是先把一套可迁移、可验证、可填充的工作流骨架准备好。进入公司保密区后，再把真实代码知识、测试知识和构建命令绑定进去。

## 项目优势

IDC 的核心优势是把动态智能分流和企业固定 SOP 分开：外层可以根据输入动态判断，内层可以保护团队已经验证过的固定流程。

- **公共框架可复用**：`IDC Core` 只保存 `/id-workflow` 薄入口、`idc-*` skills、router、lane、gate、schema、human views 和 adapter eligibility registry，不保存企业 secret。
- **企业知识不外泄**：真实 D3A 知识、GC SOP 原子能力、repo path、构建命令、内部 skill 名都通过保密区 `team-config.yaml` / knowledge index 接入。
- **D3A 主流程固定**：D3A 是用户设计的固定 workflow。IDC 只在固定流程内选择 Layer、DT Domain、adapter、execution unit 和 evidence，不重排 D3A。
- **Human Alignment 管检测**：Discovery 只做 intake / normalize / signal；Human Alignment Check 统一检测 readiness、critical gap、docs needed、approval validity 和 scope drift。
- **GC SOP 按需调用**：GC SOP 是企业能力池，不是默认全家桶。只有 stage、capability key、contract、team binding 和 blocks_when 都匹配时才触发。
- **Evidence-first 完成标准**：API Contract 先于 implementation；RED evidence 先于 GREEN evidence；D3A DONE 必须满足 required DT GREEN 和 `tran_build PASS`。
- **多团队低成本接入**：其他团队复用 IDC Core，只新增自己的 Domain Module 和 Team Binding，不需要 fork 出另一套框架。

## V0 定位

V0 不是完整企业 D3A 实现，而是可进入保密区落地的最小成熟框架。

V0 已经固定：

- 统一入口：`/id-workflow`。
- 能力实现：所有可执行能力都沉淀为 `.claude/skills/idc-*/SKILL.md`，command 只保留薄入口别名。
- 三条顶层路径：Dynamic Scenario Coding、Domain Module Coding、General Coding Fallback。
- 三种 Lane：`fast`、`lite`、`complex`。
- D3A 固定 Coding Layer：`TRAN_CFG`、`DO`、`VISP_ADP`、`TFC_TFI`、`TFE`、`ADP`、`DRV`。
- V0 DT Domain placeholder：`TPRINT`、`FW`、`DPF`。
- Human Alignment Check 作为 readiness / gap / approval gate。
- Skill Adapter Router 作为 GC SOP、Superpowers、DT skill、build skill 的唯一接入门。
- `team-config.yaml.template` 入口配置，用于在保密区绑定真实路径、命令、内部 skill、knowledge index 和 evidence parser。
- Team Binding 模板作为兼容参考；新团队优先填 `team-config.yaml`。
- Mock D3A / General E2E examples 和 harness tests。

V0 不做：

- 不复制企业内部 D3A 知识。
- 不编造 Coding Layer 到 DT Domain 的真实 mapping。
- 不内置真实 repo path、构建命令、日志、API 或企业 skill 名。
- 不把 GC SOP 十几个能力全部默认打开。
- 不让模型重新设计 D3A 主流程。

进入企业内部后，优先补的是索引和 binding，而不是把企业知识搬进 public harness：

```text
真实 D3A 知识地址
+ 真实 GC SOP atom mapping
+ 原代码仓 dt-design / dt-writer skill ref
+ 真实 DT / tran_build command
+ repo context provider
+ evidence parser
```

第一阶段目标是跑通一条最小 D3A vertical slice：1 个 Layer、1 个 DT Domain、1 条 verification mapping、1 组 repo context provider、RED evidence、GREEN evidence、`tran_build PASS` 和 Completion Summary。

## 多团队复用模型

IDC 的整体能力面向多个团队复用。公共仓库只维护稳定框架和非敏感
contract；团队差异通过轻量 DIY 层接入。

```text
IDC Core
  共享：/id-workflow、router、lane、gate、schema、human views、adapter eligibility registry
  不放：真实团队路径、命令、内部 skill 名、日志、企业 API

Domain Module
  团队扩展：<team-domain>/module.yaml、团队 layer/test registry、团队 workflow references
  用途：描述这个团队的领域怎么被 IDC 识别、规划和验证

Team Config
  团队 DIY：team-config.yaml、repo path、build/run command、internal skill ref、knowledge index、evidence parser
  用途：把公共 adapter 和 workflow extension 绑定到该团队自己的真实实现
```

Pre-alignment 也遵守同一规则：公司已有 Brainstorming 时通过 Team
Binding 复用；公司没有 Grill Me 时，直接使用本 GitHub 仓库提供的
`idc-intent-grilling`、`idc-intent-grilling-with-docs`、`grill-me-method.md`
和 `grill-with-docs-method.md`。

推荐复用方式：

1. 多团队共享 `IDC Core`，不要 fork 出不同 core。
2. 新领域先新增 `Domain Module`，不要改 D3A 或 General 的核心规则。
3. 真实路径、命令、内部 skill 和 knowledge index 只写在团队自己的 `team-config.yaml`。
4. 团队确实需要差异化时，优先改 team config / domain module / provider rules，再考虑改 core。

## 顶层路径

- **Dynamic Scenario Coding**：不绑定固定领域模块，按复杂度、不确定性、风险和可测试性动态编排。
- **Domain Module Coding**：通过可插拔 Domain Module 进入领域工作流。D3A 是当前第一个自定义 active module。
- **General Coding Fallback**：保留给简单普通 coding 任务。

同时，执行强度由 Lane 决定：

```text
fast / lite / complex
```

Domain Module 决定领域差异和 required contracts；Lane 只决定流程跑多重。
IDC V0 只允许这三种 Lane，不设置 `known-domain`、`d3a`、`gc` 或
`dynamic` lane。

整体执行哲学：

```text
前置对齐
后置自动闭环
异常再回人
```

V0 重点完成 D3A workflow 结构、contract、subagent prompt、skill 接口、mock demo、保密区 binding 入口和确定性的验证 gate。

当前框架目标不是把 D3A 写进 Core，而是先形成：

```text
动态场景分流框架
+ 自定义 Domain Module
+ 可复用企业 SOP / 原仓 skill adapter
```

## 怎么看这个仓库

优先看这三个入口：

```text
README.md
  -> .claude/commands/id-workflow.md
  -> docs/architecture.md
  -> docs/adoption-guide.md
```

- `README.md`：看当前完成了什么、目录怎么组织、怎么验证。
- `.claude/commands/id-workflow.md`：用户侧统一 `/id-workflow` 薄入口；不承载 workflow 逻辑。
- `team-config.yaml.template`：保密区复制成 `team-config.yaml` 后填参即用的唯一入口配置。
- `docs/architecture.md`：看整体架构和 D3A / General Coding 的关系。
- `QUICKSTART.md`：看如何从复制仓库到第一条 vertical slice。
- `docs/adoption-guide.md`：看其他团队如何复制 SOP。
- `docs/atomic-skills.md`：看哪些能力已经拆成可复用原子 skill。
- `docs/skillization-boundary.md`：看哪些内容应该 skill 化，哪些应该保持 reference。
- `.claude/skills/idc-workflow/assets/README.md`：看不能 skill 化的内容如何按官方 skill 目录语义沉淀为 `references/` 或 `assets/`。
- `docs/architecture-diagram.md`：看 Core + Domain Module 的架构图。
- `docs/user-input-routing-overview.html`：看不同用户输入如何先进入 Discovery，再由 Human Alignment Gate 检测成熟度、关键缺口、approval 有效性，并分流到前置能力、Domain、Lane、adapter 和执行闭环。
- `docs/intake-discovery-trigger-flow.html`：看 Discovery 产出 draft intent 后，Human Alignment Check 如何从左到右触发 Brainstorming / Grill Me / Grill With Docs / Alignment 的条件。
- `docs/flow-d3a-general.html`：看从输入开始的 D3A / General 双路径 HTML 图。
- `docs/context-runtime-view.html`：看 main agent / subagent 的运行时上下文占用变化。
- `docs/confidential-migration-checklist.md`：看进入保密区后要填什么、先做哪条 vertical slice。
- `docs/terminology.md`：看哪些英文是故意保留的机器稳定标识。

细节说明放在：

```text
docs/deep-dive/
```

## 目录结构

```text
.
├── CLAUDE.md
├── .claude/
├── docs/
├── examples/
├── test/
└── tests/
```

## D3A 核心流程

D3A 不是 IDC Core 本体，而是一个可插拔 Domain Module：

```text
.claude/skills/idc-workflow/references/domains/d3a/module.yaml
```

D3A 场景的流程是固定的用户设计流程。IDC 不重新设计 D3A 主流程，只在这个固定流程内判断进入条件、选择固定 Coding Layer、选择 required DT Domain、拆 Layer Context Packet、绑定 adapter，并用 DT RED / GREEN 与 `tran_build` evidence 判定完成。

```text
用户任务
  -> Scenario Router
  -> Intent Maturity Router
  -> Discovery Provider / 一句话想法先发散
  -> Domain Module Router
  -> 选择 d3a module
  -> Lane Resolver
  -> Contract Gate
  -> D3A Requirement Assessor
  -> Human Alignment Check
  -> Clarification Provider / Grill Me 收敛
  -> Alignment Pack
  -> Human Alignment
  -> Automated Closure Loop
  -> D3A Specification
  -> API Contract Freeze
  -> Impact Analysis
  -> Coding Layer / DT Domain Planning
  -> Knowledge Gate
  -> Layer Context Packet
  -> Execution Unit <= 500 LOC
  -> DT RED
  -> Layer Coding
  -> DT GREEN
  -> tran_build
  -> Done
```

## V0 已完成资产

- `.claude/skills/idc-workflow/SKILL.md`：Claude Code 项目级总入口 skill。
- `.claude/commands/id-workflow.md`：统一 slash command 薄入口，只负责把用户输入交给 `idc-workflow`。
- `.claude/skills/`：只保留少量可独立调用的 `idc-*` skills；router、gate、lane、provider、completion、resume、evidence 等流程节点沉淀在 `references/`。
- `.claude/skills/idc-workflow/assets/README.md`：asset / reference 边界说明，避免把 passive data 伪装成 skill。
- `.claude/skills/idc-workflow/TEAM_CUSTOMIZATION.md`：其他团队接入时优先看的修改指南。
- `.claude/skills/idc-workflow/references/workflows/`：Scenario Router、Input Adapter、Lane Resolver、Contract Gate、Human Alignment、Automated Closure Loop 等运行时规则。
- `.claude/skills/idc-workflow/references/schemas/`：Alignment Pack、Escalation、Execution Unit、D3A Plan、General Plan 等机器 contract。
- `.claude/skills/idc-workflow/references/domains/`：Domain Module registry、D3A module、General module、团队模板 module。
- `.claude/skills/idc-workflow/references/registries/`：固定 D3A Layer、DT Domain、General placeholder taxonomy、Skill Adapter registry；企业接入方只读，通过 team-config 非空列表整体覆盖。
- `.claude/skills/idc-workflow/references/registries/team-adapter-bindings.template.yaml`：保留的兼容 binding 模板（已接 `team_adapter_binding_ref` 的老团队用）。
- `team-config.yaml.template`：推荐的新团队唯一入口配置，收敛 team id、repo path、skill bindings、knowledge refs、build commands、lane defaults，以及 DT domain / GC component / test domain 的整体替换列表。
- `QUICKSTART.md`：9 步快速上手文档。
- `.claude/skills/idc-workflow/references/lanes/`：fast / lite / complex 三种执行强度定义。
- `.claude/skills/idc-workflow/references/human-views/`：给用户看的中文 Brainstorming / Clarification / Alignment / Completion / Escalation 模板。
- `.claude/skills/idc-workflow/references/constraints/`：decision / planning / execution 三段式约束。
- `.claude/skills/idc-workflow/references/knowledge/`：D3A Layer、DT Domain、General placeholder knowledge 模板。
- `.claude/skills/idc-brainstorming/SKILL.md`：仅用于模糊想法的发散和多方案探索原子 skill。
- `.claude/skills/idc-intent-discovery/SKILL.md`：IDC 内把模糊想法接入 draft spec 的原子 skill。
- `.claude/skills/idc-intent-grilling/SKILL.md`：Grill Me 收敛追问的原子 skill。
- `.claude/skills/idc-intent-grilling-with-docs/SKILL.md`：需要沉淀非敏感决策文档时使用的 Grill With Docs skill。
- `.claude/skills/idc-intent-alignment/SKILL.md`：人类前置确认的原子 skill。
- `.claude/skills/idc-general-coding/SKILL.md`：General Coding execution skill。
- `.claude/skills/idc-d3a-coding/SKILL.md`：D3A Coding execution skill。
- `.claude/skills/idc-gc-sop-adapter/SKILL.md`：企业 GC 全家桶 SOP 的外部 adapter placeholder。
- `.claude/skills/idc-dt-design/SKILL.md`：原代码仓 DT design skill 的外部 adapter。
- `.claude/skills/idc-dt-writer/SKILL.md`：原代码仓 DT writer skill 的外部 adapter。
- `.claude/skills/idc-gc-third-skill-placeholder/SKILL.md`：第三个原仓 skill 的显式 placeholder。
- `.claude/skills/idc-dt-build/SKILL.md`：DT build / run evidence 接口 skill。
- `.claude/skills/idc-tran-build/SKILL.md`：`tran_build` evidence 接口 skill。
- `.claude/agents/`：Claude Code 项目级 subagent 定义。
- `docs/domain-module-contract.md`：团队接入自己的 Domain Module 时遵循的契约。
- `docs/adoption-guide.md`：其他团队复制 SOP 的指南。
- `.claude/skills/idc-workflow/CONTEXT_ENGINEERING.md`：Claude Code 渐进式上下文加载策略。
- `.claude/skills/idc-workflow/references/workflows/resume-policy.md`：保密区中断后的 checkpoint 恢复策略。
- `.claude/skills/idc-workflow/references/schemas/runtime-state.schema.yaml`：可恢复运行状态 schema。
- `docs/agent-team-architecture.md`：Main agent 只做 planning / delegation 的 agent team 架构。
- `docs/source-attribution.md`：公开方法论来源和 license attribution。
- `docs/atomic-skills.md`：可复用原子 skill 列表和边界。
- `docs/architecture-diagram.md`：Core + Domain Module 架构图。
- `docs/user-input-routing-overview.html`：从不同用户输入开始的 Discovery-first 整体分流图。
- `docs/intake-discovery-trigger-flow.html`：Discovery 到 Alignment 的左到右触发条件图。
- `docs/flow-d3a-general.html`：D3A / General 双路径可视化 HTML。
- `docs/context-runtime-view.html`：TR3 / 一句话输入下的上下文运行视角 HTML。
- `docs/confidential-migration-checklist.md`：进入保密区前后的 checklist。
- `docs/terminology.md`：中英文术语保留规则。
- `examples/mock-d3a-task/`：非敏感 mock walkthrough。
- `examples/e2e-tr3-d3a/`：从 TR3 到 completion summary 的端到端 mock demo。
- `examples/e2e-general-task/`：General Coding 端到端 mock demo。
- `test/`：可以复制到 Claude Code 里手动体验的场景卡。
- `examples/tr3-fixtures.yaml`：TR3 输入分类样例。
- `tests/test_harness.py`：harness 自检。

## 验证方式

```sh
python3 tests/test_harness.py
```

当前测试覆盖：

- D3A Layer registry 不能漂移。
- DT Domain registry 不能漂移。
- Registry 指向的 knowledge 模板必须存在。
- Planner 不能产生 registry 外的 Layer / DT Domain。
- Domain Module registry 指向的 module 文件必须存在。
- Active module 必须声明 route、registries、workflow、knowledge、execution。
- General module 必须 active，且不依赖 D3A Layer / DT Domain registry。
- Lane registry 指向的 lane 文件必须存在。
- 每个 Lane 都必须声明 completion requirements。
- Lane Resolver fixture 必须稳定产出 fast / lite / complex。
- TR3 fixture 必须稳定识别 D3A、新增需求、霰弹式修改和 lane signals。
- Alignment Pack schema 必须存在。
- Escalation Policy schema 必须存在。
- 每个 execution unit 的 max_change_loc 必须是 500。
- Repo Context Provider 必须限制 max_results / max_snippet_chars，并要求 evidence_ref。
- Provider Selection Matrix 必须明确有锚点 grep first、无锚点但有领域语义 OKL first。
- Context Engineering 必须存在，并且 `idc-workflow` 必须显式加载。
- Runtime State / Resume Policy 必须存在，保密区中断后能从 checkpoint 恢复。
- Progressive Constraint Loading 三段约束文件必须存在。
- E2E TR3 D3A demo 必须包含完整链路文件。
- E2E General Coding demo 必须包含完整链路文件。
- Human View 模板必须存在，避免把完整 YAML 直接作为用户主界面。
- Atomic Skills 必须存在，并且 `idc-workflow` 只做编排。
- Discovery Provider 必须以 Superpowers Brainstorming 为 baseline，并且 TR3 默认跳过 Discovery。
- Clarification Provider 必须支持 Grill Me method、frontier round 和 builtin fallback。
- Requirement Assessor 作为 Human Alignment Check 的被动检查表，能识别关键字段缺失。
- Layer Context Packet 只能包含当前 Layer。
- 没有 RED evidence 不能进入 GREEN。
- 未通过全部 DT 不能进入 `ALL_LAYERS_GREEN`。
- `tran_build` 未 PASS 不能进入 `DONE`。
- Placeholder 不应被自动替换成猜测内容。

## 保密区内需要完成的内容

只能在公司保密区填写：

- 真实 Layer 职责 / 边界。
- 真实 API rules、data structure、error semantics。
- 真实 Coding Layer 到 DT Domain 的 verification mapping。
- 真实 DT build / run 命令。
- 真实 `tran_build` 命令和环境。
- 真实 repo path、CodeGraph、Wiki、build error pattern。

外部环境只维护非敏感工作流骨架。
