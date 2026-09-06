# IDC Skill 可达性审计与裁剪技术计划

## 1. 计划身份

- Task ID：`idc-skill-pruning`
- Change type：dead skill pruning
- Selected Domain：`general`
- Lane：`lite`
- Status：`PENDING_TECHNICAL_PLAN_CONFIRMATION`
- 日期：`2026-09-06`

本计划只定义审计、裁剪边界、API Contract 与验证门槛。未经 Technical Plan
Confirmation，不得删除任何 Skill、目录、注册项、文档或测试。

## 2. 目标与判定原则

目标是移除唯一被当前证据明确证明为不可执行且不参与任何 current/effective runtime
路径的 placeholder Skill，同时保留所有 current、domain、direct、extension 或
dormant-but-reachable 的能力。

“当前没有被某个团队选中”不是删除依据。只有同时满足下列条件，才可作为删除候选：

1. 不在官方 Domain Pack、有效团队配置、runtime compiler、Capability Selector、
   completion、alignment 或可安装包的可达路径中；
2. 不具备可执行契约，或被显式标记为 `NOT_EXECUTABLE` / `executable: false`；
3. 除说明、测试或 adapter prose 外不存在运行时消费者；
4. 删除不改变任一真实 capability、Domain、Lane、effective runtime 或运行输出。

## 3. 审计结论（实施前基线）

当前 `.claude/skills` 下有 18 个 `idc-*` Skill。分类必须以
`.idc/runs/idc-skill-pruning/attempt-1/skill-reachability-audit.yaml` 为准；摘要如下：

| 分类 | Skill | 处理 |
| --- | --- | --- |
| 唯一明确死候选 | `idc-gc-third-skill-placeholder` | 第一单元删除 |
| dormant-but-reachable | `idc-self-optimization` | 保留 |
| 官方 Pack 默认 | `idc-superpowers-adapter` | 保留 |
| current/domain/direct/extension runtime reachable | 其余 15 个 | 保留 |

`idc-gc-third-skill-placeholder` 的 registry 状态为 `placeholder`、
`executable: false`，其自身输出 `NOT_EXECUTABLE`；它不在当前或 effective runtime
中，现有命中仅位于 docs、tests 与 adapter prose。因此它是明确的清理对象，而不是
待团队配置的可执行能力。

`idc-self-optimization` 当前可处于 dormant 状态，但可由 `self_optimization`
的 `observe` / `propose` workflow 调用，故不得按“暂未执行”删除。
`idc-superpowers-adapter` 是 General 与 Template Domain Pack 的官方默认 inner
execution skill，故不得删除或降级。

## 4. 非删除设计债（本计划不处理）

`idc-intent-discovery` wrapper 内部调用 `idc-brainstorming`，同时 framework-default
alignment 将二者配置为连续的 `raw_idea` 步骤。这可能造成重复或回环感，但二者都有
明确可达路径，不能作为死代码清理处理。

必须在本次裁剪完成后另立 `discovery/brainstorming consolidation decision`，单独确认
路由所有权、一次调用语义、兼容迁移与回归测试；不得与 placeholder 删除捆绑，避免在
缺少产品决策时改变 raw idea 行为。

## 5. API Contract

第一实施单元不新增或修改团队配置字段、Domain Pack、Lane、capability ID、Skill
选择算法、resolver 输出、graph 输出、authorization 格式、completion predicate 或
命令行接口。

允许的公开表面变化仅为：

1. 移除目录 `.claude/skills/idc-gc-third-skill-placeholder/`；
2. 从下列 7 个位置清除该 placeholder 的声明或说明：
   - `.claude/skills/idc-gc-sop-adapter/SKILL.md`
   - `.claude/skills/idc-skill-adapter-router/SKILL.md`
   - `.claude/skills/idc-workflow/references/workflows/skill-adapter-router.md`
   - `.claude/skills/idc-workflow/SKILL.md`
   - `.claude/skills/idc-workflow/references/registries/skill-adapters.yaml`
   - `docs/atomic-skills.md`
   - `tests/test_harness.py`
3. 新增或调整一个可达性 contract test，证明已安装 Skill 集合、registry 与所有公开
   runtime refs 中均无 dead placeholder，且保留的 17 个 Skill 的 required paths 不变。

不得删除 `<ENTERPRISE_GC_THIRD_SKILL_NAME>` 等 confidentiality onboarding placeholder
的概念说明；只移除被误包装为实际 Skill 的 directory/registry/prose 引用。若该概念仍
需说明，应保留为 team onboarding 的非 executable data placeholder，不能再携带
`idc-*` Skill 身份。

## 6. DT 设计

### DT-A：可达性基线与分类

- Given：18 个本地 `idc-*` Skill、官方 Domain Pack、team config、registry、runtime
  scripts、测试、文档与 npm package manifest。
- When：生成静态反向引用图并对 General、Template、D3A、alignment、extension 与
  self optimization 路径进行真实 resolver/selector 检查。
