# TODO Next: 保密区落地清单

这份清单用于进入公司保密区后的第一轮落地。

当前外部仓库只包含非敏感 IDC Harness。进入保密区后，不要重新设计 Core，优先做一条最小 D3A vertical slice。

## 总原则

```text
不改 Core
先填 D3A Module
先跑一条 vertical slice
所有完成判断基于工具证据
```

## P0：进入保密区后的第一件事

1. 复制当前仓库到保密区。
2. 运行：

```sh
python3 tests/test_harness.py
```

3. 确认测试通过。
4. 确认仓库里仍然没有外部环境不该带入的内容。
5. 在保密区创建真实绑定分支或工作副本。

## P0：绑定 D3A Knowledge

只先填一条 vertical slice 需要的知识，不要一次填完整 D3A。

优先选择 1-2 个 Layer：

```text
knowledge/d3a/layers/<LAYER>.md
```

填写：

- 职责。
- 边界。
- API 规则。
- 编码模式。
- 禁止模式。
- 典型示例。
- 常见错误。
- DT 指引。

优先选择 1 个 DT Domain：

```text
knowledge/d3a/dt/<DT_DOMAIN>.md
```

填写：

- 目的。
- 范围。
- 测试编写规则。
- RED evidence 规则。
- GREEN evidence 规则。
- 常见失败。

## P0：绑定真实命令

在保密区替换 placeholder：

```text
<ENTERPRISE_DT_BUILD_COMMAND>
<ENTERPRISE_DT_RUN_COMMAND>
<ENTERPRISE_TRAN_BUILD_COMMAND>
<ENTERPRISE_REPO_PATH>
```

涉及文件：

```text
skills/dt-build/SKILL.md
skills/tran-build/SKILL.md
knowledge/d3a/dt/*.md
```

注意：

- 不要把命令写回外部非敏感仓库。
- 命令输出要保留 evidence_ref。
- 完整日志不要塞进 prompt，只保留摘要和引用。

## P0：接入 Repo Context Providers

按统一接口接入：

```text
schemas/repo-context-provider.schema.yaml
```

优先级：

1. `grep`
2. CodeGraph
3. OKL

每个 provider 必须返回：

```text
summary
evidence_ref
confidence
```

默认限制：

```text
max_results <= 10
max_snippet_chars <= 800
```

不要：

- 全仓无边界搜索。
- 把 OKL 全文塞进上下文。
- 把 OKL 当作 test/build evidence。

## P0：选择第一条 D3A Vertical Slice

选择标准：

- 范围小。
- 涉及 1-2 个 D3A Layer。
- 涉及 1 个 DT Domain。
- 能跑出真实 RED / GREEN evidence。
- 能最终跑 `tran_build`。

建议流程：

```text
TR3 / 用户需求
  -> Input Adapter
  -> Domain = d3a
  -> Lane = lite 或 complex
  -> Alignment Pack
  -> Human Alignment approve
  -> Planner
  -> Layer Context Packet
  -> DT RED
  -> Coding
  -> DT GREEN
  -> tran_build
  -> Completion Summary
```

## P0：强制执行拆分规则

D3A 多 Layer 必须拆 packet：

```text
max_layers_per_packet = 1
```

每个 execution unit：

```text
max_change_loc = 500
```

如果超过 500 行：

```text
必须拆分 execution unit
```

每个 execution unit 都必须有自己的 evidence。

## P1：绑定真实 Verification Mapping

外部仓库不能猜：

```text
Coding Layer -> DT Domain
```

进入保密区后逐步沉淀真实 mapping。

先为第一条 vertical slice 填最小 mapping，不要一次铺满。

记录到：

```text
examples/e2e-tr3-d3a/
或保密区专用 examples/<real-slice>/
```

## P1：补 Repo-native Architecture & Rules

从真实仓库加载：

- AGENTS / CLAUDE / README。
- 架构文档。
- OWNERS / CODEOWNERS。
- build / test config。
- lint / CI rules。
- 目录约定。

这些进入：

```text
Planning Constraints
Execution Constraints
Context Packet
```

## P1：跑真实 E2E Demo

参考：

```text
examples/e2e-tr3-d3a/
```

在保密区创建真实版本：

```text
examples/<real-d3a-slice>/
```

至少包含：

- input TR3 / user request。
- normalized request。
- domain / lane decision。
- alignment pack。
- execution plan。
- context packet summary。
- evidence summary。
- completion summary。

## P1：更新测试

在保密区新增测试，验证：

- 真实 provider 能返回 evidence_ref。
- 真实 DT command 能跑出 RED / GREEN。
- `tran_build` PASS 才能 DONE。
- 单个 execution unit 不超过 500 LOC。
- D3A packet 不跨 Layer。
- OKL 不能替代工具 evidence。

保留外部 harness tests：

```sh
python3 tests/test_harness.py
```

## P2：扩展更多 Layer / DT

第一条 vertical slice 成功后，再逐步扩展：

1. 增加更多 Layer knowledge。
2. 增加更多 DT Domain knowledge。
3. 增加真实 build error -> responsible layer 归因规则。
4. 增加更多 TR3 fixture。
5. 增加更多 lane fixture。

不要一次性填完整 D3A。

## P2：团队复制

如果其他团队要接入：

参考：

```text
docs/adoption-guide.md
domains/template-domain/
```

新增：

```text
domains/<team-domain>/module.yaml
```

不要改：

```text
domains/d3a/
IDC Core
```

## Done 标准

第一轮保密区落地完成，需要满足：

- 一条真实 D3A vertical slice 完成。
- 有 Human Alignment 记录。
- 有 Layer Context Packet。
- 有真实 RED evidence。
- 有真实 GREEN evidence。
- 有真实 `tran_build PASS` evidence。
- 有 completion summary。
- 单个 execution unit <= 500 LOC。
- 所有 evidence 都有 evidence_ref。
- 测试通过。

## 不要做

- 不要在保密区第一轮重构 Core。
- 不要一次性填完整 D3A knowledge。
- 不要猜 Coding Layer 到 DT Domain mapping。
- 不要跳过 Human Alignment。
- 不要跳过 RED / GREEN evidence。
- 不要把 OKL 当作 build/test evidence。
- 不要把超过 500 行的改动塞进一个 execution unit。
