# Docs 与运行时事实一致性技术计划

## 1. 计划身份

- Task ID：`docs-runtime-consistency`
- Change type：documentation correction / deprecated surface containment / test hardening
- Selected Domain：`general`
- Lane：`complex`
- Status：`PENDING_TECHNICAL_PLAN_CONFIRMATION`
- 日期：`2026-09-06`

选择 `complex` 是因为本任务横跨多份 Markdown、四个流程 HTML、两个旧配置入口、
README/QUICKSTART 发现入口和全量文档合同测试；错误会直接影响团队采用、授权边界与
v1/v2 运行模式判断。Technical Plan Confirmation 完成前，不得修改本计划所列的
docs、测试或发现入口。

## 2. 目标

让 `docs/` 中对外可见的架构、配置和执行说明与当前实现保持一致：

- v1 仅作为可读取、可 preview migration 的兼容入口；v2 是推荐的确定性模式。
- `team-config.yaml` 是唯一团队配置源；Domain Pack 是被选择的模块资产，不是第二份
  团队配置。
- General、Custom、D3A、Lane、ordered Skill、knowledge、approval 和授权边界均按
  当前 resolver、policy materializer、compiler、authorizer、dispatch state、ledger 和
  completion verifier 的真实行为说明。
- 所有宣称可运行的 v2 示例必须由真实 resolver 返回 `READY`。
- 两个仍呈现 v1 字段的 HTML 只保留为历史说明，不能继续生成或推荐 v1 配置。
- 不修改任何运行 API、schema、CLI、Domain Pack 或 production Python。

不得把语言风格统一、全文重写或视觉重设计混入本任务；只修事实、危险动作和发现入口。
不得引入或编造企业 API、路径、命令、日志、测试名、SOP 或 D3A 私有实现。

## 3. 固定文件结论

### KEEP（本任务不得修改）

1. `docs/deep-dive/lane-and-completion.md`
2. `docs/deep-dive/progressive-constraint-loading.md`
3. `docs/deep-dive/repo-context-providers.md`
4. `docs/deep-dive/tr3-input.md`
5. `docs/idc-config-enforcement-architecture.html`
6. `docs/skillization-boundary.md`
7. `docs/source-attribution.md`

### UPDATE（只修事实与必要入口）

1. `docs/adoption-guide.md`
2. `docs/agent-team-architecture.md`
3. `docs/architecture.md`
4. `docs/atomic-skills.md`
5. `docs/confidential-migration-checklist.md`
6. `docs/context-runtime-view.html`
7. `docs/flow-d3a-general.html`
8. `docs/intake-discovery-trigger-flow.html`
9. `docs/team-rollout-playbook.md`
10. `docs/user-input-routing-overview.html`

### DEPRECATE（历史化，不在本任务重写为 v2）

1. `docs/enterprise-adoption-map.html`
2. `docs/team-config-generator.html`

`docs/team-config-generator.html` 本次绝不重写成 v2 generator。只允许：

- 显著标明它是历史 v1 surface，不是新团队配置入口。
- 禁用复制和下载生成配置的动作，避免产生可被误认为 v2 的文件。
- 导向 `docs/idc-config-enforcement-architecture.html`、
  `.claude/skills/idc-team-config/references/team-config-v2.md`、
  `team-config.yaml.template` 和两个现行 v2 example。

`docs/enterprise-adoption-map.html` 同样只历史化，并移除其对旧 generator 的推荐；完整
v2 adoption map 或 generator 属于后续独立计划。

## 4. v1 / v2 事实边界

### v1 compatibility

- 当前根 `team-config.yaml` 可以继续是 `config_version: 1`。
- v1 使用 `domain` / `general` 等兼容字段，没有 v2 canonical graph、external
  host-control 和 protected dispatch proof 强制链。
- `migrate_team_config.py --config <PATH> --preview` 只返回 candidate 与 assets，不提供
  `--apply`，不得修改源配置或 `.idc/`。
