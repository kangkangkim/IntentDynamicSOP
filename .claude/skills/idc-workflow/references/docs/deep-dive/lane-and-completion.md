# Deep Dive: Lane and Completion

Lane 只表示执行强度。

```text
fast
lite
complex
```

IDC V0 只允许这三种 Lane。不要把 `known-domain`、`d3a`、`gc`、
`dynamic`、`unknown` 这类 domain / scenario / adapter 概念写成 Lane。

所有 Lane 都必须自闭环：

```text
fast = 小闭环
lite = 标准闭环
complex = 强闭环
```

## Fast

- 不默认 TDD。
- 必须有 basic verification evidence。
- 适合可举证的文档、注释、格式、明确元数据，以及极小、局部、低风险的 production code 修改。
- 所有 Fast 条件必须显式成立并带来源；未知条件不能帮助进入 Fast。
- 可以不新增测试代码，但必须有现有测试、build、lint、静态检查或等价 basic verification。

## Lite

- 可以 TDD，但不全局强制完整 RED/GREEN。
- 必须有 test/build evidence。
- Domain Module 可以强制 TDD。
- 适合比 Fast 稍大的普通 development task，包括需要新增/修改测试、多个相关文件/组件、局部行为设计或 focused repo exploration 的任务。

## Complex

- 强验证。
- 通常需要 RED/GREEN、build、review/audit。
- 适合跨模块、高风险、霰弹式修改。

## D3A

D3A 不参与 Lane 分类，它的 fixed workflow 直接声明 completion gate：

```text
D3A RED evidence
+
required DT GREEN
+
tran_build PASS
```
