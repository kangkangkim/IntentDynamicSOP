# Team Rollout Playbook

目标：每个团队复制同一份 IDC Core，只维护自己的 `team-config.yaml`。

## 最小接入

```yaml
config_version: 1
team: {id: payment-team, repo_path: /repos/payment}
domain: {mode: general}
bindings: {}
```

调用 `idc-workflow` 时，框架自动运行 Team Config Preflight，生成只读
`.idc/effective-team-config.yaml`。团队不运行生成步骤，也不编辑 `.idc/`。
Preflight 还会把每个 Lane step 和 required Skill 送入真实 Capability Selector
做 dry-run，验证配置的选择结果与顺序确实生效。
它同时运行 Skill Registration Audit：重复覆盖同一 capability/stage/scope/trigger
的 Skill 默认视为冲突；只有明确声明 `composes_with` 或 `supersedes` 才能通过。

## 逐级采用

1. **Level 1 - General**：填写 team、General Domain 和实际可运行的 bindings。
2. **Level 2 - Team SOP**：配置 Fast/Lite/Complex 各自的 Skill policy、steps 和 budget。
3. **Level 3 - Domain**：选择 D3A，或在同一 YAML 内定义 Custom Domain、知识索引和 completion skills。

每一级都仍然只有一个团队配置文件；未启用能力不需要填 `null` 槽位。

## 可移植路径

| 写法 | 解析位置 | 用途 |
|---|---|---|
| `'team://skills/x/SKILL.md'` | `team.repo_path` | 团队内部 Skill |
| `'harness://.claude/skills/x/SKILL.md'` | IDC Core 根目录 | 共享 Skill |
| `skills/x/SKILL.md` | team repo 优先，Core 其次 | 简洁相对路径 |
| `/absolute/path/SKILL.md` | 原路径 | 单仓固定部署 |

Resolver 把文件引用绝对化后才交给 Selector 和 Adapter Router，因此运行结果
不依赖启动命令的当前目录。本地 knowledge refs 使用同一规则并验证存在性；
`https://` 等显式 URI 保持原样。

## 团队验收

推广前每个团队至少通过：

1. Preflight 返回 `READY`，生成 `source_sha256`，且 bootstrap load plan 只有三个 Router 引用。
2. 所有已配置 Skill 路径存在；错误路径必须返回 `NEEDS_TEAM_CONFIG`。
3. Fast、Lite、Complex 各跑一个 capability demand，选择结果符合团队配置。
4. ordered Lane 缺少当前 stage 时返回 `NEEDS_ORCHESTRATION_MAPPING`。
5. deny 的 Skill 不会被默认 Registry 补回。
6. Execution Context Load Plan 只包含 Domain protocol、共享 gate 和 Selector 实际选中的 Skill。
7. 一个最小 vertical slice 产生真实 test/build evidence 并通过 Completion Gate。

CI 可额外执行：

```sh
ruby .claude/skills/idc-team-config/scripts/prepare_runtime.rb
python3 tests/test_harness.py
```

## 多团队复制边界

复制 IDC Core、schema、Resolver、Selector 和测试。不要复制另一个团队填好的
`team-config.yaml`、`.idc/`、企业知识正文、日志或真实命令。新团队从模板或生成器
创建自己的 YAML；命令继续封装在企业 Skill 内。
