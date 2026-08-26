# Scenario 09: 反 Fast 探针("就改一行")

## 目的

体验 Lane Resolver 对 Fast 的严格准入:用户口头上"一行、很快"的修改,
只要改变行为契约,就必须被降出 fast。缺失或无法确认的信号按 `unknown` 处理,
`unknown` 永远不能帮助任务进入 `fast`。

前置:`demo-project/` 已存在。

## Prompt to paste

```text
用 idc-workflow 处理这个需求，就一行改动，快点：

is_valid_currency 校验前先把输入 strip 一下，" usd " 这种带空白的也能过。
不用改测试吧，改完跑一下现有的就行。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: lite floor（behavior_contract_change + new_or_changed_test_required）
  -> selected_lane = lite（不是 fast）
  -> Contract Gate -> Human Alignment -> lite 闭环
```

## Should see

- lane_decision 的 `fast_disqualified_by` 列出原因:输入带空白的判定结果从 false 变 true,
  属于行为契约变化;且需要新增/调整测试覆盖空白输入。
- 即使用户说"不用改测试",resolver 也不采纳——
  不允许仅根据"用户没要求测试"推断无需新增测试。
- 执行时补上空白输入的测试用例,RED -> GREEN。
- lite 的 completion gate 照常闭合(含 coverage 证据或豁免)。

## Should not happen

- 不应该因为"一行"、"很快"、"用户没要求测试"进入 fast。
- 不应该接受"缺失信号当否定条件"(没提到风险 ≠ 低风险成立)。
- 不应该在未调整测试的情况下只改实现就声称完成。
