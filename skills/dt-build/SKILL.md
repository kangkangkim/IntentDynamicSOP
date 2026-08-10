# DT Build Skill

V0 只定义 DT build / run evidence 的接口，不包含真实企业命令。

## 输入

```yaml
dt_build_request:
  domain: TPRINT
  stage: build | run
  working_directory: <ENTERPRISE_REPO_PATH>
  command: <ENTERPRISE_DT_BUILD_COMMAND>
```

## 输出

```yaml
dt_build_result:
  status: PASS | FAIL | NOT_RUN
  stage: dt_build
  command: <ENTERPRISE_DT_BUILD_COMMAND>
  errors: []
  evidence: []
```

## 规则

- 在保密区绑定前，只能使用 `<ENTERPRISE_DT_BUILD_COMMAND>` 和 `<ENTERPRISE_DT_RUN_COMMAND>`。
- 有真实 stdout / stderr 或等价工具输出时，必须保留为 evidence。
- 不允许把模型自信转换成测试 evidence。
