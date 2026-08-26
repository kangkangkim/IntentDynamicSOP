---
name: idc-dt-build
description: Use inside D3A verification when a selected DT domain needs build/run evidence; return tool evidence only and never invent enterprise commands.
---

# DT Build Skill

V0 只定义 DT build / run evidence 的接口，不包含真实企业命令。

## When To Use

Use only when:

- Domain = d3a。
- Human Alignment 已 approved。
- D3A plan 已选择 required DT domain。
- 需要 DT RED 或 GREEN evidence。

Do not use when:

- 任务是 General Coding。
- 没有 selected DT domain。
- 还没有 API Contract / Verification Contract。
- 真实企业命令尚未在团队配置内绑定，却要求运行真实 DT。

## 输入

```yaml
dt_build_request:
  domain: TPRINT
  stage: build | run
  working_directory: <ENTERPRISE_REPO_PATH>
  skill_ref: <ENTERPRISE_DT_BUILD_SKILL_REF>
```

## Output

```yaml
dt_build_result:
  status: PASS | FAIL | NOT_RUN
  stage: dt_build
  skill_ref: <ENTERPRISE_DT_BUILD_SKILL_REF>
  errors: []
  evidence: []
```

## Hard Rules

- 在接入团队配置前，只能使用 `<ENTERPRISE_DT_BUILD_SKILL_REF>` placeholder，不得编造命令。
- 真实构建能力只通过 `team-config.yaml`（`bindings.dt_build.skill_ref`）绑定；真实命令封装在绑定的企业 skill 内部，配置里不出现命令，也不从其他文件读取。
- 有真实 stdout / stderr 或等价工具输出时，必须保留为 evidence。
- 不允许把模型自信转换成测试 evidence。
- 失败结果必须进入 `build-error-analyzer` 或回到 targeted fix。
