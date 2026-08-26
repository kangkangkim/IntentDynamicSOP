# Deep Dive: TR3 Input

TR3 是高级输入源。

它可以包含：

- 开发需求描述。
- API / 行为语义。
- DT 设计。
- 验收标准。
- 影响范围。

Input Adapter 会抽取：

```text
normalized_request
classification
lane_signals
```

TR3 可以帮助识别：

- 新增需求。
- 霰弹式修改。
- D3A 需求。

但 TR3 不是 DONE 证据：

```text
TR3 DT design != DT RED evidence
TR3 DT design != DT GREEN evidence
TR3 != tran_build PASS
```
