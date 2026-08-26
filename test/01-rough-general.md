# Scenario 01: Rough General Request

## 目的

体验 `rough general` 是否会先进入 `idc-intent-discovery` / Brainstorming，而不是直接开始 General Coding。

## Prompt to paste

```text
用 id-workflow 处理一下：我想做一个 general coding 的小工具，大概就是帮我整理项目里的 TODO，先试试看，还没想清楚具体交互和验收标准。
```

## Expected route

```text
id-workflow
  -> Skill-level maturity routing
  -> input_maturity = raw_idea
  -> idc-brainstorming
  -> idc-intent-discovery
  -> Brainstorming View
  -> draft spec
  -> idc-intent-grilling
  -> idc-intent-alignment
```

## Should see

- 中文 Brainstorming View。
- 2-3 个可能方案或关键探索问题。
- 明确说明 draft spec 不是 approved contract。

## Should not happen

- 不应该直接进入 `idc-general-coding`。
- 不应该直接写代码。
- 不应该直接创建 execution unit。
