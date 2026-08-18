# 架构说明

Intent Dynamic Code 把稳定的工作流机制和保密的企业 domain binding 分开。

一句话：

```text
外部做通用 harness，保密区填真实企业知识。
```

## 总体分层

```text
Scenario Router
  -> Domain Module Router
  -> Lane Resolver
  -> Contract Gate
  -> Dynamic Scenario Workflow
  -> D3A Module
  -> Other Team Domain Module
  -> General Coding Fallback
  -> Skill Adapter Router

Engineering Control
  -> Requirement Assessor
  -> Specification
  -> API Contract
  -> TDD State Machine
  -> Verification Gates

Knowledge System
  -> Static Domain Knowledge
  -> Dynamic Repository Context

Execution Runtime
  -> Claude Code / Codex / other coding runtime
  -> Agents / Subagents / Skills / Scripts
```

## 顶层思路

整个系统不是一个单一 Agent，而是一套动态分流的 Intent-Driven Coding 框架：

```text
用户 Intent
  -> Input Adapter / Intake
  -> Intake Trigger Flow
  -> 场景识别
  -> 需求清晰度判断
  -> 选择 Dynamic Scenario / Domain Module / General Coding fallback
  -> 选择执行强度 Lane
  -> 根据 Domain + Lane 决定 contract set
  -> 前置 Human Alignment
  -> 动态工作流 / domain planning
  -> 知识加载
  -> subagent 执行
  -> TDD / build verification
```

整体用户输入分流图和 Intake Trigger Flow 见：

```text
docs/user-input-routing-overview.html
docs/intake-discovery-trigger-flow.html
```

## 可插拔 Domain Module

IDC Core 不直接绑定 D3A。它只认识 Domain Module Contract。

```text
IDC Core
  -> .claude/skills/idc-workflow/references/domains/registry.yaml
  -> domains/<domain>/module.yaml
  -> module.workflow.entrypoint
```

一个 Domain Module 至少定义：

- route id。
- required contracts。
- coding layer registry。
- test domain registry。
- workflow entrypoint。
- planner schema。
- knowledge root。
- agents / skills。
- completion gate。

D3A 是当前第一个 active module：

```text
.claude/skills/idc-workflow/references/domains/d3a/module.yaml
```

其他团队接入时新增：

```text
.claude/skills/idc-workflow/references/domains/<team-domain>/module.yaml
```

并在 `.claude/skills/idc-workflow/references/domains/registry.yaml` 注册。

## Input Adapter

用户输入可以是一句话，也可以是 TR3 设计文档。

Input Adapter 负责把不同输入形态统一成：

```text
normalized_request
```

TR3 输入会额外抽取：

- 开发需求描述。
- API / 行为语义。
- DT 设计。
- 验收标准。
- 影响范围。
- domain candidates。
- change type。
- change shape。
- lane signals。

TR3 可以帮助判断新增需求、霰弹式修改和 D3A 需求，但 TR3 不是 completion evidence。

## Lane Resolver

Lane 只表示执行强度，不表示领域。

V0 只有三种 Lane，且只允许这三种输出：

```text
fast
lite
complex
```

不设置 `known-domain`、`d3a`、`gc`、`dynamic` 或 `unknown` lane。
这些概念分别由 Domain Module Router、Scenario Router 或 Skill Adapter Router 表达。

判断规则：

- 命中 Complex hard trigger，直接进入 `complex`。
- 只有 Fast required conditions 全部满足，才允许 `fast`。
- 其他情况默认 `lite`。

这样可以避免只靠模型主观判断复杂度。

## Contract Gate

Contract Gate 根据 `Domain Module + Lane + Task Type` 决定需要哪些 contract。

API Contract 不是全局强制项。

例如：

- Fast 文档类任务：Task Summary + Acceptance Criteria。
- Lite 通用开发：Task Contract + Focused Verification。
- Complex 通用开发：Task Contract + Detailed Plan + Verification Contract。
- D3A Module：D3A Specification + API Contract + Task Contract + Verification Contract。

## Skill Adapter Router

Skill Adapter Router 不靠名字猜测是否使用 GC / DT / Superpowers。

它读取：

```text
.claude/skills/idc-workflow/references/registries/skill-adapters.yaml
```

然后根据 `requested_capability_keys`、`selected_stage`、已有 contract refs、
confidential mapping refs 和阻断条件匹配 adapter。

