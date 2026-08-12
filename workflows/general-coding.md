# General Coding Workflow

General Coding 用于已注册专用 domain module 之外的普通 coding 任务。

它是 active Domain Module：

```text
domains/general/module.yaml
```

## 流程

```text
Input Adapter
  -> Intent Maturity Router
  -> intent-discovery if raw_idea
  -> intent-grilling if needed
  -> Domain Module Router selects general
  -> Lane Resolver
  -> Contract Gate
  -> intent-alignment
  -> General Plan
  -> Knowledge Gate
  -> Execution Unit <= 500 LOC
  -> TDD / Verification
  -> Completion Gate
```

## Component Registry

General Coding 不使用 D3A Layer registry。

它使用：

```text
registries/general-components.yaml
```

V0 components 是 placeholder，不代表真实团队分类：

```text
GENERAL_COMPONENT_PLACEHOLDER
GENERAL_COMPONENT_SECONDARY_PLACEHOLDER
GENERAL_COMPONENT_SUPPORT_PLACEHOLDER
```

## Test Domain Registry

General Coding 不使用 D3A DT Domain registry。

它使用：

```text
registries/general-test-domains.yaml
```

V0 test domains 是 placeholder，不代表真实团队测试体系：

```text
GENERAL_TEST_PLACEHOLDER
GENERAL_TEST_SECONDARY_PLACEHOLDER
GENERAL_CHECK_PLACEHOLDER
```

## Completion Gate

General completion 要求：

- task contract satisfied。
- verification contract satisfied。
- required tests or builds PASS。
- completion summary exists。
- evidence_ref exists。

## API Contract

API Contract 不是所有 General Coding 都必须要。

只有当任务涉及 API、外部行为、数据结构、错误语义或兼容性时才要求。

## 规则

- 不使用 D3A Layer / DT Domain registry。
- 不编造 General component / test domain taxonomy；进入真实团队后再替换 placeholder。
- 每个 execution unit 代码变更 `<= 500 LOC`。
- 如果 verification contract 要求测试，必须先 RED 再 GREEN。
- Completion 必须基于工具 evidence。
- 外部环境只能使用 placeholder 命令和路径。
