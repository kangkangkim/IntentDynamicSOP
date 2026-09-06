# 团队配置 v2

编写或迁移团队配置时，请阅读本参考。

## 唯一配置源

团队只编写一个文件：`team-config.yaml`。Resolver 输出和 `.idc/` 下的运行产物
都是派生状态。Domain Pack 是由该文件选择的可执行模块资产，不是另一份团队配置。

- 已安装的 General Pack 无需团队开发 Domain 资产即可运行。
- 自研 Custom Domain 从
  [`template-domain`](../../idc-workflow/references/domains/template-domain/)
  开始，并随模块维护其 Pack、workflow profile、capability policy、registries、
  knowledge、Skills 和 completion predicate。
- 团队选择——启用的 Domain、Pack ref、binding、extension、Lane override 和
  knowledge ref——始终保留在 `team-config.yaml`。

最小 General 配置位于
[`examples/team-config.v2-minimal.yaml`](../../../../examples/team-config.v2-minimal.yaml).
Custom 示例位于
[`examples/team-config.v2-custom-domain.yaml`](../../../../examples/team-config.v2-custom-domain.yaml).

## v2 所有权图

```yaml
config_version: 2
team: {id: <TEAM_ID>, repo_path: <REPO_PATH>}
domains:
  enabled: [general]
  default: general
  definitions:
    general:
      pack_ref: harness://.claude/skills/idc-workflow/references/domains/general/domain-pack.yaml
bindings: {}
adapter_extensions: []
```

`domains.enabled` 控制加载。省略 `d3a` 即禁用它；禁用 D3A 时，缺失的 D3A
资产树不得影响 Core。启用时，D3A Pack 保留七个固定 Coding Layer。团队可整体替换
DT registry，但 DONE 仍要求每个 effective team DT GREEN 且 `tran_build` PASS。

General 和适用 Lane 的 Custom Domain 使用 `fast`、`lite` 或 `complex`。
`lane.profiles.<lane>` 可替换该 Lane 的 Pack profile，而不会覆盖未指定的 Pack Lane。
在 `ordered` 模式中，每个配置的 step 和 Skill 都是约束性 policy：缺失、额外或重排的
Skill 都不得被授权或在 completion 时接受。

`bindings.<capability>.skill_ref` 替换可执行 Skill ref，且必须可审计。
`adapter_extensions` 增加经验证的原子 capability；它不能取得 Domain routing、Lane
选择、contract、alignment 或 completion 的所有权。

## v1 预览迁移

legacy v1 示例仍是迁移输入，不是推荐的编写入口。迁移只预览一个确定性的 candidate
和 asset bundle：

```sh
python3 .claude/skills/idc-team-config/scripts/migrate_team_config.py \
  --config <V1_TEAM_CONFIG> --preview
```

不存在 `--apply`。工具不得修改源文件、其目录或 `.idc/`。只有 status 为 `READY`、
真实 resolver validation 通过且 semantic parity 通过后，才可单独 materialize 返回的
candidate 和 relative asset。`BLOCKED` 或 `INVALID` 诊断需要人工拥有的 config 决策；
unknown field 永不被静默丢弃。
