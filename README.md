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
├── agents/
├── domains/
├── docs/
├── examples/
├── constraints/
├── human-views/
├── knowledge/
├── lanes/
├── registries/
├── schemas/
├── skills/
├── tests/
└── workflows/
```

## D3A 核心流程

D3A 不是 IDC Core 本体，而是一个可插拔 Domain Module：

```text
domains/d3a/module.yaml
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

- `workflows/scenario-router.md`：顶层场景路由。
- `skills/id-workflow/SKILL.md`：ID workflow 的 Skill 触发入口。
- `skills/intent-discovery/SKILL.md`：一句话需求发散成 draft spec 的原子 skill。
- `skills/intent-grilling/SKILL.md`：Grill Me 收敛追问的原子 skill。
- `skills/intent-alignment/SKILL.md`：人类前置确认的原子 skill。
- `workflows/input-adapter.md`：支持一句话输入和 TR3 设计文档输入。
- `workflows/discovery-provider.md`：以 Superpowers Brainstorming 为 upstream baseline，把 raw idea 展开成 draft spec。
- `workflows/domain-module-router.md`：根据 `domains/registry.yaml` 选择可插拔 module。
- `workflows/progressive-constraint-loading.md`：三段式约束加载。
- `workflows/provider-selection-matrix.md`：根据 anchor / domain / lane 选择 grep、CodeGraph、OKL。
- `workflows/repo-context-providers.md`：grep / CodeGraph / OKL 统一 provider contract。
- `workflows/lane-resolver.md`：用 hard trigger / Fast 准入 / 默认 Lite 判断执行强度。
- `workflows/lane-completion.md`：定义每个 Lane 的最小自闭环要求。
- `workflows/contract-gate.md`：根据 Domain + Lane 决定 contract set。
- `workflows/human-alignment.md`：前置人工对齐点。
- `workflows/clarification-provider.md`：吸收 Grill Me 方法论的澄清 provider。
- `workflows/automated-closure-loop.md`：对齐通过后的自动闭环。
- `workflows/execution-unit-policy.md`：每个阶段代码变更控制在 500 行以内。
- `workflows/requirement-assessor.md`：需求清晰度判断规则。
- `workflows/d3a-workflow.md`：D3A 固定骨架和动态规划点。
- `workflows/tdd-state-machine.md`：RED / GREEN / completion gate。
- `human-views/`：给用户看的中文 Brainstorming / Clarification / Alignment / Completion / Escalation 卡片模板。
- `docs/domain-module-contract.md`：团队接入自己的 Domain Module 时遵循的契约。
- `docs/adoption-guide.md`：其他团队复制 SOP 的指南。
- `docs/token-budget-policy.md`：保密区 token / provider 限额策略。
- `docs/source-attribution.md`：公开方法论来源和 license attribution。
- `docs/atomic-skills.md`：可复用原子 skill 列表和边界。
- `docs/architecture-diagram.md`：Core + Domain Module 架构图。
- `docs/confidential-migration-checklist.md`：进入保密区前后的 checklist。
- `docs/terminology.md`：中英文术语保留规则。
- `domains/`：Domain Module 注册表、D3A module、团队模板 module。
- `constraints/`：decision / planning / execution 三段式约束。
- `lanes/`：fast / lite / complex 三种执行强度定义。
- `knowledge/`：D3A Layer 和 DT Domain 的保密区填充模板。
- `registries/`：固定 D3A Layer 和 V0 DT Domain registry。
- `schemas/`：核心 contract 结构。
- `agents/`：subagent 职责边界。
- `skills/`：placeholder skill 接口。
- `skills/id-workflow/`：本机 Claude Code / Codex 体验 ID workflow 的入口 skill。
- `examples/mock-d3a-task/`：非敏感 mock walkthrough。
- `examples/e2e-tr3-d3a/`：从 TR3 到 completion summary 的端到端 mock demo。
- `examples/tr3-fixtures.yaml`：TR3 输入分类样例。
- `schemas/normalized-request.schema.yaml`：Input Adapter 的统一输出结构。
- `schemas/alignment-pack.schema.yaml`：Human Alignment 使用的对齐包。
- `schemas/escalation-policy.schema.yaml`：异常回流规则。
- `schemas/execution-unit.schema.yaml`：Execution Unit 和 500 行拆分规则。
- `schemas/repo-context-provider.schema.yaml`：grep / CodeGraph / OKL provider 统一接口。
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
- Lane registry 指向的 lane 文件必须存在。
- 每个 Lane 都必须声明 completion requirements。
- Lane Resolver fixture 必须稳定产出 fast / lite / complex。
- TR3 fixture 必须稳定识别 D3A、新增需求、霰弹式修改和 lane signals。
- Alignment Pack schema 必须存在。
- Escalation Policy schema 必须存在。
- 每个 execution unit 的 max_change_loc 必须是 500。
- Repo Context Provider 必须限制 max_results / max_snippet_chars，并要求 evidence_ref。
- Provider Selection Matrix 必须明确有锚点 grep first、无锚点但有领域语义 OKL first。
- Token Budget Policy 必须存在。
- Progressive Constraint Loading 三段约束文件必须存在。
- E2E TR3 D3A demo 必须包含完整链路文件。
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
