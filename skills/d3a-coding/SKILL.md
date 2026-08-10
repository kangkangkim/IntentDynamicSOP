# D3A Coding Skill

当 Scenario Router 选择 `D3A_CODING` 后，使用这个 skill。

## 流程

1. 运行 Requirement Assessor。
2. 如果需要，进入 Grill Me / 澄清 placeholder。
3. 产出 D3A Specification。
4. 在 implementation 前 freeze API Contract。
5. Planner 只能在固定 D3A Layer registry 内规划。
6. DT Domain 只能从 V0 DT registry 选择。
7. 构造 dependency DAG。
8. 为每个选中 Coding Layer 创建一个 Layer Context Packet。
9. Implementation 完成前必须确认 RED evidence。
10. 每个 required DT Domain 都必须有 GREEN evidence。
11. 运行 `tran_build`。
12. 只有 `tran_build` PASS 后才能标记 Done。

## 保密区绑定

以下 placeholder 只能在企业保密区替换：

```text
<ENTERPRISE_API_CONTRACT>
<ENTERPRISE_REPO_PATH>
<ENTERPRISE_PLACEHOLDER>
```
