# Input Adapter

Input Adapter 把不同输入形态统一成 `normalized_request`。

它支持两类输入：

```text
natural_language_intent
tr3_design_doc
```

## Natural Language Intent

用户输入可能是一句话或几句话。

Adapter 提取：

- 用户目标。
- 显式 domain hint。
- 风险线索。
- 文件 / 模块 / 接口线索。
- 明显缺失信息。

## TR3 Design Doc

TR3 是更结构化的输入，可能包含：

- 开发需求描述。
- API / 行为语义。
- DT 设计。
- 验收标准。
- 影响范围。
- 风险或约束。

Adapter 需要抽取：

```yaml
normalized_request:
  input_type: tr3_design_doc
  extracted_requirement: ...
  extracted_api_semantics: ...
  extracted_dt_design: ...
  extracted_acceptance: []
  explicit_domain_hints: []
  open_questions: []
```

同时输出分类信号：

```yaml
classification:
  domain_candidates: [d3a]
  change_type: new_capability
  change_shape: shotgun_change
  lane_signals:
    api_semantic_change: true
    cross_module_or_layer_impact: true
    multiple_test_domains: true
    needs_dependency_dag: true
```

## TR3 能识别什么

### 新增需求

识别信号：

```text
新增能力
新增接口
新增字段
新增行为
新的输入输出
新的错误语义
新的 DT case
```

输出：

```yaml
change_type: new_capability
lane_signals:
  api_semantic_change: true
```

### 霰弹式修改

识别信号：

```text
多个模块或 Layer 都要改
多个调用方同步调整
多个测试域一起改
没有单一 owning layer
改动分散但服务同一个目标
```

输出：

```yaml
change_shape: shotgun_change
lane_signals:
  cross_module_or_layer_impact: true
  needs_dependency_dag: true
  multiple_test_domains: true
```

### D3A 需求

识别信号：

```text
TRAN_CFG / DO / VISP_ADP / TFC_TFI / TFE / ADP / DRV
TPRINT / FW / DPF
D3A architecture
DT design 与 D3A Layer 关联
tran_build 要求
```

输出：

```yaml
classification:
  domain_candidates:
    - d3a
```

## 重要边界

TR3 不是 DONE 证据。

```text
TR3 DT design
  != DT RED evidence
  != DT GREEN evidence
  != tran_build PASS
```

TR3 只能作为：

- requirement input。
- contract draft input。
- planner input。
- verification intent input。

最终 completion 仍然必须依赖工具证据。
