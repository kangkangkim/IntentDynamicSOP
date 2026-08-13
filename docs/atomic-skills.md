# Atomic Skills

Atomic Skill 是可以被其他团队单独复用的小能力。

它必须满足：

- 有独立输入和输出。
- 不绑定 D3A 私有知识。
- 不依赖真实企业路径、命令或 secret。
- 能被 `id-workflow` 编排，也能被其他 workflow 单独调用。
- 有明确 handoff 条件。

## 第一批

### intent-discovery

```text
raw_idea -> draft_spec
```

用于一句话需求或模糊想法。

吸收 Superpowers Brainstorming 方法论，先发散，再产出 draft spec。

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
