# IDC Domain Pack 与确定性运行时整改计划

## 1. 计划身份

- Task ID: `idc-domain-pack-deterministic-runtime`
- Change type: architecture refactor / new harness capability
- Selected Domain: `general`
- Lane: `complex`
- Branch: `codex/IntentDyanmicHarnessV2`
- Status: `PENDING_TECHNICAL_PLAN_CONFIRMATION`

## 2. 目标

把当前“固定 D3A workflow + 可选原子 Skill”的 harness 改造成：

1. `team-config.yaml` 继续作为团队唯一维护的集成配置入口。
2. IDC Core 只拥有授权、范围、证据、状态迁移和完成证明等不可绕过机制。
3. Domain、Workflow、Skill 顺序和 Domain completion predicate 由配置编译产生。
4. D3A 从 Core 特判迁为可选 Domain Pack；禁用或删除 D3A 不破坏 Core。
5. `ordered` orchestration 由机器 Run Graph、Dispatcher 和 Receipt 强制执行，而非依赖模型遵从文本。

## 3. 范围边界

### In scope

- 通用 Domain Pack Contract。
- Workflow Graph Contract。
- Skill Execution Contract。
- Completion Predicate Contract。
- `team-config.yaml` v2 兼容扩展与 v1 兼容读取。
- Config reachability / shadowing / fallback audit。
- 确定性 Run Graph 编译和 hash identity。
- Host-controlled ordered execution contract、事件账本和 receipt 校验骨架。
- D3A Domain Pack 迁移。
- Generic Completion Verifier。
- 回归、故障注入和 D3A removal tests。
- 修复本次手工调整确认策略产生的重复/拼接文本，但不覆盖其他用户改动。

### Out of scope

- 真实企业 API、命令、路径、日志、测试名和构建系统。
- 自定义大型 agent framework。
- 网络服务、数据库或集中式控制平面。
- 把 Skill 内部模型输出变成比其验证契约更强的“语义绝对正确”。
- 修改或清理与本计划无关的现有 dirty worktree 内容。

## 4. Core / Domain 所有权

### IDC Core 固定机制

- Execution Authorization。
- Allowed / forbidden path enforcement。
- Immutable Run Graph identity。
- Ordered state transition validation。
- Host dispatch/session attestation。
- Evidence and receipt verification。
- Crash-safe replay / idempotency contract。
- Completion 只能由 machine verifier 产生。

### Domain Pack 可配置策略

- Domain trigger rules。
- Lane applicability / fixed profile。
- Workflow nodes、edges、guards。
- Required contracts。
- Skill capability policy。
- Domain registries and knowledge refs。
- Completion predicates。

## 5. API Contract

以下均为公开 harness contract，不包含企业实现细节。

### 5.1 Team Config v2 input

```yaml
config_version: 2
domains:
  enabled: [<DOMAIN_ID>]
  default: <DOMAIN_ID>
  definitions:
    <DOMAIN_ID>:
      pack_ref: <DOMAIN_PACK_REF>
      trigger_rules: []
      workflow_profile_ref: <WORKFLOW_REF>
      capability_policy_ref: <CAPABILITY_POLICY_REF>
      completion_predicate_ref: <COMPLETION_REF>
```

Compatibility:

- v1 remains readable during migration.
- v1 implicit defaults must surface as `FALLBACK_USED`.
- Resolver never silently combines v1 and v2 ownership sources.

### 5.2 Config Compiler output

```yaml
effective_runtime:
  status: READY | NEEDS_TEAM_CONFIG
  source_sha256: string
  enabled_domains: []
  diagnostics:
    - path: string
      status: ACTIVE | UNREACHABLE | SHADOWED | FALLBACK_USED | INVALID
      reason: string
```

### 5.3 Run Graph output

```yaml
run_graph:
  status: READY | INVALID
  graph_id: string
  config_sha256: string
  graph_sha256: string
  selected_domain: string
  selected_lane: string | null
  nodes:
    - node_id: string
      execution_order: integer
      stage: string
      skill_id: string
      skill_ref: string
      required: boolean
      trigger_signals: []
  edges: []
```

Determinism requirement:

- Canonicalized identical inputs produce byte-equivalent graph semantics and identical `graph_sha256`.
- Unknown signals fail closed.
- Ordered nodes cannot be omitted, inserted, or reordered after authorization.

### 5.4 Execution event / receipt

```yaml
execution_event:
  run_id: string
  sequence: integer
  previous_event_hash: string | null
  graph_sha256: string
  authorization_id: string
  node_id: string
  event_type: NODE_READY | NODE_DISPATCHED | NODE_SUCCEEDED | NODE_FAILED | NODE_VERIFIED
  dispatch_tool_call_ref: string | null
  executor_session_ref: string | null
  evidence_refs: []
```

```yaml
execution_receipt:
  run_id: string
  graph_sha256: string
  authorization_id: string
  executed_nodes: []
  evidence_refs: []
```

### 5.5 Completion verification

```yaml
completion_result:
  status: DONE | TARGETED_FIX | BLOCKED
  graph_match: PASS | FAIL
  order_match: PASS | FAIL
  receipt_integrity: PASS | FAIL
  predicate_results: []
  errors: []
```

`DONE` requires exact graph/order match, verified receipts, all required predicates PASS, and no unresolved failure.

## 6. DT 设计

### DT-A: single-config ownership

