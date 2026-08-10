# Mock TR3

## 开发需求描述

为 D3A dummy widget 增加状态读取能力。

## API / 行为语义

新增 `DummyGetWidgetState(dummy_widget_id)`，返回 `READY`、`BLOCKED` 或 `UNKNOWN`。

## DT 设计

需要覆盖：

- `TPRINT`：验证 dummy id 的状态返回。
- `FW`：验证调用路径的 mock 行为。

## 影响范围

涉及 dummy `DO`、`TFE`、`DRV`。

## 验收标准

- 已知 dummy id 返回状态。
- 未知 dummy id 返回 `DUMMY_NOT_FOUND`。
- required DT GREEN。
- `tran_build` PASS。
