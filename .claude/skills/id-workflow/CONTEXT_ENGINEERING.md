# Context Engineering

Context Engineering 定义 Claude Code 运行 `id-workflow` 时如何渐进式加载信息。

目标不是建立固定预算表，而是让每个阶段只拿当前决策需要的上下文，避免旧结论、长日志、全文知识库和无边界搜索污染执行判断。

## 总原则

- 不默认加载整个 `references/`。
- 不默认读取全部 `docs/`、`examples/`、`tests/`。
- 不把 OKL / docs / CodeGraph / grep finding 当作 DONE evidence。
- 长日志和 provider 结果必须摘要化，并保留 `evidence_ref`。
- 有明确代码锚点时先 bounded grep。
- 没有代码锚点但有领域语义时，先用 OKL 拿 `summary / refs / keywords`，再 bounded grep。
- 影响范围不清楚时，再使用 targeted CodeGraph。
- 每个 execution unit 的代码变更控制在 `<= 500 LOC`。
- D3A 多 Layer 必须拆成多个 Layer Context Packet，每个 packet 只服务一个 Layer。
- Main agent 只做 planning / delegation / evidence summarization。
- Subagent / agent team 的完整 session 不能回灌 main session。

## Stage 1: 输入理解

默认加载：

```text
SKILL.md
CONTEXT_ENGINEERING.md
references/workflows/input-adapter.md
references/schemas/normalized-request.schema.yaml
```

只判断：

- 输入是一句话、TR3 文档，还是已批准 Alignment Pack。
- 输入成熟度是 `raw_idea`、`draft_spec`、`tr3_doc`，还是 `approved_alignment`。
- 是否存在明显的 domain hint、lane signal、代码锚点。

禁止：

- 直接读取全部 domain module。
- 直接跑全仓搜索。
- 直接进入实现。

## Stage 2: 澄清 / Discovery

如果 `input_maturity = raw_idea`，加载：

```text
.claude/skills/intent-discovery/SKILL.md
references/workflows/discovery-provider.md
references/schemas/discovery-provider.schema.yaml
references/human-views/brainstorming-view.md
```

如果关键 contract、scope、completion gate 缺失，加载：

```text
.claude/skills/intent-grilling/SKILL.md
references/workflows/clarification-provider.md
references/schemas/clarification-provider.schema.yaml
references/human-views/clarification-view.md
```

知识加载规则：

- 先读当前仓库的 `CLAUDE.md` / `AGENTS.md` 这类 repo-native rules。
- 如果用户输入提到明确文件、symbol、error、config key，使用 bounded grep。
- 如果用户输入只有领域概念或 TR3 主题，使用 OKL 获取摘要、引用和关键词。
- 澄清阶段可以加载知识，但只能用于提出更好的问题，不能替代用户确认。

禁止：

- 因上下文裁剪牺牲需求探索质量。
- 把 brainstorming 结果当作 approved contract。
- 在用户确认前写实现代码。

## Stage 3: Domain / Lane / Contract

默认加载：

```text
references/domains/registry.yaml
references/workflows/lane-resolver.md
references/workflows/contract-gate.md
references/workflows/human-alignment.md
references/schemas/alignment-pack.schema.yaml
references/human-views/alignment-view.md
```

按需加载：

```text
references/domains/d3a/module.yaml
references/domains/general/module.yaml
references/workflows/d3a-workflow.md
references/workflows/general-coding.md
references/schemas/d3a-plan.schema.yaml
references/schemas/general-plan.schema.yaml
```

Lane 策略：

- `fast`：只加载最小 contract、直接相关文件和轻量验证入口。
- `lite`：加载 task contract、相关实现、相关测试和必要规则。
- `complex`：按 execution unit 或 D3A Layer Context Packet 分批加载。

禁止：

- 把 General 场景强行套 D3A Layer / DT Domain registry。
- 对 D3A 猜测 Coding Layer 到 DT Domain 的映射。
- 在 Alignment Pack 被用户 approve 前进入实现。

## Stage 4: 执行

用户批准 Alignment Pack 后加载：

```text
references/workflows/automated-closure-loop.md
references/workflows/delegation-router.md
references/workflows/progressive-constraint-loading.md
references/workflows/execution-unit-policy.md
references/workflows/lane-completion.md
references/schemas/delegation-contract.schema.yaml
references/schemas/escalation-policy.schema.yaml
references/schemas/verification-contract.schema.yaml
```

执行上下文必须包含：

- 已批准的 Alignment Pack 摘要。
- Delegation Contract。
- 当前 execution unit 的目标、边界和 verification contract。
- 当前 domain module。
- 当前 lane completion rule。
- 当前相关 repo-native rules。
- provider findings summary，不是 provider 原始长输出。

D3A 执行额外要求：

- 一次只加载一个 Layer Context Packet。
- packet 必须声明 selected layer、allowed paths、required DT domains、evidence refs。
- RED / GREEN / `tran_build` evidence 必须来自工具结果。

Subagent / agent team 返回给 main 的内容只能包含：

- status。
- summary。
- changed_paths。
- evidence_refs。
- blockers。
- context_to_keep。
- context_to_drop。

禁止返回完整 subagent session、完整日志、完整搜索输出。

## Stage 5: 验证 / 闭环

默认加载：

```text
references/workflows/lane-completion.md
references/workflows/tdd-state-machine.md
references/schemas/verification-contract.schema.yaml
references/human-views/completion-view.md
```

只在失败时追加：

```text
references/human-views/escalation-view.md
references/workflows/provider-selection-matrix.md
references/workflows/repo-context-providers.md
```

验证判断只看：

- 测试 / 构建 / 静态检查工具 evidence。
- TDD RED then GREEN evidence。
- D3A required DT GREEN。
- D3A `tran_build PASS`。

禁止：

- 用 OKL、文档、grep 结果宣布 DONE。
- 把完整失败日志塞入下一轮上下文。
- 失败后扩大到无边界全仓搜索。

## Context Packet 形状

每次执行前形成轻量 packet：

```yaml
context_packet:
  task_id: string
  stage: input_understanding | discovery | alignment | execution | verification
  selected_domain: d3a | general | placeholder
  selected_lane: fast | lite | complex
  execution_unit_id: string
  allowed_paths: []
  loaded_files: []
  provider_findings:
    - provider: grep | codegraph | okl | repo_search
      summary: string
      evidence_ref: string
  constraints:
    - string
  open_questions:
    - string
```

`loaded_files` 只记录本阶段实际读过的文件；下一阶段必须重新判断是否继续保留。

## Delegation Contract 形状

```yaml
delegation_contract:
  workflow_id: raw_idea_alignment | tr3_alignment | general_execution | d3a_execution | verification_fix | build_fix
  selection_layer: dynamic_workflow | agent_team | subagent
  selected_agent_team: intent_alignment | knowledge | planning | coding | verification
  selected_agents: []
  main_agent_role: planning_and_delegation_only
  selection_reason:
    workflow_reason: string
    agent_team_reason: string
    subagent_reason: string
  subagent_communication:
    required: boolean
    handoff_edges: []
  context_packet_ref: string
  expected_return:
    - summary
    - changed_paths
    - evidence_refs
    - blockers
    - context_to_keep
    - context_to_drop
  forbidden_return:
    - full_subagent_session
    - full_logs
    - full_search_results
```
