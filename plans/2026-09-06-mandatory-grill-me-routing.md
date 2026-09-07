# Structured Requirement 与 TR3 强制 Grill Me 路由技术计划

日期：2026-09-06
Task ID：`idc-mandatory-grill-me`
路由：General Domain / Lite Lane
执行单元：`unit-1-mandatory-grill-me-routing`
状态：`CONFIRMED`

## 1. 已确认决策

用户明确提出：`structured_requirement` 与 `tr3_design_doc` 两类输入都必须真实经过
Grill Me，不能再根据模型判断“看起来没有缺口”而跳过。用户在该设计说明后回复
“可以”，本记录将它作为本计划、输入路由契约与测试设计的 Technical Plan
Confirmation；这不是模型自我批准。

```yaml
technical_plan_confirmation:
  status: confirmed
  confirmation_channel: explicit_user_text
  user_message: "可以"
  confirmed_at: "2026-09-06"
  confirmed_objects:
    - technical_plan
    - input_signal_contract
    - alignment_floor_contract
    - verification_design
  model_self_attested: false
```

## 2. 当前事实与问题

当前 runtime 已有五步 effective alignment pipeline：Discovery、Brainstorming、Grilling、
Grill With Docs、Alignment Check。`tr3_input` 已在 framework default 的
`alignment-grilling` trigger 中，但 configured alignment 的 signal floor 只有
`raw_idea` 与 `critical_gaps_remain`，团队配置仍能删掉 TR3 的必经 Grilling。

`structured_requirement` 当前没有正式的 maturity-derived machine signal。测试把
`clarification_required` 当作 structured 输入的代理，只能证明“有缺口时 Grill”，不能证明
“只要输入是 structured requirement 就 Grill”。另外，旧 Studio 使用
`structured_requirement_ready` / `tr3_design_doc`，与 runtime 的 `tr3_input` 不一致。

因此当前系统只能保证“部分 TR3 默认会 Grill、检测到缺口的 structured 输入会 Grill”，
不能保证用户要求的两类输入无条件经过 configured clarification Skill。

## 3. 最小稳定 API Contract

保留输入成熟度枚举：

```text
raw_idea | structured_requirement | tr3_design_doc
```

统一使用两个 machine trigger token：

```text
structured_requirement_input
tr3_input
```

- Input Adapter 一旦产出 `input_maturity: structured_requirement`，必须同时产出
  `structured_requirement_input`。
- Input Adapter 一旦产出 `input_type/input_maturity: tr3_design_doc`，必须同时产出
  `tr3_input`。
- 不采用现有 Studio 私有 token `structured_requirement_ready`：`ready` 容易被误解为
  已通过 Human Alignment readiness；新 token 只陈述输入分类事实。
- 不采用 `tr3_design_doc` 作为 trigger token：它继续作为输入枚举，runtime signal 统一沿用
  已经存在的 `tr3_input`，避免双 token。
- `raw_idea` 路径不在本计划中改变；Discovery / Brainstorming 的去重也不属于本计划。

## 4. 机器强制语义

### 4.1 Resolver floor

v1 compatibility 与 v2 resolver 都必须将 alignment signal floor 扩展为：

```text
raw_idea
critical_gaps_remain
structured_requirement_input
tr3_input
```

其中 `structured_requirement_input` 与 `tr3_input` 必须由至少一个
`stage: clarification` 的 ordered step 覆盖。团队仍可重绑定该 step 的 `skill_ref`，但不能
删除这两类输入的 clarification coverage。缺失时 resolver 返回有界
`NEEDS_TEAM_CONFIG` / signal-floor 错误，不允许静默回退到 Alignment Check。

缺失或不完整的 `alignment` 配置继续 materialize framework default；默认
`alignment-grilling` 同时声明：

```yaml
trigger_signals:
  - critical_gaps_remain
  - clarification_required
  - structured_requirement_input
  - tr3_input
```

### 4.2 Context Plan enforcement

`plan_context.py` 正式注册 `structured_requirement_input`，并继续注册 `tr3_input`。在
decision phase 使用完整信号集时：

```text
--signals-complete --signal structured_requirement_input
```

或：

