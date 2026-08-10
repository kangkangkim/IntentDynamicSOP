# Placeholder 规则

凡是依赖企业内部信息的内容，都必须使用显式 placeholder。

## 允许使用的 Placeholder

```text
<ENTERPRISE_PLACEHOLDER>
<ENTERPRISE_API_CONTRACT>
<ENTERPRISE_REPO_PATH>
<ENTERPRISE_DT_BUILD_COMMAND>
<ENTERPRISE_DT_RUN_COMMAND>
<ENTERPRISE_TRAN_BUILD_COMMAND>
```

## 不要猜的内容

不要在外部环境猜：

- 内部 API 名称。
- 内部 class / struct 名称。
- 真实源码目录。
- 真实 build flags。
- 真实 DT mapping rules。
- 真实 error patterns。
- 真实 architecture exceptions。

## 安全内容

外部环境可以写：

- 工作流状态机。
- Schema shape。
- Agent 职责边界。
- 非敏感 dummy example。
- Test harness rules。
