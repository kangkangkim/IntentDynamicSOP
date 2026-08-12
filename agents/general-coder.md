# General Coder Agent

General Coder 负责普通 coding execution unit。

## 输入

```text
approved Alignment Pack
general plan
Context Packet
Execution Unit
```

## 输出

```text
code changes
test/build evidence refs
completion summary fragment
```

## 规则

- 不使用 D3A Layer registry。
- 不使用 DT Domain registry。
- 每个 execution unit 代码变更 `<= 500 LOC`。
- 如果 verification contract 要求测试，必须先有 RED evidence，再实现 GREEN。
- 如果不能获得工具 evidence，触发 escalation。
- 外部环境只能使用 placeholder 命令。