- Given: 一个团队只修改 `team-config.yaml`，引用已存在的 Domain Pack / Skills。
- When: Resolver 编译运行时配置。
- Then: 不要求修改共享 registry 或 Core 文件，输出 READY effective runtime。

### DT-B: unreachable Lane detection

- Given: 仅启用 lane-not-applicable Domain，同时配置 fast/lite/complex。
- When: preflight。
- Then: 三个 Lane 标记 `UNREACHABLE`；strict mode 下阻断。

### DT-C: ordered graph determinism

- Given: ordered steps `[design, coding, verify]`。
- When: 使用相同配置和信号编译两次。
- Then: 节点顺序及 `graph_sha256` 相同。

### DT-D: order violation

- Given: authorized graph `[design, coding, verify]`。
- When: receipt 为 `[design, verify]` 或顺序改变。
- Then: Completion 返回 BLOCKED，不得 DONE。

### DT-E: forged receipt

- Given: receipt 自报 SUCCESS，但缺 dispatch tool-call ref 或 executor session ref。
- When: Completion verification。
- Then: `receipt_integrity=FAIL`。

### DT-F: config drift

- Given: authorization 绑定旧 config / graph hash。
- When: 执行阶段使用新 hash。
- Then: `BLOCKED_CONFIG_DRIFT`。

### DT-G: D3A disabled

- Given: enabled domains 不含 D3A。
- When: bootstrap、route、plan、completion。
- Then: 运行产物不引用 D3A workflow、Layer、DT 或 completion predicate。

### DT-H: D3A physically removed

- Given: D3A Domain Pack fixture 不存在。
- When: 运行 Core contract tests。
- Then: Core tests PASS；只有显式启用 D3A 时返回 bounded config error。

### DT-I: replay

- Given: 相同 immutable graph 和相同 event ledger。
- When: 重放两次。
- Then: 得到相同最终状态；重复 dispatch event 不产生第二次副作用授权。

## 7. 执行单元

每个代码执行单元保持 `<= 500 LOC`，按 RED → GREEN 推进。

### Unit 1: confirmation-policy hygiene and baseline RED tests

- 修复当前手工修改造成的重复/拼接文本。
- 新增 reachability、D3A removal、ordered violation 基线 RED tests。
- 不改变现有 production behavior。

### Unit 2: generic contracts and schema

- 增加 Domain Pack、Workflow Graph、Execution Event、Completion Predicate schemas。
- 将 Domain ID 从固定枚举改为合法动态 ID，同时保留 v1 compatibility validation。

### Unit 3: reachability-aware config compiler

- Resolver 输出 ACTIVE / UNREACHABLE / SHADOWED / FALLBACK_USED / INVALID。
- strict consumption policy。
- 修复 D3A-only 环境仍把 Lane policy 报 PASS 的误导。

### Unit 4: deterministic Run Graph compiler

- 从 effective config、selected Domain/Lane、observed signals 编译 canonical graph。
- 稳定排序、hash、unknown signal fail-closed。

### Unit 5: generic Domain Pack runtime

- Router / planner / selector 从 module contract 读取策略。
- 移除执行路径中的 `if domain == d3a` 形式特判。

### Unit 6: D3A Domain Pack migration

- 搬迁 Layer、DT、workflow、capability policy、completion predicates。
- 保持 D3A RED/GREEN 和 final build placeholder evidence contract。

### Unit 7: event ledger and ordered dispatcher contract

- 实现薄状态机和 append-only hash chain。
- 强制 ordered transition、idempotency key、config drift checks。
- Host adapter 无 attestation 时 fail closed。

### Unit 8: generic completion proof

- Completion 读取 graph、ledger、receipt 和 predicate results。
- 精确比较节点集合和顺序。
- D3A 通过 Domain Pack predicates 复用同一 verifier。

### Unit 9: migration and end-to-end closure

- v1 → v2 preview migration。
- 更新公开模板、架构文档和示例。
- 故障注入、完整 harness tests、placeholder hygiene。

## 8. Delegation 与变更边界

- Main agent 只负责计划、授权、dispatch 和证据汇总。
- 所有代码、测试、schema 和文档 mutation 由授权 subagent 执行。
- 执行子代理必须加载 `idc-general-coding` 作为外层协议。
- 每个授权只覆盖一个 execution unit 和明确 allowed paths。
- 当前 dirty worktree 中非本计划内容属于用户，禁止回滚或覆盖。

## 9. 验证命令

```sh
python3 tests/test_harness.py
```

如新增独立测试入口，只使用公开 placeholder 命名，并纳入上述 harness test 调用或项目现有测试入口。

## 10. 完成标准

- 全部新增 DT 先有 RED evidence，再有 GREEN evidence。
- `python3 tests/test_harness.py` PASS。
- 相同输入可重复产生相同 Run Graph hash。
- Ordered omission/reorder/forged receipt/config drift 全部 fail closed。
- D3A 禁用与物理移除场景通过。
- Core 中不存在运行时 D3A 名称特判。
- 团队接入仍只需要编辑 `team-config.yaml` 并提供其引用的 Skill / Domain Pack 实现。
- 所有执行单元均有 authorization ID、dispatch tool-call ref、executor session ref 和 completion evidence。

## 11. 回滚策略

- v1 compatibility path 在 v2 完整 GREEN 前保留。
- 新编译器和 runtime 先通过 feature flag / config version 隔离。
- 每个 execution unit 独立提交候选，不重写用户历史。
- 任一阶段无法保持旧测试 GREEN，则停止后续迁移并返回 targeted re-plan。
