# Deep Dive: Lane and Completion

Lane 只表示执行强度。

```text
fast
lite
complex
```

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

D3A 的 completion gate 追加在 Lane 之上：

```text
Lane completion
+
D3A RED evidence
+
required DT GREEN
+
tran_build PASS
```
