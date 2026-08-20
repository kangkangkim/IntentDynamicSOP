# Intent Dynamic Code

Intent Dynamic Code 是一个非敏感的企业 Coding 工作流骨架。

它的目标不是在外部环境实现真实企业 D3A，而是先把一套可迁移、可验证、可填充的工作流骨架准备好。进入公司保密区后，只填 `team-config.yaml` 一个文件即可接入真实知识、skills 和构建能力（命令封装在 build skill 内部）。

## 项目优势

IDC 的核心优势是把动态智能分流和企业固定 SOP 分开：外层可以根据输入动态判断，内层可以保护团队已经验证过的固定流程。

- **公共框架可复用**：`IDC Core` 只保存 `idc-workflow` 统一 skill 入口、`idc-*` skills、router、lane、gate、schema、human views 和 adapter eligibility registry，不保存企业 secret。
- **企业知识不外泄**：真实 D3A 知识、GC SOP 原子能力、repo path、内部 skill 名（构建命令封装在 build skill 内部）都通过保密区 `team-config.yaml` / knowledge index 接入。
- **D3A 主流程固定**：D3A 是用户设计的固定 workflow，Lane 对它不适用，并跳过通用 Lane Resolver。IDC 只在固定流程内选择 Layer、DT Domain、adapter、execution unit 和 evidence，不重排 D3A。
- **Human Alignment 管检测**：Discovery 只做 intake / normalize / signal；Human Alignment Check 统一检测 readiness、critical gap、docs needed、approval validity 和 scope drift。
- **GC SOP 可配置且真正生效**：绑定只表示能力可用。每个 Lane 可独立配置 Skill allow/deny/required 集合与 stage 编排；Capability Selector 执行这些策略并记录顺序、选用与跳过原因。
- **Evidence-first 完成标准**：API Contract 先于 implementation；RED evidence 先于 GREEN evidence；D3A DONE 必须满足 required DT GREEN 和 `tran_build PASS`。
- **多团队单配置接入**：其他团队复用 IDC Core，只维护 `team-config.yaml`；Custom Domain 和新 GC atoms 也由 Resolver 动态注册。
- **运行时自动生效**：`idc-workflow` 每次入口自动执行 preflight，原子重建 effective config 并校验源 YAML digest；团队不维护生成文件，也不会误用旧配置。
- **执行不可绕过**：所有 repository mutation 都必须经过 Execution Authorization 并真实派发 executor。General Coding 是外层执行协议，GC Adapter 只是 executor 内按需调用的原子能力；main agent 不能直接实现后再补证据。
- **Skill 注册冲突可检测**：Preflight 检查 capability、stage、Lane/profile 与 trigger 的重叠；未声明的冲突直接阻断，有意组合或替换必须显式使用 `composes_with` / `supersedes`。

## V0 定位

V0 不是完整企业 D3A 实现，而是可进入保密区落地的最小成熟框架。

V0 已经固定：

- 统一入口：`idc-workflow` skill（显式调用为 `$idc-workflow`，也支持自然语言自动匹配）。
- 能力实现：所有可执行能力都沉淀为 `.claude/skills/idc-*/SKILL.md`，不维护 `.claude/commands`。
- 三条顶层路径：Dynamic Scenario Coding、Domain Module Coding、General Coding Fallback。
- 三种 Lane：`fast`、`lite`、`complex`。
- D3A 固定 Coding Layer：`TRAN_CFG`、`DO`、`VISP_ADP`、`TFC_TFI`、`TFE`、`ADP`、`DRV`。
- D3A 不参与 Lane 分类：输出 `lane_applicability: not_applicable`，由 `d3a_fixed_workflow` 接管。
- V0 DT Domain placeholder：`TPRINT`、`FW`、`DPF`。
- Human Alignment Check 作为 readiness / gap / approval gate。
- Skill Adapter Router 作为 GC SOP、Superpowers、DT skill、build skill 的唯一接入门。
- `team-config.yaml.template` 是唯一团队配置入口；`idc-team-config` 校验并生成只读有效配置。
- Fast / Lite / Complex 使用各自的 capability profile。团队既可让 Selector 自主补齐最小充分集合，也可用 ordered steps 固定过程；无匹配步骤时明确阻断，不静默回退。
- Mock D3A / General E2E examples 和 harness tests。

