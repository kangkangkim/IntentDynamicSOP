# Atomic Skills

Atomic Skill 是可以被其他团队单独复用的小能力。

它必须满足：

- 有独立输入和输出。
- 不绑定 D3A 私有知识。
- 不依赖真实企业路径、命令或 secret。
- 能被 `id-workflow` 编排，也能被其他 workflow 单独调用。
- 有明确 handoff 条件。

## 第一批

### brainstorming

```text
raw_idea -> approaches + draft_spec
```

仅用于模糊想法、raw idea 和早期产品方向。

短需求不等于模糊需求；如果一句话已经包含目标、行为和验收线索，应跳过 `brainstorming`，进入 Grill Me / Alignment。

这是可直接复用的发散原子能力，吸收 Superpowers Brainstorming 方法论，先探索 2-3 个方向，再产出 draft spec。

### intent-discovery

```text
raw_idea -> draft_spec
```

用于 IDC workflow 内的模糊想法。

它是 `brainstorming` 的 IDC wrapper，负责把发散结果接入 normalized request、Grill Me 和 Alignment。

### intent-grilling

```text
draft_spec / structured_requirement / tr3_design_doc -> clarification answers
```

用于 contract、scope、completion gate 进入 Alignment 前的关键追问。

吸收 Grill Me 方法论，按 decision tree 和 frontier round 收敛。

### intent-alignment

```text
machine contract -> human approval
```

用于把 Alignment Pack 渲染成中文 Alignment View，并等待用户 approve。

## 编排关系

```text
id-workflow
  -> brainstorming
  -> intent-discovery
  -> intent-grilling
  -> intent-alignment
  -> automated closure loop
```

## 不属于第一批

D3A 不拆成通用 atomic skill。

D3A 是 Domain Module：

```text
.claude/skills/id-workflow/references/domains/d3a/module.yaml
.claude/skills/d3a-coding/SKILL.md
```

它可以复用 atomic skills，但自身保留领域边界。
