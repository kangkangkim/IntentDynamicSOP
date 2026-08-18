# Domain Module Contract

Domain Module 是 IDC 的可插拔领域模块。

D3A 不应该是 IDC Core 的一部分，而应该是第一个 Domain Module。其他团队复制这套 SOP 时，不需要改 core，只需要新增自己的模块：

```text
.claude/skills/idc-workflow/references/domains/<team-domain>/module.yaml
```

## Core 和 Module 的边界

IDC Core 负责：

- Scenario Router。
- Requirement Assessor。
- Contract-first 规则。
- Knowledge Gate。
- TDD State Machine。
- Verification Gate。
- Evidence-based completion。

Domain Module 负责：

- 自己的 route id。
- 自己的 coding layer registry。
- 自己的 test domain registry。
- 自己的 planner schema。
- 自己的 workflow entrypoint。
- 自己的 knowledge root。
- 自己的 agents / skills。
- 自己的 completion gate。

## 一个团队如何接入

新增一个目录：

```text
.claude/skills/idc-workflow/references/domains/<team-domain>/
```

至少提供：

```text
module.yaml
layers.yaml
test-domains.yaml
workflow.md
knowledge/
examples/
```

然后在：

```text
.claude/skills/idc-workflow/references/domains/registry.yaml
```

注册：

```yaml
domain_modules:
  - id: <team-domain>
    module_file: .claude/skills/idc-workflow/references/domains/<team-domain>/module.yaml
    status: active
```

## D3A 的位置

当前 D3A 是一个 active module：

```text
.claude/skills/idc-workflow/references/domains/d3a/module.yaml
```

它引用现有资产：

```text
.claude/skills/idc-workflow/references/registries/d3a-layers.yaml
.claude/skills/idc-workflow/references/registries/dt-domains.yaml
.claude/skills/idc-workflow/references/workflows/d3a-workflow.md
.claude/skills/idc-workflow/references/knowledge/d3a/
.claude/agents/
.claude/skills/
examples/mock-d3a-task/
```

## 复制原则

其他团队复制时应该复用：

- Core workflow 思想。
- Contract-first。
- Knowledge Gate。
- TDD / build gate。
- Evidence-based completion。

其他团队必须替换：

- Domain layer registry。
- Test domain registry。
- Verification mapping。
- Knowledge templates。
- Build / run commands。
- Repo context provider。
- Mock example。

## 禁止事项

- 不要把团队 domain 直接写进 IDC Core。
- 不要让 Scenario Router 知道某个 module 的内部 layer。
- 不要把 test domain 和 coding layer 简化成一对一。
- 不要绕过 API Contract。
- 不要绕过 RED / GREEN evidence。
