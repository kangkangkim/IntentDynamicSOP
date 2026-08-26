# Atomic Skills

## `idc-team-config`

Validates the single team-authored configuration, materializes the read-only
effective runtime config, and executes Lane/profile-aware Capability Selection.

## `idc-self-optimization`

Records bounded enterprise-adaptation events and generates replay-tested,
Human-Alignment-gated team-overlay proposals without modifying IDC Core.

Atomic Skill 是可以被其他团队单独复用的小能力。

它必须满足：

- 有独立输入和输出。
- 不绑定 D3A 私有知识。
- 不依赖真实企业路径、命令或企业私有细节。
- 能被 `idc-workflow` 编排，也能被其他 workflow 单独调用。
- 有明确 handoff 条件。

## 第一批

### 保留为 skill 的能力

这些 skill 有稳定输入/输出，能被 workflow 独立调用：

```text
idc-skill-adapter-router
idc-brainstorming
idc-intent-discovery
idc-intent-grilling
idc-intent-grilling-with-docs
idc-intent-alignment
idc-general-coding
idc-d3a-coding
idc-dt-build
idc-tran-build
idc-superpowers-adapter
idc-gc-sop-adapter
idc-dt-design
idc-dt-writer
idc-gc-third-skill-placeholder
```

### 降级为 references 的流程节点

这些是规则、决策表、schema 或 gate policy，不需要独立 skill：

```text
input-adapter
scenario-router
domain-module-router
lane-resolver
contract-gate
requirement-assessor
automated-closure-loop
execution-unit-policy
progressive-constraint-loading
delegation-router
execution-authorization-gate
knowledge-gate
provider-selection-matrix
repo-context-providers
tdd-state-machine
lane-completion
vertical-slice-readiness-gate
resume-policy
verification-contract
```

共同边界：只有需要独立调用、独立 handoff、独立输入输出的主动能力才保留为 skill；schema / registry / human-view / evidence / knowledge template / gate policy 沉淀为 `references/` 或 `assets/`。

### idc-brainstorming

```text
raw_idea -> approaches + draft_spec
```

仅用于模糊想法、raw idea 和早期产品方向。

短需求不等于模糊需求；如果一句话已经包含目标、行为和验收线索，应跳过 `idc-brainstorming`，进入 Grill Me / Alignment。

这是可直接复用的发散原子能力，吸收 Superpowers Brainstorming 方法论，先探索 2-3 个方向，再产出 draft spec。

### idc-intent-discovery

```text
raw_idea -> draft_spec
```

用于 IDC workflow 内的模糊想法。

它是 `idc-brainstorming` 的 IDC wrapper，负责把发散结果接入 normalized request、Grill Me 和 Alignment。

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

### idc-intent-grilling-with-docs

```text
draft_spec / structured_requirement / tr3_design_doc + docs -> clarification answers + doc refs
```

用于需要把澄清结果沉淀为公开决策文档、CONTEXT 或 glossary 的场景。

它和 `idc-intent-grilling` 共用 Grill Me 的 decision tree / frontier round
方法，但额外读取：

```text
.claude/skills/idc-intent-grilling-with-docs/SKILL.md
.claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md
```

### idc-intent-alignment

```text
machine contract -> human approval
```

用于把 Alignment Pack 渲染成中文 Alignment View，并等待用户 approve。

### idc-superpowers-adapter

```text
approved_alignment + bounded execution units -> Superpowers-style engineering loop
```

用于 Human Alignment 之后，把 Superpowers 的 planning、TDD、subagent development、systematic debugging、code review、verification-before-completion 和 finish branch 思路接入 IDC。

它不是外层 workflow owner：

```text
IDC Harness 决定 Domain / Lane / Contract / Completion Gate
idc-superpowers-adapter 只提供 approved 后的执行纪律
```

### idc-gc-sop-adapter

```text
approved_alignment + selected GC atom -> team-config GC SOP handoff
```

用于在企业内部复用 GC 全家桶 SOP 的原子能力。

外部仓库只保留 adapter contract，不包含真实 GC SOP prompt、命令、路径、日志或内部规则。

### idc-dt-design

```text
verification_contract + selected DT domain -> DT design artifact
```

原代码仓 DT design skill 的外部 adapter。它可以设计 DT，但 DT design 本身不是 RED / GREEN evidence。

### idc-dt-writer

```text
dt_design_ref + allowed paths -> DT changes + RED/GREEN evidence refs
```

原代码仓 DT writer skill 的外部 adapter。它可以写 DT 并返回 evidence refs，但不能标记 IDC DONE。

### idc-dt-build

```text
selected DT domain + enterprise command placeholder -> DT build/run evidence
```

D3A verification 阶段的 DT build / run evidence 接口 skill。外部 harness 只定义公开输入输出，不包含真实企业命令。

### idc-tran-build

```text
required DT GREEN -> tran_build PASS/FAIL evidence
```

D3A final build verification 接口 skill。它只服务 D3A DONE gate，不作为 General Coding gate。

### idc-gc-third-skill-placeholder

```text
<ENTERPRISE_GC_THIRD_SKILL_NAME> -> placeholder adapter
```

第三个原代码仓 skill 尚未命名，外部 harness 只保留占位，不能执行、不能猜用途。

## 编排关系

```text
idc-workflow
  -> idc-brainstorming
  -> idc-intent-discovery
  -> idc-intent-grilling
  -> idc-intent-grilling-with-docs if docs need updates
  -> idc-intent-alignment
  -> idc-superpowers-adapter
  -> idc-gc-sop-adapter
  -> idc-dt-design / idc-dt-writer / idc-dt-build / idc-tran-build / idc-gc-third-skill-placeholder
  -> idc-general-coding / idc-d3a-coding
  -> automated closure loop
```

## Domain Execution Skills

D3A 不拆成通用框架原子能力，但它作为本仓库 skill 也统一使用 `idc-` 前缀。

D3A 是 Domain Module + domain execution skill：

```text
.claude/skills/idc-workflow/references/domains/d3a/module.yaml
.claude/skills/idc-d3a-coding/SKILL.md
```

它可以复用 atomic skills，但自身保留领域边界。
