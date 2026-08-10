# Adoption Guide

这份文档给其他团队复制 IDC SOP 使用。

核心原则：

```text
复制 IDC Core
新增自己的 Domain Module
不要改 D3A
不要改 Core
```

## 适合使用的团队

适合：

- 有固定领域架构。
- 有相对稳定的测试/构建闭环。
- 希望把需求澄清、规划、执行、验证标准化。
- 希望把领域 SOP 做成可插拔模块。

不适合：

- 没有稳定代码仓。
- 没有任何可运行测试或构建证据。
- 领域规则完全依赖口头经验且暂时无法沉淀。

## 新增 Domain Module

复制模板：

```text
domains/template-domain/
```

新建：

```text
domains/<team-domain>/
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

注册到：

```text
domains/registry.yaml
```

示例：

```yaml
domain_modules:
  - id: payment
    module_file: domains/payment/module.yaml
    status: active
```

## 必须定义

每个团队必须定义：

- route trigger rules。
- layer registry。
- test domain registry。
- required contracts。
- planner schema。
- knowledge root。
- completion gate。
- repo context provider 接入方式。
- token budget。
- 第一条 mock vertical slice。

## 不要改

- 不要改 D3A module。
- 不要把团队领域写进 IDC Core。
- 不要绕过 Human Alignment。
- 不要绕过 Lane Completion。
- 不要绕过 Evidence-based Completion。

## 第一周落地建议

1. 复制 `domains/template-domain/`。
2. 填 2-3 个 Layer placeholder。
3. 填 1-2 个 Test Domain placeholder。
4. 写一个 mock TR3。
5. 产出 Alignment Pack。
6. 产出一个 execution plan。
7. 绑定一个最小 repo context provider。
8. 跑一个小闭环 demo。
9. 加 fixture 测试。

## 成功标准

第一条 vertical slice 成功即可：

```text
Input/TR3
  -> normalized_request
  -> domain/lane decision
  -> alignment_pack
  -> plan
  -> context_packet
  -> evidence
  -> completion_summary
```