V0 不做：不复制企业内部 D3A 知识；不编造 Coding Layer 到 DT Domain 的真实 mapping；不内置真实 repo path、构建命令、日志、API 或企业 skill 名；不把 GC SOP 十几个能力全部默认打开；不让模型重新设计 D3A 主流程。

进入企业内部后，优先补的是索引和 binding，而不是把企业知识搬进 public harness：

```text
真实 D3A 知识地址
+ 真实 GC SOP atom mapping
+ 原代码仓 dt-design / dt-writer skill ref
+ 真实 DT / tran_build build skill
+ repo context provider
+ evidence parser
```

第一阶段目标是跑通一条最小 D3A vertical slice：1 个 Layer、1 个 DT Domain、1 条 verification mapping、1 组 repo context provider、RED evidence、GREEN evidence、`tran_build PASS` 和 Completion Summary。

## 多团队复用模型

IDC 的整体能力面向多个团队复用。公共仓库只维护稳定框架和非敏感 contract；团队差异通过轻量 DIY 层接入。

```text
IDC Core
  共享：idc-workflow skill、router、lane、gate、schema、human views、adapter eligibility registry
  不放：真实团队路径、命令、内部 skill 名、日志、企业 API

Team Config
  团队唯一 DIY：team-config.yaml
  包含：内置/Custom Domain、layer/test registry、skill bindings、adapter extensions、knowledge refs

Generated Runtime
  框架生成：.idc/effective-team-config.yaml
  只读，不是第二配置入口
```

推荐复用方式：

1. 多团队共享 `IDC Core`，不要 fork 出不同 core。
2. 新领域填写 `domain.mode: custom` 和内联 `domain.custom`，不要改共享 Domain registry。
3. 真实路径、内部 skill 和 knowledge index 只写在团队自己的 `team-config.yaml`；命令留在 Skill 内。
4. Pre-alignment 同理：公司已有 Brainstorming 时通过 Team Binding 复用；公司没有 Grill Me 时，直接使用本仓库提供的 `idc-intent-grilling` 系列。

## 顶层路径

- **Dynamic Scenario Coding**：不绑定固定领域模块，按复杂度、不确定性、风险和可测试性动态编排。
- **Domain Module Coding**：通过可插拔 Domain Module 进入领域工作流。D3A 是当前第一个自定义 active module。
- **General Coding Fallback**：保留给简单普通 coding 任务。

Domain Module 决定领域差异和 required contracts；Lane（`fast / lite / complex`）只决定流程跑多重。整体执行哲学：前置对齐、后置自动闭环、异常再回人。

## 快速开始

```sh
cp team-config.yaml.template team-config.yaml   # 保密区内填写
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb --config team-config.yaml --check
python3 tests/test_harness.py
```

九步操作见 `QUICKSTART.md`；企业接入全流程见 `docs/confidential-migration-checklist.md`。

## 文档导览

