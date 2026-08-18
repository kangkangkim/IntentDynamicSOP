# Atomic Skills

Atomic Skill 是可以被其他团队单独复用的小能力。

它必须满足：

- 有独立输入和输出。
- 不绑定 D3A 私有知识。
- 不依赖真实企业路径、命令或 secret。
- 能被 `idc-workflow` 编排，也能被其他 workflow 单独调用。
- 有明确 handoff 条件。

## 第一批

### 框架级原子 skill

这些 skill 负责动态分流、门禁和 handoff：

```text
idc-input-adapter
idc-scenario-router
idc-domain-module-router
idc-lane-resolver
idc-contract-gate
idc-requirement-assessor
idc-output-surface-router
idc-automated-closure
idc-execution-unit-planner
idc-progressive-constraint-loader
idc-delegation-router
idc-skill-adapter-router
idc-knowledge-gate
idc-provider-selection
idc-repo-context-provider
idc-tdd-state-machine
idc-lane-completion
idc-evidence-gate
idc-vertical-slice-readiness
idc-resume-run
```

它们的共同边界：

```text
主动决策 / 路由 / 门禁 / handoff 可以 skill 化
schema / registry / human-view / evidence / knowledge template 不 skill 化
```

### brainstorming

```text
raw_idea -> approaches + draft_spec
```

仅用于模糊想法、raw idea 和早期产品方向。

短需求不等于模糊需求；如果一句话已经包含目标、行为和验收线索，应跳过 `brainstorming`，进入 Grill Me / Alignment。

这是可直接复用的发散原子能力，吸收 Superpowers Brainstorming 方法论，先探索 2-3 个方向，再产出 draft spec。

### idc-intent-discovery

```text
raw_idea -> draft_spec
```

用于 IDC workflow 内的模糊想法。

它是 `brainstorming` 的 IDC wrapper，负责把发散结果接入 normalized request、Grill Me 和 Alignment。

### idc-intent-grilling

```text
draft_spec / structured_requirement / tr3_design_doc -> clarification answers
```

用于 contract、scope、completion gate 进入 Alignment 前的关键追问。

吸收 Grill Me 方法论，按 decision tree 和 frontier round 收敛。

Skill package shape:

```text
.claude/skills/idc-intent-grilling/SKILL.md
.claude/skills/idc-intent-grilling/references/grill-me-method.md
.claude/skills/idc-intent-grilling/assets/question-card-template.md
```

### idc-intent-alignment

```text
machine contract -> human approval
```

用于把 Alignment Pack 渲染成中文 Alignment View，并等待用户 approve。

### superpowers-adapter

```text
approved_alignment + bounded execution units -> Superpowers-style engineering loop
```

用于 Human Alignment 之后，把 Superpowers 的 planning、TDD、subagent development、systematic debugging、code review、verification-before-completion 和 finish branch 思路接入 IDC。

它不是外层 workflow owner：

```text
IDC Harness 决定 Domain / Lane / Contract / Completion Gate
superpowers-adapter 只提供 approved 后的执行纪律
```

### gc-sop-adapter

```text
approved_alignment + selected GC atom -> confidential GC SOP handoff
```

用于在企业内部复用 GC 全家桶 SOP 的原子能力。

外部仓库只保留 adapter contract，不包含真实 GC SOP prompt、命令、路径、日志或内部规则。

### dt-design

```text
verification_contract + selected DT domain -> DT design artifact
```

原代码仓 DT design skill 的外部 adapter。它可以设计 DT，但 DT design 本身不是 RED / GREEN evidence。

### dt-writer

```text
dt_design_ref + allowed paths -> DT changes + RED/GREEN evidence refs
```

原代码仓 DT writer skill 的外部 adapter。它可以写 DT 并返回 evidence refs，但不能标记 IDC DONE。

### gc-third-skill-placeholder

```text
<ENTERPRISE_GC_THIRD_SKILL_NAME> -> placeholder adapter
```

第三个原代码仓 skill 尚未命名，外部 harness 只保留占位，不能执行、不能猜用途。

## 编排关系

```text
idc-workflow
  -> brainstorming
  -> idc-intent-discovery
  -> idc-intent-grilling
  -> idc-intent-alignment
  -> superpowers-adapter
  -> gc-sop-adapter
  -> dt-design / dt-writer / gc-third-skill-placeholder
  -> automated closure loop
```

## 不属于第一批

D3A 不拆成通用 atomic skill。

D3A 是 Domain Module：

```text
.claude/skills/idc-workflow/references/domains/d3a/module.yaml
.claude/skills/d3a-coding/SKILL.md
```

它可以复用 atomic skills，但自身保留领域边界。