如果没有 registry row 匹配，返回 `NEEDS_ADAPTER_MAPPING`，不能临时把某个
`idc-gc-*` 或 `idc-dt-*` skill 当作万能入口。

## Human Alignment

Human Alignment 是唯一默认人工对齐点。

设计哲学：

```text
前置对齐
后置自动闭环
异常再回人
```

Human Alignment 发生在 Planner 之前。

它确认：

- 输入理解。
- Domain / Lane 判断。
- change type / change shape。
- contract set。
- scope / boundary。
- completion gate。
- open questions。

它不确认具体实现细节。

如果信息不足，先进入 Grill Me / Clarification，补齐后再生成 Alignment Pack。

## Automated Closure Loop

Human Alignment approve 后，后续默认自动闭环：

```text
Planner
  -> Knowledge Gate
  -> Execution
  -> Verification
  -> Error Analyzer / Targeted Fix / Re-plan
  -> DONE
```

后续不再默认人工卡点。

只有命中 Escalation Policy 才回到 Human Alignment：

- 需要扩大 scope。
- 需要修改 API Contract。
- Planner 无法在 scope 内完成。
- 工具 evidence 缺失。
- 连续自动修复失败。
- Domain / Lane 需要重判。
- TR3 和 repo facts 冲突。
- Completion gate 无法满足。

## D3A Module

D3A 使用固定架构空间，但在这个固定空间内动态规划。

固定 Coding Layer：

```text
TRAN_CFG
DO
VISP_ADP
TFC_TFI
TFE
ADP
DRV
```

V0 DT Domain：

```text
TPRINT
FW
DPF
```

D3A 的动态性主要发生在：

- 本次任务涉及哪些 Coding Layer。
- 本次需要哪些 DT Domain。
- Layer 之间的 dependency DAG 怎么排。
- Coding Layer 和 DT Domain 如何形成 verification mapping。
- 哪些知识需要加载。
- 哪些 subagent 可以并行，哪些必须串行。

重要约束：

- D3A Planner 不能创建新的 D3A Layer。
- D3A Planner 不能删除已有 D3A Layer。
- Coding Layer 到 DT Domain 是多对多关系，不能在外部环境猜。
- 所有真实 mapping 必须进入保密区后填写。

## Dynamic Scenario Mode

Dynamic Scenario 用于没有固定 Domain Module、但仍需要按任务形态动态编排的场景。

它可以根据：

- 复杂度。
- 不确定性。
- 风险。
- 可测试性。
- 是否需要 GC SOP atomic ability。
- 是否需要 subagent / agent team / official dynamic workflow。

决定后续执行方式。

它不允许猜测 D3A Layer、DT Domain 或企业内部 GC SOP 细节。

## General Coding Fallback

General Coding 用于简单普通开发任务 fallback。

更复杂的非 D3A 任务优先进入 Dynamic Scenario Mode。

V0 只预留 assessment 维度：

- Complexity
- Uncertainty
- Risk
- Testability

未来 composer 可以根据这些维度决定：

- 是否需要 Grill Me。
- Specification 深度。
- TDD 深度。
- Context gathering 策略。
- Subagent 拆分策略。
- Review 和 final verification 强度。

## 三个关键角色

```text
Scenario Router
  -> 判断进入 Domain Module 还是 General Coding

Domain Module Router
  -> 判断选中哪个可插拔 module

Requirement Assessor
  -> 判断需求信息够不够

Domain / Dynamic Planner
  -> 判断这条路具体怎么走
```

Requirement Assessor 只负责 `Decide`，不负责澄清、设计、规划或写代码。

## 知识系统

Knowledge 分两类：

```text
Static Domain Knowledge
  -> Layer Knowledge
  -> DT Knowledge
  -> Architecture Rules

Dynamic Repository Context
  -> Grep
  -> CodeGraph
  -> Wiki
  -> Repository Search
```

V0 只定义接口和模板，不接真实企业 CodeGraph / Wiki。

## 保密边界

外部可以开发：

- 工作流状态机。
- Schema shape。
- Agent 职责边界。
- Mock examples。
- Placeholder skill 接口。
- Harness tests。

必须进入保密区开发：

- 真实 Domain Module 知识。
- 真实 D3A Layer / DT Domain 知识。
- 真实 build / run 命令。
- 真实 repo context provider。
- 真实 build error 到 Layer 的归因规则。