- 历史 v1 页面不能再被描述为推荐的新接入或“可运行 v2”入口。

### v2 deterministic runtime

- 团队配置使用 `team.id`、`team.repo_path` 和
  `domains.enabled/default/definitions`；definitions 必须位于 `domains` 内。
- General 使用官方 General Pack；Custom 从 `template-domain` 复制并维护自己的 Pack
  资产，再由 team-config 引用；D3A 是可启用或禁用的官方 Pack，不是 Core 内的 Domain
  ID 特判。
- 从 `domains.enabled` 省略 `d3a` 即禁用；禁用后物理缺少 D3A 资产不影响 Core、General
  或 Custom。启用 D3A 时仍固定七层，团队 DT registry 可整体替换，DONE 仍要求每个
  required DT GREEN 和 `tran_build` PASS。
- General 与 Lane-applicable Custom 使用 `fast`、`lite`、`complex`。`ordered` 中每个
  configured Skill occurrence 成为独立 graph node；遗漏、插入、重排、未注册或不符合
  Lane 的 Skill 必须 fail closed。
- 真实 v2 graph authorization 要求 host 在 executor 不可写路径提供 control record；
  `dispatch_state.py` 是 Python host API，不是 CLI。
- v2 proof contract 完成结果使用 `completion_result.status: DONE`；无 graph 的兼容路径
  可以返回 `completion_verification_result.status: DONE`。

## 5. API Contract

API Contract 不变。本任务不得修改：

- `team-config.yaml` schema、字段、枚举或所有权。
- resolver、migration、selection、compiler、authorization、dispatch、ledger、completion
  的参数、返回结构、错误码或状态。
- Domain Pack、workflow profile、capability policy、registry 或 completion predicate。
- `dispatch_state.py` 的 Python API。

文档必须使用真实接口：

```text
prepare_runtime.py --config PATH [--output PATH]
compile_run_graph.py --effective PATH --selection PATH --request PATH --output PATH
authorize_execution.py --request PATH [--host-control-record PATH] [--output PATH]
verify_completion.py --request PATH [--dispatch-state PATH] [--output PATH]
migrate_team_config.py --config PATH --preview
```

其中 `--host-control-record` 的强制性只针对真实 v2 graph authorization；文档不得把
`dispatch_state.py` 写成命令行工具。

旧 v1 页面历史化和禁用复制/下载是 UI 安全修正，不改变 v1 resolver compatibility，
也不新增任何配置转换 API。

## 6. 五个独立执行单元

每个 execution unit 的 production/test/evidence delta 必须独立小于或等于 500 LOC；
不得用删除整份大 HTML 的方式规避边界。

### Unit 1：Docs Contract RED

- 仅新增 `tests/test_docs_runtime_consistency.py`，并在 `tests/test_harness.py` 增加最小的
  fail-propagating standalone suite gate。
- 抽取 active docs 中标为 runnable 的 team-config v2 YAML，并调用真实 resolver。
- 对 v1 historical 标识、generator 复制/下载禁用、Discovery Provider、technical-plan、
  authorization、v2 completion result、CLI/API 文案建立精确 RED。
- 建立本地链接和 HTML 自包含/viewport/media 的机械检查。
- 只写 RED evidence，不修改 docs、README 或 QUICKSTART。

### Unit 2：危险 v1 surface containment

- 历史化 `docs/enterprise-adoption-map.html` 和 `docs/team-config-generator.html`。
- 只禁用 generator 的复制/下载动作并增加 canonical v2 入口；不重写其表单、状态模型或
  YAML generator 为 v2。
- 修正 `docs/confidential-migration-checklist.md` 和
  `docs/team-rollout-playbook.md` 的旧入口。
- 在 `README.md`、`QUICKSTART.md` 中把旧 generator/adoption map 的推荐入口替换为
  canonical v2 guide/template/examples；可以保留明确标为 historical 的浏览入口。

### Unit 3：Canonical Markdown 事实收敛

只更新以下文件：

