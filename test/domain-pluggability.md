# Scenario: Domain 可插拔亲手验证（builtin 拔插 / DT 替换 / 误用拦截）

## 目标

不用 Claude、直接跑脚本，亲手验证 domain 可插拔是真实被工具强制的，而不是文档口号：

1. builtin domain（d3a / general）必须在 domain module registry 里 active 注册，否则 preflight 直接 INVALID（Gate 1，`resolve_team_config.rb`）。
2. `--domain` 显式指定时必须与 effective config 的 domain 一致，否则 context load plan 直接 INVALID（Gate 2，`plan_context.rb`）。
3. `domain.d3a.dt_domains` 是整体替换（不是合并）：换成 TDEMO_A/TDEMO_B 后内置 TPRINT/FW/DPF 彻底消失。
4. `mode: custom` 走 `domain.custom` 内联注册，不受 registry gate 影响。

## 前置

- 全部命令在仓库根目录执行（resolver 从 cwd 向上找 `.claude/skills/idc-workflow` 定位 harness root）。
- 本机需要 `ruby` 和 `python3`。
- ruby 启动时可能打印一串
  `Ignoring commonmarker-0.23.6 because its extensions are not built. Try: gem pristine ...`
  之类的 gem 警告：这是本机 gem 环境噪音，与结果无关，可忽略。注意 Gate 1 的报错本身走
  stderr，不要无脑 `2>/dev/null`。
- 实验全部在 `mktemp -d` 临时目录里做，靠 `--registry` 覆盖注入假 registry；
  不要直接改仓库里的 `registry.yaml` / `team-config.yaml`（想动真实文件用文末沙箱版）。

## 实验 1：拔掉 d3a 注册，mode 仍为 d3a → INVALID

```sh
cd "<仓库根目录>"
TMP=$(mktemp -d)

# 一份没有 d3a 的 registry（general 仍 active，template 原样保留）
cat > "$TMP/registry.yaml" <<'YAML'
domain_modules:
  - id: general
    module_file: domains/general/module.yaml
    status: active
  - id: template-domain
    module_file: domains/template-domain/module.yaml
    status: template
YAML

# 最小 team-config，mode 还是 d3a
cat > "$TMP/team-config.yaml" <<'YAML'
config_version: 1
team:
  id: gate-d3a-team
  repo_path: .
domain:
  mode: d3a
bindings: {}
YAML

ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config "$TMP/team-config.yaml" --registry "$TMP/registry.yaml" --check
echo "exit=$?"
```

期望（已实测）：

```text
INVALID team-config.yaml
- domain.mode d3a is not registered in the domain module registry; register it or switch domain.mode
exit=1
```

`--registry` 是专门给沙箱/测试用的可选覆盖；不传时 resolver 用仓库默认
`.claude/skills/idc-workflow/references/domains/registry.yaml`。这就是 Gate 1：
builtin mode 的注册状态是 load-bearing 的。

## 实验 2：同 registry + mode: general → READY；再拿 d3a 去跑 → 被拒

```sh
cat > "$TMP/team-config-general.yaml" <<'YAML'
config_version: 1
team:
  id: gate-general-team
  repo_path: .
domain:
  mode: general
bindings: {}
YAML

# 拔掉 d3a 不影响 general 团队
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config "$TMP/team-config-general.yaml" --registry "$TMP/registry.yaml" --check
echo "exit=$?"

# 生成 effective config，然后故意用 --domain d3a 去 plan
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config "$TMP/team-config-general.yaml" --registry "$TMP/registry.yaml" \
  --output "$TMP/effective.yaml" >/dev/null

ruby .claude/skills/idc-team-config/scripts/plan_context.rb \
  --effective "$TMP/effective.yaml" --phase decision --domain d3a
echo "exit=$?"
```

期望（已实测）：第一步 `READY: team-config.yaml is valid`、exit=0；
第三步 stdout 输出、exit=2：

```yaml
---
context_load_plan:
  status: INVALID
  reason: "--domain d3a does not match effective domain general; switch team-config
    domain.mode or use the effective domain"
```

这就是 Gate 2：团队已切到 general，就不允许再按 d3a 开 session。
对照实验：同一 effective 把 `--domain d3a` 换成 `--domain general` → `status: READY`、exit=0。
bootstrap 阶段（不传 `--domain`）不经过这道 gate。

## 实验 3：dt_domains 整体替换成 TDEMO_A / TDEMO_B

```sh
TMP=$(mktemp -d)
echo "demo dt knowledge (TDEMO_A)" > "$TMP/tdemo_a.md"
echo "demo dt knowledge (TDEMO_B)" > "$TMP/tdemo_b.md"

cat > "$TMP/team-config.yaml" <<YAML
config_version: 1
team:
  id: dt-demo-team
  repo_path: .
domain:
  mode: d3a
  d3a:
    dt_domains:
      - id: TDEMO_A
        knowledge_ref: $TMP/tdemo_a.md
      - id: TDEMO_B
        knowledge_ref: $TMP/tdemo_b.md
bindings: {}
YAML

# 这次用默认 registry（d3a 仍在），preflight 应 READY
ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config "$TMP/team-config.yaml" --check
echo "exit=$?"

ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config "$TMP/team-config.yaml" --output "$TMP/effective.yaml" >/dev/null

grep -e "id: TDEMO_A" -e "id: TDEMO_B" "$TMP/effective.yaml"
grep -c -e "id: TPRINT" -e "id: FW" -e "id: DPF" "$TMP/effective.yaml"
grep "test_domains_source:" "$TMP/effective.yaml"
```

