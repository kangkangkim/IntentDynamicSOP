# Scenario 10: Lane = complex(hard trigger:跨模块 + 多测试域 + 依赖 DAG)

## 目的

体验 Complex hard trigger 的直接命中:多模块、多个测试域、需要依赖 DAG,
Lane Resolver 跳过 fast/lite 判断直接选择 `complex`,并观察 complex 级别的
完整输出(full_task_contract、dependency_dag、subagent_split、evidence_plan、audit)。

前置:`demo-project/` 已存在。

## Prompt to paste

```text
用 idc-workflow 处理这个 general coding 需求：

目标：在 demo-project 实现一个汇率换算子系统。
行为：
- 新增 currency_pair 解析模块：校验 "BASE/QUOTE" 货币对语法，
  BASE/QUOTE 必须是 is_valid_currency 认可的合法代码且不相等。
- 新增 rates 模块：静态汇率表 + 查询，未知汇率报错。
- 新增 convert 入口：金额用 Decimal 处理精度，输入金额字符串 + 货币对，
  输出换算结果字符串（保留两位小数）。
- 错误分类体系：无效货币对 / 未知汇率 / 金额非法，各自可区分。
- 复用现有 is_valid_currency 和 is_valid_amount（如存在）。
验收：
- 解析、汇率查询、换算集成三层各自的测试。
- 现有测试保持通过。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: hard triggers
     （cross_module_or_layer_impact + multiple_test_domains + needs_dependency_dag）
  -> selected_lane = complex（decision_rule = hard_trigger）
  -> Contract Gate -> Human Alignment -> complex 闭环
```

## Should see

- hard triggers 命中被显式列出,且有事实来源(三个模块、三层测试、解析->汇率->换算依赖)。
- complex required_outputs 齐全:full_task_contract、detailed_plan、dependency_dag、
  knowledge_gate_result、subagent_split、evidence_plan、audit_or_review。
- 多执行单元拆分(每 EU <= 500 LOC),capability selection 覆盖 execution DAG。
- TDD RED -> GREEN + coverage evidence(工具报告或豁免条目)。
- 跨模块改动经 Execution Authorization,allowed_paths 覆盖全部声明产物目的地。

## Should not happen

- 不应该因为"都是小函数"降级 lite(hard trigger 优先于一切强度判断)。
- 不应该把三个模块塞进单个巨大执行单元。
- 不应该跳过 dependency_dag / subagent_split / audit 直接写码。
- 不应该在 coverage 或 audit 缺失时标记 DONE。
