# Mock Script 说明文件 (GENERAL-MOCK-002)

> 本文件是 Intent-Driven Coding harness 的 demo/fixture，用于演示 General Coding lite lane 的执行单元产出。本文件不包含任何真实企业代码、路径、命令或日志。所有具体值均为 placeholder。

## 用途

本说明文件描述一个 mock 脚本（dummy widget 状态查询 mock）的预期行为，供 workflow evidence 演示使用。它本身只是文档，不是可执行脚本，也不接入任何真实业务系统。

## 预期行为（Placeholder）

- 输入：一个 placeholder widget id（`<WIDGET_ID_PLACEHOLDER>`）。
- 输出：返回该 widget 的 mock 状态（`<WIDGET_STATUS_PLACEHOLDER>`）。
- 对未知 widget id，返回一个 placeholder "unknown" 状态。
- 不写入、不修改任何真实业务数据。

## 运行方式（Placeholder）

```
<ENTERPRISE_GENERAL_MOCK_SCRIPT_PLACEHOLDER_COMMAND> --widget-id <WIDGET_ID_PLACEHOLDER>
```

上述命令为 placeholder，不代表任何真实可执行入口。在真实任务中，此处应替换为受影响企业环境中的实际脚本调用。

## 不触碰的范围

- 不触碰任何真实业务代码。
- 不触碰 `.claude/skills/idc-workflow/references/domains/d3a/` 目录。
- 不修改、不覆盖 GENERAL-MOCK-001 已有的 fixture 文件。
- 不依赖任何真实企业路径、命令或日志。

## 安全声明

本文件不含真实企业代码/路径/命令/日志。所有具体值均为 placeholder，符合 placeholder 保密区约定。