期望（已实测）：

```text
READY: team-config.yaml is valid
exit=0
id: TDEMO_A / id: TDEMO_B 共命中 4 行（domain.test_domains 与 knowledge_catalog.d3a.test_domains 各两份）
0                                ← 内置 TPRINT/FW/DPF 计数为 0（grep 无命中时 exit=1）
  test_domains_source: team-config.yaml
```

两点说明：`dt_domains` 非空即整体替换内置清单，不合并；每个条目的 `knowledge_ref`
必须指向真实存在的文件（相对路径按 `team.repo_path` / harness root 解析，绝对路径直接用），
否则 resolver 报 `does not exist`。

## 实验 4：custom 不查 registry（内联注册豁免）

```sh
TMP=$(mktemp -d)
echo layer doc > "$TMP/custom_layer.md"
echo dt doc > "$TMP/custom_dt.md"

cat > "$TMP/registry.yaml" <<'YAML'
domain_modules:
  - id: general
    module_file: domains/general/module.yaml
    status: active
YAML

cat > "$TMP/team-config.yaml" <<YAML
config_version: 1
team:
  id: custom-demo-team
  repo_path: .
domain:
  mode: custom
  custom:
    id: my-domain
    trigger_rules:
      - keyword: demo
    lane_policy:
      mode: dynamic
    coding_layers:
      - id: LDEMO
        knowledge_ref: $TMP/custom_layer.md
    test_domains:
      - id: DTDEMO
        knowledge_ref: $TMP/custom_dt.md
    required_contracts: [task_contract, verification_contract]
    workflow_skill_ref: .claude/skills/idc-workflow/SKILL.md
    planner_skill_ref: .claude/skills/idc-intent-alignment/SKILL.md
    completion_skill_ref: .claude/skills/idc-team-config/SKILL.md
bindings: {}
YAML

ruby .claude/skills/idc-team-config/scripts/resolve_team_config.rb \
  --config "$TMP/team-config.yaml" --registry "$TMP/registry.yaml" --check
echo "exit=$?"
```

期望（已实测）：`READY: team-config.yaml is valid`、exit=0 —— 换成默认 registry 结果相同。
`custom` 的合法性来自 `domain.custom` 内联声明，Gate 1 不查 registry。

## 沙箱版：cp 到 /tmp 亲手编辑真实文件

不想用 `--registry` 注入，也可以直接改副本：

```sh
SB=/tmp/idc-plug-sandbox
rm -rf "$SB"
cp -R "$PWD" "$SB"        # 在仓库根目录执行
cd "$SB"

# 1) 删掉 .claude/skills/idc-workflow/references/domains/registry.yaml 里的 d3a 条目
#    （连续 3 行：- id: d3a / module_file / status: active），或：
#    sed -i '' '/- id: d3a$/,/^    status: active$/d' .claude/skills/idc-workflow/references/domains/registry.yaml

# 此时 team-config.yaml 仍是 mode: d3a，跑正式入口：
ruby .claude/skills/idc-team-config/scripts/prepare_runtime.rb
echo "exit=$?"
# 期望 status: NEEDS_TEAM_CONFIG、exit=1，reason 里能看到
#   INVALID team-config.yaml
#   - domain.mode d3a is not registered in the domain module registry; ...
# （reason 里混进来的 Ignoring <gem> 行同样是本机噪音）

# 2) 把 team-config.yaml 的 mode: d3a 改成 mode: general，再跑：
ruby .claude/skills/idc-team-config/scripts/prepare_runtime.rb | grep "status: READY"
# 期望命中 status: READY —— 拔掉 d3a + 切 mode 两步做完，runtime 才恢复

# 3) 在沙箱里跑全量 harness：
python3 tests/test_harness.py | grep 失败
```

期望（已实测）：第 3 步 `8 个测试失败。`，第一条是

```text
失败 test_domain_module_registry_files_exist: Domain Module registry 缺少 d3a module。
```

其余 7 条失败都是 harness 内部用 d3a 模式配置去跑 resolver、被同一道 Gate 1 拦下。
这是故意的：「默认 registry 必须含 active 的 d3a」这个约束被测试钉死——
你在沙箱里拔掉它，harness 立刻红给你看。验证完 `rm -rf /tmp/idc-plug-sandbox` 即可。

## 全量自检

回到真实仓库根目录：

```sh
python3 tests/test_harness.py
```

期望最后一行：`61 个测试通过。`（本卡只新增文档，不改任何被测行为。）

## 一句话结论

registry 是 load-bearing 的：拔掉一个内置 domain = 注册表删条目 + team-config 切 mode，两步缺一不可；`--domain` 与 effective domain 不一致会被 plan_context 当场拒绝；`dt_domains` / `test_domains` 是整体替换不是合并；custom domain 内联注册，不受 registry gate 影响。
