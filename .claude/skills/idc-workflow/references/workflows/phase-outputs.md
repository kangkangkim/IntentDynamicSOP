# Phase Outputs

每个 phase 的「必须存在的输出件」统一清单。本文件不发明新规则，只汇总既有
schema / workflow / 脚本已经要求的落盘产物；规则出处标在每条之后。

逐 phase 自检：进入下一个 phase 前，对应产物必须真实存在于
`.idc/runs/<task-id>/attempt-<n>/`（或示例目录的等价位置），机器可校验。

## bootstrap

| 输出件 | 规则出处 |
|---|---|
| `effective-team-config.yaml`（`.idc/`，框架生成） | `scripts/prepare_runtime.py`；`idc-workflow/SKILL.md` Required behavior |
| `runtime_preflight.status: READY` | `idc-workflow/SKILL.md`（Continue only when READY） |

## decision（pre-alignment → Human Alignment）

| 输出件 | 规则出处 |
|---|---|
| `alignment-pack.yaml`（status: approved） | `schemas/alignment-pack.schema.yaml`；`workflows/human-alignment.md` |
| Domain / Lane decision（d3a 固定 `not_applicable`） | `references/domains/d3a/module.yaml`；`workflows/domain-module-router.md` |

## planning

| 输出件 | 规则出处 |
|---|---|
| **计划件本体（硬性，新增钉死）**：`general-plan.yaml` 或 `d3a-plan.yaml`。计划件必须落盘并符合对应 schema；`execution_authorization_request.technical_plan_confirmation.confirmation_ref` 必须指向这个文件，`authorize_execution.py` 校验其存在——文件缺失即 `BLOCKED_PLAN_CONFIRMATION_REQUIRED`，这就是强制点。 | `schemas/general-plan.schema.yaml`；`schemas/d3a-plan.schema.yaml`；`workflows/execution-authorization-gate.md` |
| Technical Plan Confirmation 记录（三件已确认：计划件 + required API Contract + DT 设计） | `workflows/execution-authorization-gate.md`；`workflows/ask-user-tool-policy.md` |
| capability plan（READY） | `schemas/capability-selection.schema.yaml`；`scripts/select_capabilities.py` |
| knowledge plan（READY，绑定 execution unit） | `schemas/knowledge-load-plan.schema.yaml`；`scripts/plan_knowledge.py` |

计划件落盘是 planning phase 的完成条件：不落盘就无法通过 Execution
Authorization，也不允许只在会话里「口头」存在一个计划。

## execution（逐 execution unit）

| 输出件 | 规则出处 |
|---|---|
| delegation contract（逐 EU） | `schemas/delegation-contract.schema.yaml`；`workflows/delegation-router.md` |
| execution-authorization request + result（含 `technical_plan_confirmation` echo） | `schemas/execution-authorization.schema.yaml`；`scripts/authorize_execution.py` |
| context packet（D3A 逐 Layer，General 逐 EU） | `schemas/layer-context-packet.schema.yaml`；`workflows/progressive-constraint-loading.md` |
| knowledge consumption receipt（completion 前 VERIFIED） | `scripts/verify_knowledge_consumption.py` |

## completion

| 输出件 | 规则出处 |
|---|---|
| completion result / summary（`DONE` 只能来自工具判定） | `scripts/verify_completion.py`；`schemas/completion-verification.schema.yaml` |
| evidence（RED / GREEN / build / tran_build 等工具证据） | `schemas/verification-contract.schema.yaml`；`workflows/lane-completion.md`；d3a 另见 `idc-d3a-coding/SKILL.md` |
| execution receipt（authorization ID + dispatch tool-call ref + executor session ref） | `schemas/execution-authorization.schema.yaml`；`workflows/execution-authorization-gate.md` |

## resume

| 输出件 | 规则出处 |
|---|---|
| runtime-state checkpoint（latest_event / resume_from / evidence ledger） | `schemas/runtime-state.schema.yaml`；`workflows/resume-policy.md` |
| Plan confirmed checkpoint（中断后 dispatch 前必须可证明已确认） | `workflows/resume-policy.md`（Plan confirmed 紧跟 Plan created） |
