# IDC Skill Pack Studio Prototype

这个目录是一个静态网页原型，用来表达 “上传团队 skills，拖拽编排 SOP，导出整套 skill pack” 的产品形态。

打开方式：

```sh
open prototypes/idc-skill-pack-studio/index.html
```

当前原型包含：

- Skill Intake：上传 `SKILL.md` / zip 后模拟标准化成 capability。
- Top-down Harness Board：中间主看板按从上到下的 IDC Harness 核心层展示，每一层都是可点击、可替换、可拖入原子能力的大框。
- Harness Layers：左侧作为层级导航和能力过滤，包括 Input、Routing、Contract、Domain、Knowledge、Execution、Evidence。
- Layer Swap：每层可以选择默认 IDC 实现、团队 adapter 或 placeholder 实现，并沉淀到 `layer_stack`。
- Routing Strategy：可视化 Scenario、Domain 和 Lane applicability；General Coding 动态选择 fast / lite / complex，D3A 使用固定 workflow 且 Lane 不适用。
- Capability Catalog：当前层下的团队 skill、agent、gate、router、handoff 原子能力货架。
- Drag Grid Canvas：canvas 是表格型拖拽网格，行是 Harness Layer，列是 Implementation / Atomic Capabilities / Gates。
- Canvas Drag Editing：在网格中拖动 layer 行改上下顺序，拖动能力卡跨 layer 移动，左侧能力拖入 layer 新增。
- Properties Panel：配置节点 inputs、outputs、evidence、session 策略。
- Validation Console：检查 API Contract、RED/GREEN evidence、DT GREEN、`tran_build` 等 IDC harness gate。
- Generated Pack：预览最终要导出的 npm / harness 资产结构和 `sop.yaml`。

这是 UX / 信息架构原型，不包含真实文件解析、真实 zip 导出或 registry 发布。
