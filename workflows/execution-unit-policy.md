# Execution Unit Policy

每个阶段的代码变更都必须控制在 500 行以内。

这里的“阶段”指一个可执行、可验证、可回滚的 execution unit。

## 全局规则

```text
max_change_loc_per_execution_unit = 500
```

如果预计或实际代码变更超过 500 行：

```text
必须拆分 execution unit
```

不能为了赶进度把多个无关修改合并在一起。

## 为什么限制 500 行

- 控制上下文大小。
- 降低 review 难度。
- 降低失败归因成本。
- 提高自动修复成功率。
- 让 evidence 更聚焦。
- 避免一次性跨太多边界。

## 拆分顺序

通用任务：

```text
先按功能边界拆
再按文件 / 模块拆
最后按 500 LOC 拆
```

D3A 任务：

```text
先按 Layer 拆
再按 execution unit 拆
最后按 500 LOC 拆
```

例如：

```text
D3A Plan
  -> impacted_layers: [DO, TFE, DRV]

DO Layer Context Packet
  -> DO execution unit 1 <= 500 LOC
  -> DO execution unit 2 <= 500 LOC

TFE Layer Context Packet
  -> TFE execution unit 1 <= 500 LOC

DRV Layer Context Packet
  -> DRV execution unit 1 <= 500 LOC
```

## Evidence 要求

每个 execution unit 都必须有自己的 evidence：

```text
changed_files
change_summary
verification_evidence
completion_summary
```

D3A execution unit 还需要遵守 module completion gate：

```text
RED evidence
required DT GREEN
tran_build PASS
```

## Escalation

如果无法在 500 行以内完成一个 execution unit：

```text
return_to: Planner
reason: execution_unit_too_large
```

如果拆分会改变已批准的 scope / contract / completion gate：

```text
return_to: Human Alignment
reason: scope_or_contract_change_required
```
