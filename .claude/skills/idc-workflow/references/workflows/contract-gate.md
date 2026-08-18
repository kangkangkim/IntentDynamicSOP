# Contract Gate

Contract Gate 决定这次任务需要哪些 contract。

API Contract 不是全局强制项。它由 `Domain Module + Lane + Task Type` 共同决定。

## 基本原则

- 所有任务至少要能说明目标和验收标准。
- 所有任务都必须有 completion evidence。
- 只有涉及接口、行为契约或领域模块要求时，才需要 API Contract。
- Domain Module 可以声明 required contracts。
- Lane 决定 contract 的详细程度。

## 示例

### Fast 通用任务

```text
Task Summary
Acceptance Criteria
Basic Verification
```

### Lite 通用开发

```text
Task Contract
Acceptance Criteria
Focused Verification
```

### Complex 通用开发

```text
Task Contract
Detailed Plan
Risk Notes
Verification Contract
```

### D3A Module

D3A 可以强制要求：

```text
D3A Specification
API Contract
Verification Contract
```

## 输出形状

```yaml
contract_gate_result:
  selected_domain: d3a
  selected_lane: complex
  required_contracts:
    - d3a_specification
    - api_contract
    - task_contract
    - verification_contract
  optional_contracts: []
  reasons:
    - D3A module 要求 API Contract。
    - Complex lane 要求详细 verification contract。
```
