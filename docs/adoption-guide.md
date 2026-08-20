# Adoption Guide

这份文档给其他团队复制 IDC SOP 使用。

核心原则：

```text
复制 IDC Core
只填写 team-config.yaml
Resolver 生成有效运行配置
不要改 D3A 或 Core
```

`idc-workflow` 每次启动都会自动运行 Resolver preflight。团队只提交自己的
`team-config.yaml`，不维护 `.idc/effective-team-config.yaml`。跨团队推广的最小
配置、`team://` 路径和验收矩阵见 `docs/team-rollout-playbook.md`。

## Core 和 Module 的边界

IDC Core 负责：Scenario Router、Requirement Assessor、Contract-first 规则、
Knowledge Gate、TDD State Machine、Verification Gate、Evidence-based
completion。

Domain Module 负责：自己的 route id、coding layer registry、test domain
registry、planner schema、workflow entrypoint、knowledge root、agents /
skills、completion gate。

D3A 不是 Core 的一部分，而是第一个 active Domain Module
（`references/domains/d3a/module.yaml`），引用固定 layer registry、DT
registry、workflow 与知识目录。

## 适合使用的团队

适合：

- 有固定领域架构。
- 有相对稳定的测试/构建闭环。
- 希望把需求澄清、规划、执行、验证标准化。
- 希望把领域 SOP 做成可插拔模块。

不适合：

- 没有稳定代码仓。
- 没有任何可运行测试或构建证据。
- 领域规则完全依赖口头经验且暂时无法沉淀。

## 新增 Domain Module

在 `team-config.yaml` 选择 `mode: custom`：

```text
domain:
  mode: custom
  custom:
    id: payment
    trigger_rules: []
    lane_policy: {mode: dynamic, selected_lane: null}
    coding_layers: []
    test_domains: []
    required_contracts: [task_contract, verification_contract]
    workflow_skill_ref: <TEAM_WORKFLOW_SKILL_REF>
    planner_skill_ref: <TEAM_PLANNER_SKILL_REF>
    completion_skill_ref: <TEAM_COMPLETION_SKILL_REF>
```

Resolver 会把这段配置生成为有效 Domain Module；团队不编辑共享 registry。

## 必须定义

每个团队必须定义：

- route trigger rules。
- lane policy：`dynamic` 使用 Lane Resolver；只有团队固定 SOP 才声明 `fixed + selected_lane`。
- layer registry。
- test domain registry。
- required contracts。
- planner schema。
- knowledge root。
- completion gate。
- repo context provider 接入方式。
- context loading boundary。
- 第一条 mock vertical slice。

## 复制原则

复用：Core workflow 思想、Contract-first、Knowledge Gate、TDD / build gate、
Evidence-based completion。

必须替换（接入团队全部通过 `team-config.yaml` 覆盖，不改共享文件）：

- Test domain registry（`domain.d3a.dt_domains` / `general.test_domains` / `general.components` 非空时整体替换，不合并）。
- Verification mapping（`knowledge.verification_mapping_ref`）。
- Knowledge refs（registry 条目的 `knowledge_ref`、`knowledge.layer_docs`）。
- Build / run skills（`bindings.*.skill_ref`；命令封装在 Skill 内）。
- Repo context provider（`knowledge.repo_context.provider_skill_ref`）。
- Mock example。

Custom Domain layer registry 填在 `domain.custom.coding_layers`；D3A 的 7 层
固定，不提供配置覆盖。

## 不要改

- 不要改 D3A module。
- 不要把团队领域写进 IDC Core。
- 不要让 Scenario Router 知道某个 module 的内部 layer。
- 不要把 test domain 和 coding layer 简化成一对一。
- 不要绕过 Human Alignment。
- 不要绕过 Lane Completion。
- 不要绕过 Evidence-based Completion。
- 不要绕过 API Contract 与 RED / GREEN evidence。

## 第一周落地建议

1. 复制 `team-config.yaml.template`。
2. 在 `domain.custom` 填 2-3 个 Layer。
3. 填 1-2 个 Test Domain placeholder。
4. 写一个 mock TR3。
5. 产出 Alignment Pack。
6. 产出一个 execution plan。
7. 绑定一个最小 repo context provider Skill。
8. 跑一个小闭环 demo。
9. 加 fixture 测试。

## 成功标准

第一条 vertical slice 成功即可：

```text
Input/TR3
  -> normalized_request
  -> domain/lane decision
  -> alignment_pack
  -> plan
  -> context_packet
  -> evidence
  -> completion_summary
```
