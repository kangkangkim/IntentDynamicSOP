# tran_build Skill

V0 只定义 D3A 最终 build verification 的接口。

## 输入

```yaml
tran_build_request:
  working_directory: <ENTERPRISE_REPO_PATH>
  command: <ENTERPRISE_TRAN_BUILD_COMMAND>
```

## 输出

```yaml
tran_build_result:
  status: PASS | FAIL | NOT_RUN
  stage: tran_build
  command: <ENTERPRISE_TRAN_BUILD_COMMAND>
  errors: []
  evidence: []
```

## 规则

- D3A completion 要求 `status: PASS`。
- 失败结果必须进入 `build-error-analyzer`。
- 外部环境不能填写真实 command。