```text
--signals-complete --signal tr3_input
```

生成的 `alignment_resolution.steps` 必须把 effective pipeline 中相应 clarification step
标记为 `must_execute`，并加载该 step 当前绑定的 Skill；默认配置下 Discovery 与
Brainstorming 为 `skipped_by_signal`，Alignment Check 为 `always_run`。

强制性来自 effective ordered step、resolver floor 和 context-plan 状态三者闭合，不来自
文档中的“应该调用”措辞，也不允许 `plan_context.py` 硬编码 signal→Skill 名称。

### 4.3 Grill With Docs 边界

`docs_clarification_required` 继续单独触发 `alignment-grilling-with-docs`。
`tr3_input` 本身只保证普通 Grill Me clarification step 必经；没有
`docs_clarification_required` 时，不强制写文档或调用 docs-aware grilling。团队可以将
clarification step 重绑定为自己的文档感知 Skill，但 Core 不因此修改文档完成语义。

Grill Me 完成后仍须经过 Human Alignment；Grill Me 的回答不构成 Technical Plan
Confirmation 或 DONE 证据。

## 5. 配置兼容与迁移

- 未配置、或缺少完整 bindings/orchestration 的团队配置自动获得新 framework default，
  无需新增第二个配置文件。
- 已完整自定义 alignment 的 v1/v2 配置若缺任一新 floor token，将从“可运行”变为
  `NEEDS_TEAM_CONFIG`。这是有意的安全收紧，不能静默补入或猜测应该绑定哪个团队 Skill。
- 修复方式仅修改同一个 `team-config.yaml`：把两个 token 加到团队选择的
  `stage: clarification` step；团队自己的 Skill binding 保持有效。
- `team-config.yaml.template`、HTML Generator 与 Team Config Studio 的默认值、预设、
  导入校验和说明必须同步，禁止继续生成旧 token。
- `migration_preview.py` 继续复用 resolver 诊断；无需新增另一份迁移状态源，但要增加
  回归测试证明旧自定义配置得到有界错误、补齐后 READY。

## 6. 允许修改路径

运行时与 schema：

- `.claude/skills/idc-team-config/scripts/resolve_team_config.py`
- `.claude/skills/idc-team-config/scripts/prepare_runtime.py`
- `.claude/skills/idc-team-config/scripts/plan_context.py`
- `.claude/skills/idc-workflow/references/schemas/normalized-request.schema.yaml`
- `.claude/skills/idc-workflow/references/schemas/team-config.schema.yaml`
- `.claude/skills/idc-workflow/references/schemas/effective-team-config.schema.yaml`
- `.claude/skills/idc-workflow/references/workflows/input-adapter.md`
- `.claude/skills/idc-workflow/CONTEXT_ENGINEERING.md`
- `.claude/skills/idc-workflow/TEAM_CUSTOMIZATION.md`
- `.claude/skills/idc-workflow/SKILL.md`
- `.claude/skills/idc-intent-grilling/SKILL.md`

唯一配置入口及生成器：

- `team-config.yaml.template`
- `docs/team-config-generator.html`
- `prototypes/team-config-studio/script.js`
- `prototypes/team-config-studio/studio.test.mjs`

公开说明与场景：

- `README.md`
- `docs/user-input-routing-overview.html`
- `docs/idc-config-enforcement-architecture.html`
- `test/02-structured-general.md`
- `test/03-tr3-d3a.md`

测试与本次证据：

- `tests/test_harness.py`
- `tests/test_team_config_migration.py`
- `tests/test_v2_config_ownership.py`
- `.idc/runs/idc-mandatory-grill-me/attempt-1/red-evidence.txt`
- `.idc/runs/idc-mandatory-grill-me/attempt-1/green-evidence.txt`
- `.idc/runs/idc-mandatory-grill-me/attempt-1/studio-evidence.txt`
- `.idc/runs/idc-mandatory-grill-me/attempt-1/npm-evidence.txt`
- `.idc/runs/idc-mandatory-grill-me/attempt-1/knowledge-consumption-receipt.yaml`
- `.idc/runs/idc-mandatory-grill-me/attempt-1/knowledge-consumption-result.yaml`
- `.idc/runs/idc-mandatory-grill-me/attempt-1/execution-receipt.yaml`

