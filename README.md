# Intent Dynamic Code

Intent Dynamic Code 是一个非敏感的企业 Coding 工作流骨架。

它的目标不是在外部环境实现真实企业 D3A，而是先把一套可迁移、可验证、可填充的工作流骨架准备好。进入公司保密区后，再把真实代码知识、测试知识和构建命令绑定进去。

## 两条顶层路径

- **Domain Module Coding**：通过可插拔 Domain Module 进入领域工作流。D3A 是当前第一个 active module。
- **General Coding**：预留给非 D3A 的普通开发任务，未来根据复杂度、不确定性、风险和可测试性动态编排。

同时，执行强度由 Lane 决定：

```text
fast / lite / complex
```

Domain Module 决定领域差异和 required contracts；Lane 只决定流程跑多重。

整体执行哲学：

```text
前置对齐
后置自动闭环
异常再回人
```

V0 重点完成 D3A workflow 结构、contract、subagent prompt、skill 接口、mock demo 和确定性的验证 gate。

## 怎么看这个仓库

优先看这三个入口：

```text
README.md
  -> docs/architecture.md
  -> docs/adoption-guide.md
```

- `README.md`：看当前完成了什么、目录怎么组织、怎么验证。
- `docs/architecture.md`：看整体架构和 D3A / General Coding 的关系。
- `docs/adoption-guide.md`：看其他团队如何复制 SOP。
- `docs/atomic-skills.md`：看哪些能力已经拆成可复用原子 skill。
- `docs/architecture-diagram.md`：看 Core + Domain Module 的架构图。
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
├── AGENTS.md
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
.claude/skills/id-workflow/references/.claude/skills/id-workflow/references/domains/d3a/module.yaml
```

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

- `.claude/skills/id-workflow/SKILL.md`：Claude Code 项目级总入口 skill。
- `.claude/skills/id-workflow/TEAM_CUSTOMIZATION.md`：其他团队接入时优先看的修改指南。
- `.claude/skills/id-workflow/references/workflows/`：Scenario Router、Input Adapter、Lane Resolver、Contract Gate、Human Alignment、Automated Closure Loop 等运行时规则。
- `.claude/skills/id-workflow/references/schemas/`：Alignment Pack、Escalation、Execution Unit、D3A Plan、General Plan 等机器 contract。
- `.claude/skills/id-workflow/references/domains/`：Domain Module registry、D3A module、General module、团队模板 module。
- `.claude/skills/id-workflow/references/registries/`：固定 D3A Layer、DT Domain、General placeholder taxonomy。
- `.claude/skills/id-workflow/references/lanes/`：fast / lite / complex 三种执行强度定义。
- `.claude/skills/id-workflow/references/human-views/`：给用户看的中文 Brainstorming / Clarification / Alignment / Completion / Escalation 模板。
- `.claude/skills/id-workflow/references/constraints/`：decision / planning / execution 三段式约束。
- `.claude/skills/id-workflow/references/knowledge/`：D3A Layer、DT Domain、General placeholder knowledge 模板。
- `.claude/skills/brainstorming/SKILL.md`：仅用于模糊想法的发散和多方案探索原子 skill。
- `.claude/skills/intent-discovery/SKILL.md`：IDC 内把模糊想法接入 draft spec 的原子 skill。
- `.claude/skills/intent-grilling/SKILL.md`：Grill Me 收敛追问的原子 skill。
- `.claude/skills/intent-alignment/SKILL.md`：人类前置确认的原子 skill。
- `.claude/skills/general-coding/SKILL.md`：General Coding execution skill。
- `.claude/skills/d3a-coding/SKILL.md`：D3A Coding execution skill。
- `.claude/skills/dt-build/SKILL.md`：DT build / run evidence 接口 skill。
- `.claude/skills/tran-build/SKILL.md`：`tran_build` evidence 接口 skill。
- `.claude/agents/`：Claude Code 项目级 subagent 定义。
- `docs/domain-module-contract.md`：团队接入自己的 Domain Module 时遵循的契约。
- `docs/adoption-guide.md`：其他团队复制 SOP 的指南。
- `.claude/skills/id-workflow/CONTEXT_ENGINEERING.md`：Claude Code 渐进式上下文加载策略。
- `docs/agent-team-architecture.md`：Main agent 只做 planning / delegation 的 agent team 架构。
- `docs/source-attribution.md`：公开方法论来源和 license attribution。
- `docs/atomic-skills.md`：可复用原子 skill 列表和边界。
- `docs/architecture-diagram.md`：Core + Domain Module 架构图。
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
- Context Engineering 必须存在，并且 `id-workflow` 必须显式加载。
- Progressive Constraint Loading 三段约束文件必须存在。
- E2E TR3 D3A demo 必须包含完整链路文件。
- E2E General Coding demo 必须包含完整链路文件。
- Human View 模板必须存在，避免把完整 YAML 直接作为用户主界面。
- Atomic Skills 必须存在，并且 `id-workflow` 只做编排。
- Discovery Provider 必须以 Superpowers Brainstorming 为 baseline，并且 TR3 默认跳过 Discovery。
- Clarification Provider 必须支持 Grill Me method、frontier round 和 builtin fallback。
- Requirement Assessor 能识别关键字段缺失。
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