- `docs/architecture.md`
- `docs/adoption-guide.md`
- `docs/agent-team-architecture.md`
- `docs/atomic-skills.md`

修正 Pack ownership、Custom 资产边界、v1 compatibility、v2 graph/host-control、Technical
Plan Confirmation、Execution Receipt 和 v1/v2 completion result；不复制 runtime lifecycle
全文，以 canonical links 承担细节。

### Unit 4：流程 HTML 授权边界修正

只更新：

- `docs/context-runtime-view.html`
- `docs/flow-d3a-general.html`
- `docs/intake-discovery-trigger-flow.html`
- `docs/user-input-routing-overview.html`

明确 Input Adapter/Maturity Router 是统一入口；只有 raw idea 进入 Discovery Provider，
结构化需求和 TR3 默认跳过它。把 mutation 主链改为：

```text
Human Alignment approval
-> Technical Plan Confirmation
-> Capability Selection + Knowledge Plan
-> Execution Authorization
-> real executor dispatch
-> evidence-backed Completion Verification
```

D3A 必须描述为官方可选 Pack 的固定架构，不得称为团队可重新设计的 workflow。

### Unit 5：GREEN、视觉与全量验收

- 使 Unit 1 的独立 suite GREEN，不削弱断言。
- 对所有 UPDATE/DEPRECATE 页面执行链接、静态 HTML、桌面/移动/打印视觉验收。
- 运行 skill validation、所有相关 standalone suites、full harness 和 diff check。
- 写真实 GREEN evidence、knowledge receipt、execution receipt；Completion Verifier 必须消费
  完整 execution receipt，不能用文档自述代替工具结果。

## 7. DT 矩阵

| DT | Given / When | Then |
|---|---|---|
| DT-1 Active v2 示例 | 抽取所有声称可运行或最小接入的 v2 YAML，使用真实 resolver | 全部 `READY`；`team` 与 `domains.definitions` 层级正确 |
| DT-2 v1 隔离 | 扫描 active onboarding 页面和两个 deprecated HTML | active 页面不生成/推荐 v1；deprecated 页面有醒目标识且复制/下载不可用 |
| DT-3 Domain ownership | 对照 General、template-domain、D3A official Packs | Pack 是模块资产；Custom 自维护资产；D3A 可禁用且不被 Core 特判 |
| DT-4 D3A 边界 | 对照 core-isolation、ownership 和 final suites | 七层固定、team DT 整体替换、禁用/物理删除、`tran_build` 文案一致 |
| DT-5 三 Lane ordered | 对照 selection/compiler/dispatch/completion tests | 每个 occurrence 保序；遗漏、插入、重排和未注册 Skill fail closed |
| DT-6 Approval/authorization | 扫描所有 mutation flow | 同时出现 Human Alignment、Technical Plan Confirmation、Authorization 和真实 executor provenance |
| DT-7 Host trust | 对照 authorizer、dispatch state、ledger 和 completion | v2 host-control 为外部受保护输入；hash 不是签名；dispatch state 明确为 Python API |
| DT-8 Completion result | 对照 `verify_completion.py` 两条路径 | v2 proof 使用 `completion_result`；兼容路径使用 `completion_verification_result` |
| DT-9 CLI surface | 对文档出现的脚本运行 `--help` | 命令、必需参数和可选参数与真实 CLI 一致 |
| DT-10 Links | 解析全部 Markdown links 与 HTML `href/src` | 本地目标和 fragment 均存在；deprecated 入口导向 canonical v2 页面 |
| DT-11 HTML static | 解析七个 HTML | 自包含、无外网资源、语义结构有效、viewport/media 存在、无重复 ID |
| DT-12 Visual | 浏览器在桌面与移动宽度检查，并执行打印预览 | 无页面级横向溢出、警告可见、交互禁用状态清晰、打印不截断核心事实 |
| DT-13 Hygiene/regression | 运行 skill validation、standalone 和 full harness | placeholder hygiene PASS；相关 suites PASS；full harness 113 或更新后的真实总数全绿 |

