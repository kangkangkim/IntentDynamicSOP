# 术语说明

这个项目采用“中文说明 + 稳定英文标识”的写法。

## 为什么不是全中文

有些内容需要被脚本、agent、schema 或后续自动化稳定读取。如果把这些内容翻译成中文，后续很容易出现字段不一致、测试失效或跨工具传递失败。

因此：

- 人看的解释尽量使用中文。
- 机器读的字段名保持英文。
- D3A / DT 的固定名称保持原样。
- 状态机枚举保持原样。

## 故意保留英文的内容

### 文件和目录名

例如：

```text
README.md
docs/
schemas/
workflows/
.claude/agents/
.claude/skills/
tests/
```

这些名字方便被工具、脚本和其他 coding agent 识别。

### YAML / Python 字段名

例如：

```text
api_contract
d3a_plan
required_dt_domains
verification_mapping
completion_status
```

这些是 contract key，属于机器接口，不建议翻译。

### 固定架构标识

例如：

```text
TRAN_CFG
DO
VISP_ADP
TFC_TFI
TFE
ADP
DRV
TPRINT
FW
DPF
```

这些是 D3A / DT 的固定 registry id，不应翻译。

### 状态和 evidence 枚举

例如：

```text
RED
GREEN
PASS
FAIL
DONE
NEED_CLARIFICATION
READY_FOR_SPEC
```

这些值会被测试和 workflow gate 使用，不建议翻译。

## 已中文化的内容

- README 说明。
- 架构说明。
- 保密区迁移 checklist。
- Placeholder 规则。
- Workflow 文档。
- Agent 职责文档。
- Skill 接口说明。
- Knowledge 模板标题。
- Mock 示例中的自然语言描述。
- 测试输出和失败提示。

## 阅读建议

如果只想理解项目，不需要关心英文 key 的细节。先看：

```text
README.md
docs/architecture.md
docs/confidential-migration-checklist.md
```

如果要改 contract 或测试，再看：

```text
schemas/
tests/test_harness.py
```
