# Scenario 02: Structured General Request

## 目的

体验已经有目标、行为、验收线索的 General 请求是否跳过 Brainstorming，进入 Grill Me / Alignment。

## Prompt to paste

```text
用 id-workflow 处理这个 general coding 需求：

目标：增加一个脚本，扫描仓库 Markdown 文件里的 TODO。
行为：
- 只扫描 docs/ 和 README.md。
- 输出 TODO 所在文件、行号和原文。
- 不修改任何文件。
验收：
- 能用一个命令运行。
- 给一个 mock 输出示例。
```

## Expected route

```text
id-workflow
  -> input_maturity = structured_requirement
  -> Domain = general
  -> intent-grilling if contract/scope/completion gate gap exists
  -> intent-alignment
```

## Should see

- 如果存在脚本语言、TODO 匹配规则、mock 输出位置等 contract / scope / completion gate gap，必须先出现 Clarification View。
- Clarification View 应该使用选择题问题卡，而不是长篇开放追问。
- 用户回答 Clarification View 后，才应该回到 Alignment View。
- Alignment View 在实现前出现。

## Should not happen

- 不应该默认 Brainstorming。
- 不应该把待定细节或开放问题塞进 Alignment View。
- 不应该把 Clarification View 合并进 Alignment View。
- 不应该未 approval 就写代码。
- 不应该使用 D3A Layer / DT Domain registry。
