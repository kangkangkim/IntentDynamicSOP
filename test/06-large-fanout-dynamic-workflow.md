# Scenario 06: Large Fan-out Official Dynamic Workflow

## 目的

体验什么时候才应该考虑 official dynamic workflow，而不是普通 IDC Workflow Router。

## Prompt to paste

```text
用 id-workflow 判断这个任务应该怎么编排：

我有一个 approved general migration，需要扫描 80 个 Markdown 文件和 40 个 config 文件。
每个文件都要：
- 找到 deprecated marker。
- 生成一个局部修复建议。
- 跑一个 placeholder verification。
- 收集结果后去重、合并、排序。

如果有失败，需要 repeat fix -> verify，直到没有新增 failure 或达到停止条件。
这个流程以后每个 release 都要复跑。
先不要写代码，先告诉我应该用 IDC Workflow Router、Agent Team、Subagent，还是 official Dynamic Workflow。
```

## Expected route

```text
id-workflow
  -> IDC Workflow Router sees approved general migration
  -> official_dynamic_workflow.required = true
  -> triggers:
       many_files
       many_execution_units
       fanout_collect_verify
       repeat_until_pass
       save_and_rerun_needed
  -> propose workflow orchestration
```

## Should see

- 明确说明为什么不是单个 subagent。
- 明确说明为什么 agent team 不够。
- 明确说明 official dynamic workflow 适合脚本化 fan-out / collect / verify / repeat。

## Should not happen

- 不应该直接实现 migration。
- 不应该把普通 raw idea/TR3 路由说成 official dynamic workflow。
- 不应该跳过 Human Alignment / approved contract 前提。

