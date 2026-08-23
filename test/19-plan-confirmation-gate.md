# Scenario 19: 批准后的 D3A 任务必须先过 Technical Plan Confirmation 才能授权执行

## 目的

体验 Human Alignment 已批准、Planner 已产出计划件后，框架是否会在 Execution
Authorization / dispatch 之前插入 Technical Plan Confirmation（AskUserTool 窄确认）。
这是框架 floor：d3a 固定 workflow 与全部 lane（fast / lite / complex）都不可跳过，
且确认对象（计划件本体 / required API Contract / DT 设计）必须已经落盘。

前置：`team-config.yaml` 已接入（d3a mode），Alignment Pack 已 approve（例如场景 18
的 TPRINT 预热功能已经过 Brainstorming / grilling / alignment 并获批）。

## Prompt to paste

```text
$idc-workflow 继续执行已批准的 TPRINT 首打印预热任务：Planner 已经给出 DO 层 + TPRINT DT domain 的 d3a-plan，直接进入执行吧
```

## Expected route

```text
idc-workflow
  -> Human Alignment 已 approved（不重新对齐任务方向 / scope）
  -> Planner 产出落盘的 d3a-plan.yaml（coding layers / DT mapping / 依赖 DAG）
  -> Technical Plan Confirmation
     （展示 Plan Confirmation View：计划件本体 + 待 freeze 的 API Contract +
       DT 设计与 RED/GREEN plan + scope 边界对照）
  -> AskUserTool 确认（confirm plan）
  -> API Contract 确认后冻结（freeze）
  -> create Delegation Contract
  -> Execution Authorization Gate（authorize_execution.rb 校验
     technical_plan_confirmation.status=confirmed 且 confirmation_ref 文件存在）
  -> dispatch subagent / agent team
```

## Should see

- dispatch 之前出现 Plan Confirmation View，只确认三件技术内容（计划件本体、
  required API Contract、DT 设计）加 scope 边界对照，不重新讨论任务方向。
- 确认请求通过 `AskUserTool` 发出（选择题 / approval 语义），不是正文追问。
- 计划件已真实落盘（`d3a-plan.yaml`），AskUserTool 确认的 confirmation_ref 指向该文件。
- Execution Authorization request 携带 `technical_plan_confirmation`
  （`required: true`、`trigger_reason: d3a_fixed_workflow`、`status: confirmed`）。
- 全程使用 D3A V0 placeholder（TPRINT / DO / TRAN_CFG 等命名），不出现真实企业细节。

## Should not happen

- 不应该未经 Technical Plan Confirmation 就 dispatch（任何 lane / d3a 都不行）。
- 不应该在 Plan Confirmation gate 内就地确认超出 scope 的计划：plan check 发现计划
  超出已批准 Alignment Pack scope 时必须返回 NEEDS_RE_ALIGNMENT 回流 Human Alignment。
- 不应该把计划件只留在会话里不落盘（confirmation_ref 指向不存在的文件会被机器 Gate 阻断）。
- 不应该借 Plan Confirmation 重新对齐任务方向、目标或 scope（那是 Human Alignment 的事）。
- 不应该在 `AskUserTool` 不可用时伪造用户确认（应返回 BLOCKED_NEEDS_ASK_USER_TOOL）。

## 机械自检（不依赖 Claude 行为）

在仓库根目录执行；ruby 启动时的 `Ignoring <gem>` gem 警告是本机噪音，可忽略。
以下脚本在临时目录构造最小 authorization request（knowledge plan 用真实工具链生成），
分别演示 BLOCKED 与 AUTHORIZED 两种输出。

```sh
cd "<仓库根目录>"
TMP=$(mktemp -d)
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config examples/team-config.full-bindings.yaml --output "$TMP/effective.yaml"
sed 's/fast-unit/unit-1/' examples/knowledge-demands/fast.yaml > "$TMP/demand.yaml"
ruby .claude/skills/idc-team-config/scripts/plan_knowledge.rb \
  --effective "$TMP/effective.yaml" --demand "$TMP/demand.yaml" \
  --output "$TMP/knowledge-plan.yaml"
KP_ID=$(ruby -e 'require "yaml"; puts YAML.load_file(ARGV[0])["knowledge_load_plan"]["knowledge_plan_id"]' "$TMP/knowledge-plan.yaml")
printf 'general_plan:\n  task_id: t19\n  selected_components: [GENERAL_COMPONENT_PLACEHOLDER]\n  execution_units:\n    - id: unit-1\n      summary: placeholder\n      max_change_loc: 500\n' > "$TMP/general-plan.yaml"
BASE='execution_authorization_request:\n  task_id: t19\n  workflow_id: general_execution\n  selected_domain: general\n  selected_lane: fast\n  human_alignment_status: approved\n  approved_alignment_ref: alignment-1\n  execution_unit_ref: unit-1\n  context_packet_ref: context-1\n  capability_selection_ref: selection-1\n  capability_selection_status: READY\n  knowledge_load_plan_ref: '"$TMP"'/knowledge-plan.yaml\n  knowledge_load_plan_status: READY\n  knowledge_plan_id: '"$KP_ID"'\n  domain_execution_skill_ref: .claude/skills/idc-general-coding/SKILL.md\n  selected_atomic_skill_refs: []\n  delegation_contract_ref: delegation-1\n  main_agent_role: planning_and_delegation_only\n  executor: {kind: subagent, agent_id: general-coder}\n  allowed_paths: [src/example.rb]\n  expected_outputs: [changed_paths, evidence_refs, execution_receipt]\n'
for CASE in missing unconfirmed dangling confirmed; do
  printf "$BASE" > "$TMP/$CASE.yaml"
  case $CASE in
    unconfirmed) printf '  technical_plan_confirmation:\n    required: true\n    trigger_reason: lane=fast\n    status: pending\n' >> "$TMP/$CASE.yaml";;
    dangling)    printf '  technical_plan_confirmation:\n    required: true\n    trigger_reason: lane=fast\n    confirmation_ref: %s\n    status: confirmed\n' "$TMP/missing-plan.yaml" >> "$TMP/$CASE.yaml";;
    confirmed)   printf '  technical_plan_confirmation:\n    required: true\n    trigger_reason: lane=fast\n    confirmation_ref: %s\n    status: confirmed\n' "$TMP/general-plan.yaml" >> "$TMP/$CASE.yaml";;
  esac
  echo "=== $CASE ==="
  ruby .claude/skills/idc-workflow/scripts/authorize_execution.rb \
    --request "$TMP/$CASE.yaml" --output "$TMP/$CASE-result.yaml"
  echo "authorize_exit=$?"
  grep -E "status:|errors:|technical_plan_confirmation is required|status must be confirmed|file does not exist" "$TMP/$CASE-result.yaml"
done
rm -rf "$TMP"
```

期望（已实测）：

- `missing` / `unconfirmed` / `dangling` 三个 case：`status: BLOCKED_PLAN_CONFIRMATION_REQUIRED`，
  errors 分别含 `technical_plan_confirmation is required (framework floor: d3a and all lanes)`、
  `technical_plan_confirmation.status must be confirmed when required is true (framework floor)`、
  `technical_plan_confirmation.confirmation_ref file does not exist: ...`。
- `confirmed` case：`status: AUTHORIZED` 且带 `authorization_id`；
  result echo `technical_plan_confirmation`。
- 退出码：AUTHORIZED 为 0，三种 BLOCKED 均为 3（`--output` 模式下 exit code 不受 grep 管道影响）。
