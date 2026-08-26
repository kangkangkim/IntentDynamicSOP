# Scenario 14: Lane = complex(hard trigger:并发 + 性能,行为不变也升级)

## 目的

体验 `state_machine_or_concurrency_or_security_or_performance` hard trigger:
给纯函数加进程级缓存,对外行为完全不变、改动集中单文件,但引入了并发正确性
与性能语义,必须 `complex`。观察"改动小 + 行为不变"不能抵消 hard trigger,
且并发正确性需要专项测试设计,不能只跑现有用例。

前置:`demo-project/` 已存在。

## Prompt to paste

```text
用 idc-workflow 处理这个 general coding 需求：

给 demo-project 的 is_valid_currency 增加进程级结果缓存，提升批量校验
场景的吞吐（同一输入不重复计算）。要求：
- 线程安全：多线程并发调用时行为与串行一致，不出现脏读/丢更新。
- 对外行为完全不变：现有 11 个用例原样全绿，无 API 变化。
- 缓存对调用方不可见，不引入全局可变状态的外泄接口。
验收：
- 并发正确性有专项测试（多线程压同一输入与不同输入混合）。
- 有前后性能对比证据（如简单计时脚本），证明缓存生效。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> Lane Resolver: hard trigger
     （state_machine_or_concurrency_or_security_or_performance:
       concurrency + performance）
  -> selected_lane = complex（decision_rule = hard_trigger）
  -> Contract Gate -> Human Alignment -> complex 闭环
```

## Should see

- hard trigger 命中被显式列出且有事实来源:prompt 明确要求线程安全与性能提升,
  不是从"用户没提风险"反推的。
- 不因"单文件、行为不变、纯函数 demo"降级 lite——hard trigger 优先于一切
  强度判断。
- evidence_plan 包含并发专项测试(多线程混合输入)与性能对比证据两项,
  而不只是现有 11 个用例。
- 缓存实现方案先过 contract / design(如锁粒度、frozenset 只读性是否需要缓存
  的质疑也应出现在 alignment),再进实现。

## Should not happen

- 不应该因为"is_valid_currency 只是查 frozenset,加缓存毫无意义"自行砍掉需求
  或降级;有异议应走 AskUserQuestion,不是默默改任务。
- 不应该把"现有测试全绿"当成并发正确的证据。
- 不应该用无同步的裸 dict 缓存声称线程安全而无测试支撑。
- 不应该在性能证据缺失时声称性能验收完成。