RED 必须先于任何 docs/入口修改。GREEN evidence 必须记录真实命令、退出码和失败传播；
不得只检查关键词存在，也不得用 mock resolver 代替真实 resolver。

## 8. Allowed Paths 边界

Technical Plan Confirmation 后，每个 Execution Authorization 只能从下列路径中选取其
execution unit 的最小子集：

```text
docs/adoption-guide.md
docs/agent-team-architecture.md
docs/architecture.md
docs/atomic-skills.md
docs/confidential-migration-checklist.md
docs/context-runtime-view.html
docs/enterprise-adoption-map.html
docs/flow-d3a-general.html
docs/intake-discovery-trigger-flow.html
docs/team-config-generator.html
docs/team-rollout-playbook.md
docs/user-input-routing-overview.html
README.md
QUICKSTART.md
tests/test_docs_runtime_consistency.py
tests/test_harness.py
.idc/runs/docs-runtime-consistency/attempt-<n>/...
```

KEEP 文件、`team-config.yaml*`、examples、`.claude/skills/**`、schemas、Domain Packs、Python
runtime 和其他测试均禁止修改。测试若暴露 production 缺口，应返回 blocker 并另立计划，
不得在本任务扩权。

## 9. 验证命令

至少执行：

```sh
python3 -B tests/test_docs_runtime_consistency.py
python3 <SKILL_CREATOR_ROOT>/scripts/quick_validate.py .claude/skills/idc-team-config
python3 <SKILL_CREATOR_ROOT>/scripts/quick_validate.py .claude/skills/idc-workflow
python3 tests/test_harness.py
git diff --check
```

还需对文档中的 CLI 运行 `--help`，对 runnable v2 示例运行真实 resolver，并用本地浏览器
完成桌面、移动和打印验收。任何 standalone 失败必须传播到 full harness。

## 10. 风险与回滚

- **最高风险：旧 generator 仍可产出 v1。** 本任务先禁用复制/下载；若禁用不可验证，
  保留页面但移除所有发现入口并标为不可操作 historical artifact。
- **兼容文档被误删。** v1 事实只历史化，不删除 resolver compatibility 或 migration 说明。
- **混淆 Pack 与团队配置。** 所有更新必须保留 `team-config.yaml` 唯一团队配置源，同时说明
  Custom Domain 仍需团队维护自己的模块资产。
- **文档测试变成关键词堆砌。** runnable 示例必须真实 resolve，CLI 必须真实 `--help`，
  deprecated action 必须验证不可操作。
- **视觉修正扩大范围。** 仅修警告、链接和必要响应式问题，不重做现有设计系统。
- **测试总数漂移。** 文档不得写死“45”或“113”为长期合同；evidence 记录当次真实总数。

回滚以 execution unit 为边界：

1. Unit 1 可独立移除新 standalone test 与 harness gate。
2. Unit 2 可恢复旧页面动作和发现链接，但不得只恢复一半造成隐藏可操作入口。
3. Unit 3、4 按各自文件组整体回滚，不能混回 v1/v2 半套术语。
4. Unit 5 只回滚测试/evidence 增量，不改生产运行时。

若修订需要改变 schema、CLI、resolver、Domain Pack 或 runtime 行为，立即停止并请求新的
Technical Plan Confirmation；本计划不授权该类扩展。

## 11. 完成条件

- 固定 KEEP 文件无变化。
- 10 个 UPDATE 文件只修获准事实和入口。
- 2 个 DEPRECATE 页面无法继续复制/下载生成 v1 配置，并明确导向 canonical v2。
- Active v2 示例全部由真实 resolver 返回 `READY`。
- 所有本地链接、HTML 静态/桌面/移动/打印验收通过。
- skill validation、相关 standalone、full harness 和 diff check 全绿。
- Execution Receipt 与 Completion Verification 对 authorization、executor、changed paths、
  knowledge 和 evidence 的引用一致。
- 用户完成本计划的 Technical Plan Confirmation 后，才允许进入 Unit 1 RED。
