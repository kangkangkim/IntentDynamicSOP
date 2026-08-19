---
name: idc-tran-build
description: Use only as the final D3A build verification after all required DT domains are GREEN; return tran_build PASS/FAIL evidence and route failures to build-error-analyzer.
---

# tran_build Skill

V0 只定义 D3A 最终 build verification 的接口。

## When To Use

Use only when:

- Domain = d3a。
- Human Alignment 已 approved。
- D3A implementation 已完成。
- 所有 required DT domain 已有 GREEN evidence。

Do not use when:

- 任务是 General Coding。
- required DT domain 还没有 GREEN evidence。
- 只是 TR3 / draft spec / alignment 阶段。
- 真实企业命令尚未在保密区绑定，却要求运行真实 `tran_build`。

## 输入

```yaml
tran_build_request:
  working_directory: <ENTERPRISE_REPO_PATH>
  skill_ref: <ENTERPRISE_TRAN_BUILD_SKILL_REF>
```

## Output

```yaml
tran_build_result:
  status: PASS | FAIL | NOT_RUN
  stage: tran_build
  skill_ref: <ENTERPRISE_TRAN_BUILD_SKILL_REF>
  errors: []
  evidence: []
```

## Hard Rules

- D3A completion 要求 `status: PASS`。
- 失败结果必须进入 `build-error-analyzer`。
- 外部环境不能绑定真实企业 skill。
- 真实 `tran_build` 能力（命令与 PASS 判定）只通过 `team-config.yaml`（`bindings.tran_build.skill_ref`）绑定；命令封装在绑定的企业 skill 内部，配置里不出现命令。
- `tran_build` PASS 是 D3A DONE gate，不是 General Coding gate。
