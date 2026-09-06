# npm 发布准备技术计划（不执行发布）

日期：2026-09-06
任务：`idc-npm-release-readiness`
路由：General Domain / Lite Lane
执行单元：`unit-1-npm-release-readiness`

## 已确认的范围

用户在已明确列出以下发布准备项后回复“可以”。本记录将该文本作为本计划的
Technical Plan Confirmation：允许完成 npm 发布**准备**，但不允许执行 `npm publish`、
写入任何 registry、创建 tag/release，或删除、覆盖无关的用户改动。

用户确认的五项是：

1. 修正 installer 测试与 v2 模板、`--team` 参数的真实行为，并使测试通过；
2. 明确私有或公开 registry 的发布策略；
3. 明确许可证策略；
4. 补齐版本、变更日志、`publishConfig`、包完整性和安装回归检查；
5. 明确 Node.js 支持门槛（当前为 `>=18`）。

确认记录：

```yaml
technical_plan_confirmation:
  status: confirmed
  confirmation_channel: explicit_user_text
  user_message: "可以"
  confirmed_at: "2026-09-06"
  confirmed_objects: [technical_plan, installer_cli_contract, package_contract]
  model_self_attested: false
  scope: npm_release_readiness_only
  forbidden_actions: [npm_publish, registry_write, git_tag, release_creation]
```

## 当前已知问题与目标

当前 CLI 已实现 `idc install --team <id>`，但 `tests/test_installer.mjs` 仍以旧
模板形状断言 `id: payments`；v2 模板实际需要验证其 `team.id` 的填充位置和 runtime
preflight。目标是让安装器契约、模板和包内容以同一事实源运行，并验证打出的 tarball
可以在全新临时项目中安装和执行。

## API / CLI Contract

```text
idc install --team <TEAM_ID> --directory <TARGET> --json
```

成功时必须：

- 创建 `<TARGET>/team-config.yaml`，其中 v2 `team.id == normalized(<TEAM_ID>)`；
- 不覆盖已有 `team-config.yaml`；
- 在未传 `--skip-runtime` 时生成 `<TARGET>/.idc/effective-team-config.yaml`，且
  `runtime_preflight.status == READY`；
- 保留 `.cac -> .claude` 与 `AGENTS.md -> CLAUDE.md` 的既有安装契约；
- `--json` 输出保持 machine-readable，失败以非零退出码表示；
- `idc doctor` 对刚安装项目返回 `READY`。

包契约：

- `npm pack --json` 生成的 tarball 必须包含 CLI、installer、所有运行时所需 IDC
  assets、`team-config.yaml.template`、规则文件和 hook settings；
- tarball 不得包含 `.idc` 运行产物、缓存、测试临时文件或无关开发资产；
- 在临时目录 `npm install <tarball>` 后，`node node_modules/idc-harness/dist/bin/idc.js
  install --team <TEAM_ID>` 与 `doctor` 都必须满足以上契约；
- 发布策略默认为私有 npm registry；除非在后续单独确认公开发布和许可证，不得设置为
  公开发布或执行 publish。

## 执行步骤与 TDD

1. 先扩展/修正 installer contract test，使它读取 YAML 的 v2 `team.id`，并加入模板、
   existing-config preservation、runtime READY 的断言。此提交前测试必须可复现旧的
   RED（旧断言与 v2 template 不一致）。
2. 修复 `dist/installer/core.js` 或模板替换逻辑，只在实际问题存在时改动；保留现有
   `--team` 正规化规则。执行 installer test 至 GREEN。
3. 扩展 `tests/test_package_contract.mjs`：检查版本、Node engine、许可证/registry
   publishing policy、files allowlist 和 tarball manifest 的安全边界。
4. 如当前 whitelist 无法精确排除开发资产，新增最小 `.npmignore`；若 `files` 已足够，
   不新增该文件。不要为了方便把整个仓库纳入 tarball。
5. 只在必要时修改 `package.json`、`README.md`、`dist/bin/idc.js`，让文档、CLI help
   和 package metadata 对齐。README 必须说明私有发布是默认策略、公开发布须单独决定
   许可证与 registry；不得宣称已经发布。
6. 增加 tarball 临时安装 smoke test：`npm pack` 到临时目录，临时安装该 tarball，运行
   install/doctor；测试结束清理临时目录，绝不写任何 registry。
7. 运行 targeted RED/GREEN、`npm test`、`npm pack --dry-run`、实际本地 `npm pack --json`
   smoke test、`git diff --check`。记录命令输出和包清单。

## 允许修改与禁止修改

允许路径：

- `package.json`
- `README.md`
- `.npmignore`（仅在步骤 4 证明必要时）
- `dist/bin/idc.js`
- `dist/installer/core.js`
- `tests/test_installer.mjs`
- `tests/test_package_contract.mjs`
- 最小的新测试或发布 CI 文件（仅必要时）
- `.idc/runs/idc-npm-release-readiness/attempt-1/` 下的本次证据

禁止：`npm publish`、`npm access`、registry 写入、git tag/release、删除用户文件、修改
`team-config.yaml`、修改 IDC runtime/skills 或与包装无关的产品文件。

## 完成条件

- installer 的 `--team` v2 contract 有 RED 与 GREEN 证据；
- 完整 `npm test` 通过；
- `npm pack --dry-run` 和本地 tarball 安装 smoke test 通过；
- tarball manifest 满足 allowlist / exclude policy；
- README 说明 Node 门槛、私有 registry 默认策略和未执行发布的边界；
- Execution Receipt 引用授权、真实 subagent dispatch、测试证据与变更路径。
