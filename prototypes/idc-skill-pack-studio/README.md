# IDC Skill Pack Studio Prototype

这个目录是一个静态网页原型，用来表达 “上传团队 skills，拖拽编排 SOP，导出整套 skill pack” 的产品形态。

打开方式：

```sh
open prototypes/idc-skill-pack-studio/index.html
```

当前原型包含：

- Skill Intake：上传 `SKILL.md` / zip 后模拟标准化成 capability。
- Harness Layers：按 IDC Harness 核心层选择能力，包括 Input、Routing、Contract、Domain、Knowledge、Execution、Evidence。
- Layer Swap：每层可以选择默认 IDC 实现、团队 adapter 或 placeholder 实现，并沉淀到 `layer_stack`。
- Routing Strategy：可视化 Scenario、Domain、Lane 决策，支持切换 D3A / Custom Team Domain / General Coding，以及 fast / lite / complex lane。
- Capability Catalog：当前层下的团队 skill、agent、gate、router、handoff 原子能力货架。
- SOP Canvas：把 capability 拖到画布上编排流程，并继续拖动画布节点调整位置。
- Properties Panel：配置节点 inputs、outputs、evidence、session 策略。
- Validation Console：检查 API Contract、RED/GREEN evidence、DT GREEN、`tran_build` 等 IDC harness gate。
- Generated Pack：预览最终要导出的 npm / harness 资产结构和 `sop.yaml`。

这是 UX / 信息架构原型，不包含真实文件解析、真实 zip 导出或 registry 发布。
