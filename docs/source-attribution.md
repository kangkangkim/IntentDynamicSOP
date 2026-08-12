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
workflows/clarification-provider.md
human-views/clarification-view.md
schemas/clarification-provider.schema.yaml
```
