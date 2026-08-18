# Source Attribution

这个仓库会吸收公开项目中的方法论，但不直接包含企业 secret，也不复制外部项目的大段 prompt。

## Grill Me Inspiration

本仓库的 Clarification Provider 吸收了 Matt Pocock `skills` 项目中 `grill-me` / `grill-with-docs` 的公开设计思想。

Source:

```text
https://github.com/mattpocock/skills
https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me
https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs
```

License:

```text
MIT License
Copyright (c) 2026 Matt Pocock
```

本仓库吸收的是方法论，不是逐字复制原始 skill prompt。

吸收点：

- relentless interview：对模糊需求持续追问，直到能承诺方向。
- decision tree：沿着决策树展开问题，而不是一次性乱问。
- frontier round：每轮只问当前前置条件已经满足的问题。
- stateless / docs mode split：纯澄清不写文件；需要沉淀时才写 ADR / context。
- no implementation during grilling：澄清阶段不进入代码实现。
- same-language interaction：用户中文输入时，用中文完成澄清。

在 Intent Dynamic Code 中，这些思想被落到：

```text
.claude/skills/idc-workflow/references/workflows/clarification-provider.md
.claude/skills/idc-workflow/references/human-views/clarification-view.md
.claude/skills/idc-workflow/references/schemas/clarification-provider.schema.yaml
```

## Superpowers Brainstorming Inspiration

本仓库的 Discovery Provider 以 `obra/superpowers` 项目中 `idc-brainstorming` skill 的公开设计为 upstream baseline，并在其上添加 IDC overlay。

Source:

```text
https://github.com/obra/superpowers
https://github.com/obra/superpowers/tree/main/skills/brainstorming
```

License:

```text
MIT License
Copyright (c) 2025 Jesse Vincent
```

本仓库保留 upstream baseline 的核心流程，并用 IDC overlay 适配 handoff、Human View 和 machine contract。

Baseline 保留点：

- project context first：先理解项目上下文，再展开想法。
- focused discovery questions：根据问题复杂度成组追问，不因上下文裁剪牺牲需求探索质量。
- alternatives with trade-offs：给出 2-3 个方案、取舍和推荐。
- design before implementation：设计确认前不进入实现。
- written draft spec：把发散结果沉淀成 draft spec，再进入收敛。

在 Intent Dynamic Code 中，这些思想被落到：

```text
.claude/skills/idc-workflow/references/workflows/discovery-provider.md
.claude/skills/idc-workflow/references/human-views/brainstorming-view.md
.claude/skills/idc-workflow/references/schemas/discovery-provider.schema.yaml
```

## Superpowers Adapter Inspiration

本仓库的 `idc-superpowers-adapter` 将 Superpowers 的公开工程流程作为 IDC approved 后的内层执行纪律。

Source:

```text
https://github.com/obra/superpowers
https://github.com/obra/superpowers/tree/main/skills
```

License:

```text
MIT License
Copyright (c) 2025 Jesse Vincent
```

本仓库吸收的是 workflow shape，不逐字复制 upstream skill prompt。

当前 adapter 覆盖的 upstream skill family：

- writing-plans。
- executing-plans。
- test-driven-development。
- subagent-driven-development。
- systematic-debugging。
- requesting-code-review。
- receiving-code-review。
- verification-before-completion。
- finishing-a-development-branch。

IDC 保留外层控制权：

```text
Domain / Lane / Contract Gate / Completion Gate
```

在 Intent Dynamic Code 中，这些思想被落到：

```text
.claude/skills/idc-superpowers-adapter/SKILL.md
```
