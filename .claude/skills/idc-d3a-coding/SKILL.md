---
name: idc-d3a-coding
description: Use only after the IDC workflow selects Domain = d3a and Human Alignment is approved; execute D3A work through fixed layer planning, Layer Context Packets, DT RED/GREEN evidence, and tran_build completion gates.
---

# D3A Coding Skill

当 IDC workflow 选择 `Domain = d3a` 且 Human Alignment 已批准后，使用这个 skill。

D3A 场景使用用户设计的固定 D3A workflow。这个 skill 只能在固定流程内做 layer planning、DT mapping、execution unit 拆分、adapter 绑定和 evidence 收集，不能重排或重新设计 D3A 主流程。

## When To Use

Use when all are true:

- Domain Module Router selects `d3a` / `D3A_CODING`。
- Human Alignment 已 approved。
- D3A contract set 已明确。
- Planner 能在固定 D3A Layer registry 内拆 Layer Context Packet。

Do not use when:

- 需求仍是 rough / raw idea。
- TR3 或 structured requirement 还没有过 Human Alignment。
- 任务是 General Coding。
- 没有 API Contract / Verification Contract。
- 没有 Layer Context Packet。

If the D3A request is rough, route to:

```text
.claude/skills/idc-intent-discovery/SKILL.md
```

If D3A contract / scope / completion gate 不清楚，route to:

```text
.claude/skills/idc-intent-grilling/SKILL.md
```

## 流程

1. 运行 Requirement Assessor。
2. 如果需要，进入 Grill Me / 澄清 placeholder。
3. 产出 D3A Specification。
4. 在 implementation 前 freeze API Contract。
5. Planner 只能在固定 D3A Layer registry 内规划。
6. DT Domain 只能从生效 registry 选择：仓库默认 `dt-domains.yaml`，或 `team-config.yaml.domain.d3a_dt_domains` 非空时整体替换；禁止合并两个来源、禁止 registry 外编造。
7. 构造 dependency DAG。
8. 为每个选中 Coding Layer 创建一个 Layer Context Packet。
9. Implementation 完成前必须确认 RED evidence。
10. 每个 required DT Domain 都必须有 GREEN evidence。
11. 运行 `tran_build`。
12. 只有 `tran_build` PASS 后才能标记 Done。

## Output

```yaml
d3a_execution_result:
  status: done | blocked | needs_fix | escalated
  selected_layers: []
  required_dt_domains: []
  changed_files: []
  red_evidence_refs: []
  green_evidence_refs: []
  tran_build_evidence_ref: <ENTERPRISE_TRAN_BUILD_EVIDENCE_REF>
  completion_summary_ref: <COMPLETION_SUMMARY_REF>
```

## Hard Rules

- 不允许绕过 Human Alignment approval。
- 不允许重排或重新设计用户定义的固定 D3A workflow。
- 不允许使用 General component registry。
- 不允许猜 Coding Layer 到 DT Domain mapping。
- 不允许把 TR3 DT design 当作 RED / GREEN evidence。
- 每个 execution unit 代码变更必须 `<= 500 LOC`。
- 每个 D3A Layer 必须单独 Layer Context Packet。
- DONE 必须同时满足 required DT GREEN 和 `tran_build PASS`。

## 保密区绑定

以下 placeholder 只能在企业保密区替换：

```text
<ENTERPRISE_API_CONTRACT>
<ENTERPRISE_REPO_PATH>
<ENTERPRISE_PLACEHOLDER>
```