- Then：每个 Skill 有分类、consumer evidence 与保留/删除理由；只有
  `idc-gc-third-skill-placeholder` 满足删除条件。

### DT-B：RED evidence

- Given：删除前仓库。
- When：执行新的 reachability contract test。
- Then：它应因死 placeholder directory/registry/prose reference 仍存在而 RED；记录
  明确的发现位置，而不是仅依赖目录计数。

### DT-C：裁剪闭合

- Given：第一单元允许路径。
- When：删除 placeholder 目录并清理全部 7 处引用。
- Then：`rg` 对完整 token、SKILL directory、adapter registry 及 public docs 无残留；
  registry 不含 `status: placeholder` 的可执行 adapter row；所有 remaining registry
  `skill_ref` 真实存在。

### DT-D：真实运行时不变

- Given：现有 `team-config.yaml` 与公开 v2 General、Custom、D3A examples。
- When：执行 `prepare_runtime.py`，并运行 relevant standalone selector/compiler/
  authorization/integrity/completion tests。
- Then：所有真实 Domain、Lane、capability selection、effective runtime 与 graph 仍
  GREEN；不出现该 placeholder 的 fallback、silent substitution 或新的 capability。

### DT-E：保留项防回归

- Given：裁剪后的 Skill tree。
- When：审计 `idc-self-optimization` 与 `idc-superpowers-adapter` 的 evidence。
- Then：前者仍有 self optimization `observe` / `propose` workflow consumer，后者仍为
  General/Template Pack default；`idc-intent-discovery` 与 `idc-brainstorming` 均保持，
  且没有在本单元改变两者的 raw idea 顺序。

### DT-F：打包与全量回归

- Given：最终 workspace。
- When：执行 `npm pack --dry-run`（或仓库等价 package verification）、`git diff --check`、
  `quick_validate.py`（每个保留 Skill）、所有 standalone tests、`prepare_runtime.py` 和
  `python3 tests/test_harness.py`。
- Then：npm package 不包含 dead Skill directory 或 token；全量 harness GREEN；无 API
  或运行输出漂移。

## 7. 实施单元

### Unit 1：dead placeholder Skill 删除（需要本计划确认后单独授权）

1. 执行 DT-A 并冻结 reachability manifest、所有 token refs 与 npm dry-run baseline。
2. 先新增 reachability contract test，运行并记录 DT-B RED evidence。
3. 由授权 executor 删除
   `.claude/skills/idc-gc-third-skill-placeholder/`，并精确清理上述 7 处引用。
4. 把原先“第三个原仓 Skill”表述改为普通 onboarding placeholder，而非 registry
   adapter 或可调用 Skill；不得猜测企业实现。
5. 运行 DT-C 至 DT-F，记录 GREEN evidence、package listing、effective runtime and
   standalone results。

### Unit 2：discovery/brainstorming consolidation（可选，必须另确认）

此单元不属于本次授权范围。仅在用户单独确认 consolidation decision 后，才可分析
`idc-intent-discovery` 与 `idc-brainstorming` 的 wrapper/连续 alignment 行为、决定
single invocation ownership，并设计迁移和回归合同。

## 8. 计划内验证命令

```sh
python3 .claude/skills/idc-team-config/scripts/prepare_runtime.py \
  --config team-config.yaml --output /tmp/idc-skill-pruning-effective.yaml

python3 tests/test_runtime_integrity.py
python3 tests/test_dispatch_state.py
python3 tests/test_execution_binding.py
python3 tests/test_team_config_migration.py
python3 tests/test_v2_config_ownership.py
python3 tests/test_v2_core_isolation.py
python3 tests/test_final_security_review.py
python3 tests/test_harness.py

python3 <SKILL_CREATOR_ROOT>/scripts/quick_validate.py \
  .claude/skills/<REMAINING_IDC_SKILL>

npm pack --dry-run
git diff --check
```

执行时还必须运行一个仓库内 reachability contract test：它校验 Skill directory、registry
entry、Pack policy skill refs、resolver defaults、runtime artifacts 和 npm dry-run file list
的一致性。所有命令中的真实企业输入均继续使用公开 placeholder。

## 9. 风险与停止条件

- 删除仅在 prose 出现的 token 仍可能破坏 contract tests、skills list 或 package
  surfaces；必须先 RED 后 GREEN。
- “无当前 team binding”不能推断为不可达；Domain Pack default、extension admission 和
  dormant workflow 都必须审计。
- 若清理发现该 placeholder 出现在已 materialize runtime、Domain Pack policy 或公开
  example 的可执行选择中，立即停止并将分类改为 `BLOCKED_REACHABILITY_DECISION`。
- 若把 discovery/brainstorming 结论混入本次 diff，立即拆分为 Unit 2，不得在没有新的
  Technical Plan Confirmation 下改变 raw idea 行为。