| 文档 | 看什么 |
|---|---|
| `QUICKSTART.md` | 从复制仓库到第一条 vertical slice 的 9 步操作。 |
| `docs/architecture.md` | 架构正本：分流、Domain Module、gate、知识系统、保密边界、架构图与命名约定。 |
| `docs/adoption-guide.md` | 其他团队如何复制 SOP：Core/Module 边界、复制原则、第一周落地。 |
| `docs/confidential-migration-checklist.md` | 入区前后 checklist：填什么、先跑哪条 slice、失败闭环。 |
| `docs/atomic-skills.md` | 哪些能力已拆成可复用原子 skill 及编排顺序。 |
| `docs/skillization-boundary.md` | 哪些内容应该 skill 化，哪些应保持 reference。 |
| `docs/agent-team-architecture.md` | Main agent 只做 planning / delegation 的 agent team 架构。 |
| `docs/source-attribution.md` | 公开方法论来源和 license attribution。 |
| `docs/deep-dive/` | Lane、约束加载、repo context、TR3 输入的专题深入。 |
| `docs/enterprise-adoption-map.html` | 企业资产 ↔ team-config 插槽逐项匹配图 + 入区五步。 |
| `docs/team-config-generator.html` | 交互式表单：填完即生成、即校验 `team-config.yaml`，可复制/下载。 |
| `docs/team-rollout-playbook.md` | 面向多团队推广的最小配置、路径规则、接入层级和验收清单。 |
| `docs/*.html`（其余 4 个） | 输入分流、Discovery 触发、D3A/General 双路径、上下文运行视角的可视化。 |
| `.claude/skills/idc-workflow/TEAM_CUSTOMIZATION.md` | 团队接入时优先看的定制指南。 |
| `.claude/skills/idc-workflow/CONTEXT_ENGINEERING.md` | 渐进式上下文加载策略；preflight 与 `plan_context.rb` 按阶段生成最小 `required_refs`。 |

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

D3A 不是 IDC Core 本体，而是一个可插拔 Domain Module（`references/domains/d3a/module.yaml`）。它与 General Coding 共享 `Planner -> Knowledge Preparation -> Execution Unit Split -> TDD -> Completion` 骨架，但 D3A 的 Layer、DT mapping、knowledge requirements 和 completion gate 由企业固定 SOP 约束：

```text
用户任务 -> Scenario Router -> Discovery / Grill Me -> Domain Module Router
  -> d3a module -> D3A Fixed Workflow (Lane N/A) -> Contract Gate -> Human Alignment
  -> Alignment Pack -> Automated Closure Loop -> D3A Specification
  -> API Contract Freeze -> Planner (Layer / DT / DAG / Knowledge Requirements)
  -> Knowledge Gate -> Knowledge Preparation
  -> Layer Context Packet per Layer -> Execution Unit <= 500 LOC
  -> Per-Layer TDD (DT RED -> Layer Coding -> DT GREEN)
  -> tran_build -> Done
```

完整分层与图示见 `docs/architecture.md` 的 D3A Module 与架构图章节。

## 关键资产

- `.claude/skills/idc-workflow/SKILL.md`：统一用户入口与编排 skill；无需额外 command alias。
- `.claude/skills/`：少量可独立调用的 `idc-*` skills（清单见 `docs/atomic-skills.md`）；router、gate、lane、provider、completion、resume、evidence 等流程节点沉淀在 `references/`。
- `.claude/skills/idc-workflow/assets/README.md`：asset / reference 边界说明。
- `.claude/skills/idc-workflow/references/registries/`：固定 D3A Layer、DT Domain、General placeholder taxonomy、Skill Adapter registry；企业接入方只读，通过 team-config 非空列表整体覆盖。
- `.claude/skills/idc-team-config/`：单配置校验、有效配置生成和 Capability Selector 可执行实现。
- `team-config.yaml.template`：唯一团队入口，收敛 Domain、registries、skill bindings、adapter extensions、knowledge、Lane capability profile 和自优化策略。
- `.claude/agents/`：`d3a-layer-coder`、`dt-test-writer`、`build-error-analyzer`、`general-coder` subagent 定义。
- `examples/`：mock D3A、E2E TR3 D3A、E2E General 三个非敏感 walkthrough。
- `test/`：可复制到 Claude Code 手动体验的场景卡。
- `tests/test_harness.py`：harness 自检。

## 验证方式

```sh
python3 tests/test_harness.py
```

测试覆盖：registry 固定性（D3A Layer / DT Domain 不漂移）、planner 不越界、contract / lane / provider / context 约束、RED→GREEN→`tran_build` 状态门、Runtime State / Resume Policy、placeholder hygiene、team-config 覆盖规则与填写校验。

## 保密区迁移

真实 Layer 职责、verification mapping、DT / `tran_build` build skill、repo path 等只能在公司保密区填写，且只写进 `team-config.yaml`（知识正文留在企业本地）。完整 checklist 见 `docs/confidential-migration-checklist.md`。
