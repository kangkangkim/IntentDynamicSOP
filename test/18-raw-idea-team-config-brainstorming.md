# Scenario 18: 企业 team-config 下的 raw idea（目标词陷阱：不能跳过 Brainstorming）

## 目的

体验企业 team config 已接入（d3a mode）时，一条**带目标词但无行为语义 / 无验收标准**
的 raw idea 是否会被误判成 structured_requirement，从而跳过 Discovery / Brainstorming。
这是最危险的形态：prompt 里有 domain 名（TPRINT）、有目标词（"想让第一次打印别那么慢"），
看起来"方向很明确"，但行为语义和验收标准完全缺失——诚实分类必须是 raw_idea，
必须先走 alignment-discovery → idc-brainstorming 发散出方案，再进 grilling / alignment。

前置：`team-config.yaml` 已接入（d3a mode），alignment 管线为框架默认五步链
（discovery/raw_idea → brainstorming/raw_idea+alternatives_needed →
grilling/critical_gaps_remain+clarification_required+tr3_input →
grilling-with-docs/docs_clarification_required → alignment_check/无信号）。

## Prompt to paste

```text
$idc-workflow 我想给 TPRINT 加个首打印预热功能，大概想让第一次打印别那么慢，具体怎么做还没想清楚，你先帮我看看怎么弄
```

## Expected route

```text
idc-workflow
  -> Skill-level maturity routing
  -> input_maturity = raw_idea
     （有目标词但无行为语义、无验收标准 → 不是 structured_requirement）
  -> alignment-discovery（idc-intent-discovery）
  -> idc-brainstorming（2-3 个方案 + draft spec + Brainstorming View）
  -> idc-intent-grilling（默认 Grill Me；docs_needed 时换 idc-intent-grilling-with-docs）
  -> idc-intent-alignment（Alignment View）
  -> AskUserTool approval（人类批准后才进 D3A workflow）
```

## Should see

- Brainstorming View 展示 2-3 个可能方案和取舍（例如预热触发的时机、预热范围、
  对首打印之外路径的影响），而不是单一方案直接开做。
- 明确产出 draft spec，并声明 draft spec 不是 approved contract。
- 后续 Grill 问题（缺口澄清）通过 AskUserTool 发出，不混在正文里追问。
- 全程使用 D3A V0 placeholder（TPRINT / FW / DPF、TRAN_CFG 等命名），不出现真实企业细节。

## Should not happen

- 不应该因为 prompt 里出现了目标词（"想让第一次打印别那么慢"）或 domain 名（TPRINT）
  就判成 structured_requirement，跳过 Discovery / Brainstorming。
- 不应该不展示 Brainstorming View 直接进 Clarification / Alignment View。
- 不应该跳过 grill（idc-intent-grilling / idc-intent-grilling-with-docs）直接展示 Alignment View。
- 不应该在 AskUserTool approval 之前写任何代码（D3A task 在 approval 前不得进入 execution）。

## 机械自检（不依赖 Claude 行为）

在仓库根目录执行；ruby 启动时的 `Ignoring <gem>` gem 警告是本机噪音，可忽略。

### 1. team config 接入确认（READY）

```sh
cd "<仓库根目录>"
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config team-config.yaml --output /tmp/effective.yaml
echo "exit=$?"
```

期望（已实测）：stdout 以 `READY` 开头（`--output` 模式打印 `READY: wrote /tmp/effective.yaml`）、
exit=0。

### 2. raw_idea 诚实信号检查（修复前缺陷（历史）已修复）

```sh
ruby .claude/skills/idc-team-config/scripts/plan_context.rb \
  --effective /tmp/effective.yaml --phase decision --domain d3a \
  --signal raw_idea --signals-complete
```

期望（已实测，修复后）：

- refs 含 `.claude/skills/idc-intent-discovery/SKILL.md`、
  `.claude/skills/idc-brainstorming/SKILL.md` 与
  `.claude/skills/idc-intent-alignment/SKILL.md`；
  `matched_step_ids` 含 `alignment-discovery` / `alignment-brainstorming` /
  `alignment-check`，其余两步进 `skipped_step_ids`。
- `alignment_resolution` 新增 `alignment_check_gate: pre_alignment_signals_resolved`，
  `steps` 数组按 step 标注 `must_execute` / `always_run` / `skipped_by_signal`。
- **修复前缺陷（历史）**：`.claude/skills/idc-brainstorming/SKILL.md` 曾不在 refs——
  alignment-brainstorming step 只认 `alternatives_needed`，而该信号没有任何产出义务方
  （诚实报告 raw_idea 的任务点亮不了 brainstorming step）。已由本次修复解决：
  触发信号改为 `[raw_idea, alternatives_needed]`、匹配语义改为 any-of，
  `tests/test_harness.py` 的 `test_raw_idea_signal_must_light_brainstorming_step`
  已由 RED 转 GREEN。

### 3. uncertain fallback 检查（不传 signal）

```sh
ruby .claude/skills/idc-team-config/scripts/plan_context.rb \
  --effective /tmp/effective.yaml --phase decision --domain d3a
```

期望（已实测）：五个 intent/grilling SKILL.md 全量进入 required_refs
（idc-intent-discovery、idc-brainstorming、idc-intent-grilling、
idc-intent-grilling-with-docs、idc-intent-alignment），且含 `signal_set: uncertain`、
`fallback_reason: signal set not declared complete; loaded full configured alignment pipeline`——
uncertain 时全量加载，没有 must-execute 区分。

### 备注

步骤 2 的 brainstorming 缺失即 `tests/test_harness.py` 中
`test_raw_idea_signal_must_light_brainstorming_step` 的 RED 证据：
修复 `plan_context.rb` 的信号匹配前，该测试保持失败（GREEN 部分
`test_raw_idea_decision_plan_pins_pre_alignment_reachability` 钉住的是当前正确行为，
两条互相独立）。验证完 `rm -f /tmp/effective.yaml` 即可。