若实现证明 `effective-team-config.schema.yaml`、migration 或 ownership 单测无需修改，应保留
原文件；allowlist 是上限，不是要求制造 diff。

## 7. 明确禁止

- 不合并或删除 Discovery / Brainstorming Skill，不处理它们潜在的重复调用。
- 不删除任何 Skill，不执行先前尚未批准的 Skill pruning 计划。
- 不改变 Lane 选择、D3A 固定七层、TDD state machine、authorization、dispatch、ledger
  或 completion 语义。
- 不让 Grill With Docs 对所有 TR3 无条件执行。
- 不新增第二个团队配置源，不允许模型或 Core 默默修改完整的团队 alignment override。
- 不引入企业内部 API、路径、命令、日志或实现细节。

## 8. TDD / DT 设计

### DT-1：Structured Requirement 必经 clarification

RED：默认和 configured effective runtime 在完整信号集
`[structured_requirement_input]` 下，当前 planner 不识别或不选择 clarification step。

GREEN：resolver READY；decision Context Plan 中相应 clarification step 为
`must_execute`、默认 Discovery/Brainstorming 为 `skipped_by_signal`、Alignment Check 为
`always_run`，required refs 包含 effective binding 指向的 Skill。

### DT-2：TR3 必经 clarification

RED：自定义 alignment 移除 `tr3_input` 后当前 resolver 仍可能 READY。

GREEN：v1/v2 configured alignment 缺 `tr3_input` 都被拒绝；补齐后
`--signals-complete --signal tr3_input` 必须选中 clarification step。仅有 `tr3_input` 时
Grill With Docs 保持 skipped；再加入 `docs_clarification_required` 时才选中 docs step。

### DT-3：团队重绑定仍受 floor 约束

团队把 mandatory signal 绑定到自定义 `idc-*` clarification Skill 后，Context Plan 必须
加载自定义 ref 并标记 must_execute；把 token 放到非 clarification stage 或全部删除时必须
失败。由此证明 Core 保证“必经团队配置的 clarification 能力”，而不是强制某个固定 Skill。

### DT-4：默认值与生成器一致

template、HTML generator、Team Config Studio 所有 preset 和预览都使用同一 token。生成的
YAML 通过权威 resolver；Studio 测试证明 structured/TR3 都触发普通 Grilling、不会触发
Discovery/Brainstorming，TR3 无 docs signal 时不会触发 Grill With Docs。

### DT-5：迁移与完整回归

旧完整 custom alignment 获得明确 signal-floor 错误；补齐同一 `team-config.yaml` 后
`prepare_runtime.py` READY。运行 full harness、runtime integrity、migration、v2 ownership、
Studio、installer/npm tests、`npm pack --dry-run` 与 `git diff --check`，全部 GREEN。

## 9. 实施顺序

1. 新增 DT-1～DT-4 contract tests 并保存可重复的 RED evidence。
2. 同步修改 v1/v2 resolver default 与 signal-floor/clarification-stage invariant。
3. 注册 planner signal，并更新 Input Adapter 与 machine schema contract。
4. 更新 template、两个配置生成器/Studio 默认值和迁移提示。
5. 更新相关公开 docs 与场景，使描述与机器路径一致。
6. 运行 targeted GREEN、`prepare_runtime.py`、完整 Python/Node/npm 回归并保存证据。
7. executor 返回 Execution Receipt；main agent 根据授权、dispatch ref 与证据判定完成状态。

## 10. 完成条件

- Structured 与 TR3 的 mandatory Grill Me 均由真实 resolver + decision Context Plan 证明。
- v1/v2、default/configured、团队 Skill 重绑定四类路径都有回归测试。
- `structured_requirement_ready` 与作为 trigger 的 `tr3_design_doc` 不再由官方生成器产生。
- Raw idea、docs-aware grilling、Human Alignment、Lane、D3A、TDD 与 Completion 行为无漂移。
- RED / GREEN、Studio、npm/full harness 与 diff hygiene 证据齐全。
- Execution Receipt 绑定本计划、authorization ID、真实 executor session、变更路径与证据。
