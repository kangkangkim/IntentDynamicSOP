# GitHub 上传技术计划

状态：`CONFIRMED`
日期：2026-09-06
任务：`idc-github-publish`
路由：General Domain / Lite Lane
目标分支：`codex/IntentDyanmicHarnessV2`
远端：`origin`（`git@github.com:kangkangkim/IntentDynamicSOP.git`）

## 用户确认与边界

用户明确请求“帮我上传到云端 GitHub”。这授权创建一个普通 commit 并将当前工作区的
非忽略产品、测试、文档、示例与计划文件推送到上述同名远端分支。开始前确认该远端分支
不存在。

```yaml
technical_plan_confirmation:
  status: confirmed
  confirmation_channel: explicit_user_text
  user_message: "帮我上传到云端 GitHub"
  confirmed_at: "2026-09-06"
  confirmed_objects: [technical_plan, git_publish_contract, verification_contract]
  model_self_attested: false
```

严格禁止：`--force` / `--force-with-lease`，tag、GitHub release、PR、merge、registry
写入、`npm publish`、删除任何文件，以及执行 pending skill-pruning 的删除动作。

## Git Publish Contract

执行器必须：

1. 在暂存前运行 secret/private hygiene、placeholder hygiene、`git diff --check`、全量
   tests 和 npm package checks；任一必需检查失败时停止，不暂存、不提交、不推送。
2. 以 `git ls-files --modified` 与 `git ls-files --others --exclude-standard` 在执行时重新
   生成精确候选集；只暂存该集合内的非忽略文件。
3. 明确排除所有 ignored 文件和运行态文件，至少包含 `team-config.yaml`、`.idc/`、
   `settings.local`、`node_modules/`、`*.tgz`、`desktop-pet/demo-project/`；这些文件即使
   在磁盘存在也不得 `git add -f`。
4. 暂存后先审查 `git diff --cached --check` 与 `git diff --cached --name-only`；若范围与
   本计划不一致，清晰报告并停止。
5. 使用建议 message：`feat: add deterministic team-config v2 runtime` 创建普通 commit。
6. 仅在 commit 成功后推送：

   ```sh
   git push origin HEAD:refs/heads/codex/IntentDyanmicHarnessV2
   ```

   不得 force；不得覆盖远端其他引用。

## 当前允许集合

以执行时重新计算的 nonignored 工作区为准，当前预览包含：

- 已跟踪修改：IDC team-config/runtime/workflow 源、`CLAUDE.md`、`QUICKSTART.md`、
  `README.md`、installer、三份现有文档、v2 template、harness/installer/package tests；
- 未跟踪源：新增 team-config references 与 runtime scripts、D3A/General/template Domain
  Pack assets、新 schema、架构 HTML、v2 examples、新测试；
- 未跟踪计划：`plans/` 下的所有非忽略计划文件，包括本文件。

`.idc` 是 ignored evidence，不属于 commit 候选集；它仅保存授权和验证证据。

## 验证顺序

1. `git status --short`、ignored-file audit、secret/private hygiene 和 placeholder hygiene；
2. `git diff --check`；
3. `python3 tests/test_harness.py` 与 `npm test`；
4. `npm pack --dry-run`，并执行 package contract / installer checks；
5. 仅当上述均 PASS 时执行精确暂存、staged diff inspection、commit、non-force push；
6. 返回 commit SHA、push ref、精确 staged path 清单和每项检查证据。

如果既有检查失败，执行器必须保留工作区并以 `blocked` 返回；不能通过删测试、放宽断言或
跳过检查来上传。
