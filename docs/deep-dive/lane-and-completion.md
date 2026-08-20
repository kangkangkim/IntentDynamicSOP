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
- 适合文档、注释、小范围低风险修改。

## Lite

- 可以 TDD，但不全局强制完整 RED/GREEN。
- 必须有 test/build evidence。
- Domain Module 可以强制 TDD。

## Complex

- 强验证。
- 通常需要 RED/GREEN、build、review/audit。
- 适合跨模块、高风险、霰弹式修改。

## D3A

D3A 是固定范式 Domain Module，Lane 对它不适用；它跳过 Lane Resolver，由用户设计的 D3A workflow 决定执行和证据要求。
其 completion gate 直接来自 D3A workflow：

```text
D3A RED evidence
+
required DT GREEN
+
tran_build PASS
```
