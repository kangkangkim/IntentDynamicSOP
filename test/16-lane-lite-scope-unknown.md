# Scenario 16: Lane = lite(lite floor:affected_scope_unknown,范围未知)

## 目的

体验 `affected_scope_unknown` + `broad_repo_exploration_required` lite floor:
任务方向清楚(字面量换成命名常量),但事先不知道有多少处、涉及哪些文件,
影响范围 unknown。`unknown` 不能帮任务进 fast,Fast 资格直接取消;执行上
必须先探索盘点、收敛范围,再锁定改动清单。

前置:`demo-project/` 已存在。

## Prompt to paste

```text
用 idc-workflow 处理这个 general coding 需求：

把 demo-project 里的字面量 magic 值清理成命名常量：货币码列表、
docstring 之外重复出现的示例货币码字符串、测试里重复的样例数据等。
我不确定一共有多少处、最后会涉及哪些文件。
要求：行为和测试结果保持完全不变，改完列出全部改动清单。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: lite floor
     （affected_scope_unknown + broad_repo_exploration_required）
     fast 取消资格（scope unknown ≠ scope tiny）
  -> selected_lane = lite
  -> 先探索盘点（inventory） -> 收敛 scope -> Contract Gate -> Alignment -> lite 闭环
```

## Should see

- lane_decision 的 `fast_disqualified_by` 含 scope unknown 类信号;
  `tiny_scope` / `localized_change` / `fast_scope_evidence_present` 为
  unknown 或 false,而不是被当成 true。
- 执行先产出盘点结果(哪些文件、哪些字面量、哪些值得抽常量),scope 收敛后
  有明确的改动清单声明,再进入 contract / Execution Authorization。
- `no_behavior_contract_change` 的判定基于盘点后的事实(例如确认测试样例
  数据抽取不影响断言语义),而不是想当然。
- 改动清单外的文件不被触碰;现有 11 个用例照跑全绿作为 basic verification。

## Should not happen

- 不应该因为"重构不改行为、看起来简单"进 fast(scope unknown 直接取消资格)。
- 不应该把"用户说不知道范围"当成低风险信号(unknown 不算否定条件)。
- 不应该在盘点前锁定 allowed_paths 并开始改代码。
- 不应该在清单未收敛时把剩余字面量静默跳过却声称完成。
- 不应该因为盘点后发现涉及文件多就无声升级 complex——升级要有新的事实
  命中 hard trigger,并输出新的 lane_decision。
