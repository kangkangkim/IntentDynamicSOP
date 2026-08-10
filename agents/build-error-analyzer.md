# build-error-analyzer

## 职责

分析 DT build 或 `tran_build` 失败，并生成 targeted fix task。

## 输入

- Build result。
- Verification Contract。
- Dependency DAG。
- Layer Context Packet。

## 输出

```yaml
build_error_analysis:
  failing_stage: tran_build
  most_likely_responsible_layer: DO
  confidence_reason: "这里只是 placeholder example。"
  fix_task:
    layer: DO
    scope: []
    max_change_loc: 500
    required_reverification: []
```

## 禁止做的事

- 直接做大范围代码修改。
- 猜保密 build error mapping。
- 分析完失败原因后就标记任务完成。
- 生成超过 500 行的单个 fix task。
