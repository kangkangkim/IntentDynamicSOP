# 新增文件中文本地化技术计划

## 1. 计划身份

- Task ID：`new-files-zh-localization`
- Change type：documentation localization
- Selected Domain：`general`
- Lane：`lite`
- Status：`PENDING_TECHNICAL_PLAN_CONFIRMATION`
- 日期：`2026-09-05`

本文件仅定义待确认的变更范围和验证合同。Technical Plan Confirmation 完成前，
不得修改下列目标文件，也不得提前创建 HTML、修改 README 或增加测试。

## 2. 目标

把本次新增文件中的用户可读自然语言翻译为中文，同时保持所有机器协议、运行语义、
依赖关系和可执行接口不变。翻译不得演变为 schema、API、运行时诊断或行为重构。

同时新增一份清晰的中文 HTML 架构指南，解释 IDC v2 架构、配置方式，以及配置如何
经真实消费者、运行约束、失败状态和证据链被强制执行；README 只增加一个发现入口。

## 3. 固定范围

中文本地化范围固定为以下 9 个文件：

1. `.claude/skills/idc-team-config/references/team-config-v2.md`
2. `.claude/skills/idc-team-config/references/runtime-lifecycle.md`
3. `.claude/skills/idc-workflow/references/schemas/completion-predicate.schema.yaml`
4. `.claude/skills/idc-workflow/references/schemas/domain-pack.schema.yaml`
5. `.claude/skills/idc-workflow/references/schemas/execution-event.schema.yaml`
6. `.claude/skills/idc-workflow/references/schemas/host-control-record.schema.yaml`
7. `.claude/skills/idc-workflow/references/schemas/migration-preview.schema.yaml`
8. `.claude/skills/idc-workflow/references/schemas/workflow-graph.schema.yaml`
9. `.claude/skills/idc-workflow/references/domains/d3a/completion-predicate.yaml`

新增交付范围：

10. `docs/idc-config-enforcement-architecture.html`
11. `README.md`，仅增加一个指向上述 HTML 的发现入口链接。

为验证 HTML，允许在 `tests/test_harness.py` 增加一个独立、可传播失败的验收测试；
不得修改或削弱任何既有测试、fixture 或 gate。Execution Authorization 还可包含本
单元自己的 RED/GREEN evidence、knowledge receipt 和 execution receipt 路径。

允许翻译：

- Markdown 标题与说明正文。
- YAML 注释和 `rules` 下的自然语言说明。
- D3A completion predicate 中两条面向人的自然语言 `requirements`。

禁止修改：

- YAML 键名、层级、列表顺序和数据类型。
- schema/API 字段名。
- Domain、Lane、Skill、Capability、predicate 和 contract ID。
- 状态、枚举、错误码和 placeholder。
- 文件路径、引用、命令、CLI 参数、变量名和哈希字段。
- Markdown 代码块及行内代码中的协议 token。
- 除上述 `tests/test_harness.py` 最小验收增量外，任何 Python、测试、示例、其他
  Domain Pack、已批准计划或既有 `.idc` 运行证据。

HTML 必须满足：

- 所有用户可读标题、标签、正文、图例和表头使用中文；必要技术 token 保持原样。
- 单文件自包含，不加载外网脚本、样式、字体、图片或其他资源。
- 响应式、可打印、语义化并具备基本可访问性：正确语言、标题层级、landmark、
  表格表头、可见焦点和足够的文字对比度。
- 复用现有 `docs/*.html` 的视觉语言：系统字体、浅色页面、白色面板、细边框、克制
  状态色、紧凑卡片和清晰信息层级；不得复制其他页面的无关内容。
- 桌面首屏应能看清主链路；窄屏允许图和矩阵安全横向滚动或转为单列，不得把文字
  压缩到不可读。
- README 只承担发现入口，不复制 HTML 的架构说明或运行手册。

## 4. API Contract

API Contract 不变。本单元不增加、删除或重命名任何字段、参数、命令、状态、错误码、
枚举或返回结构。翻译后的 YAML 解析结果除允许翻译的 prose scalar 外，必须与翻译前
保持结构等价；Markdown 代码块必须逐字节保持不变。

HTML 是当前实现的静态说明视图，不是新的配置源、resolver、控制面、执行器或 API。
README 链接不改变 `team-config.yaml` 作为唯一团队配置源的所有权。

虽然 prose 或注释变化会改变文件字节和相关依赖哈希，但这不代表 API 变化。验证时
必须重新生成临时 effective runtime、selection、graph 和 authorization；不得复用旧
运行产物，也不得手工改写哈希以制造一致。

## 5. DT 设计

### DT-A：YAML 结构等价

- Given：保存 7 个目标 YAML 文件翻译前的解析结构。
- When：只替换获准的自然语言注释、`rules` 和 D3A requirements 文案。
- Then：所有键、层级、列表顺序、类型及非 prose scalar 完全不变，且文件仍可由
  `yaml.safe_load` 解析。

### DT-B：受保护 token 不变

- Given：从 9 个目标文件提取键名、ID、枚举、错误码、placeholder、路径、命令、
  CLI 参数、变量名、哈希字段、行内代码和代码块。
- When：比较翻译前后的 token manifest。
- Then：manifest 完全相同；任何缺失、新增或重排均阻断完成。

### DT-C：Markdown 代码块与链接不变

- Given：两个 reference 中的 fenced code blocks、行内协议 token 和本地链接。
- When：执行翻译并检查链接。
- Then：代码块字节相同，全部本地链接仍可解析，命令示例及参数不变。

### DT-D：Skill 可加载

- Given：`idc-team-config` 继续链接两个 translated references。
- When：运行 skill-creator `quick_validate.py`。
- Then：Skill validation PASS，入口 Skill 无需增加重复说明。

### DT-E：运行时语义回归

- Given：翻译会合法改变部分被引用文件的字节哈希。
- When：从源配置重新生成真实临时运行产物并执行 standalone 与 full harness。
- Then：resolver、migration、security、integrity、completion 和 full harness 全部 PASS；
  新产物使用新 dependency identity，旧 authorization 不被错误复用。

### DT-F：HTML DOM、关键文案与可访问性

- Given：生成 `docs/idc-config-enforcement-architecture.html`。
- When：使用标准库 HTML parser 检查 DOM，并提取可见文本。
- Then：文档声明 `lang="zh-CN"`，存在唯一 `main` 和一级标题；标题层级连续；架构、
  配置、执行闭环、追踪矩阵、D3A 和信任边界各有可定位 section；表格具有 `caption`、
  `thead` 和列标题；交互链接可通过键盘获得可见焦点；不存在重复 ID、空标题、占位
  文案或把大段英文当作用户说明。

### DT-G：端到端架构图与确定性闭环

- Given：HTML 的总览架构图和时序区。
- When：核对节点、连线和说明文字。
- Then：主链完整呈现 `team-config.yaml` → resolver/compiler → Domain Pack/Lane/
  ordered Skills → external host control/authorization → dispatch/ledger → completion
  verifier；另以确定性时序说明 prepare、plan/select、compile、host control、authorize、
  initialize/acquire、record success/predicate、export/replay、verify 的真实顺序。运行区
  给出当前真实 prepare、compile、authorize、ledger replay 和 completion verify 命令，
  并明确 dispatch state 是 Python host API，不虚构 dispatch CLI。

### DT-H：配置示例、切换与删除边界

- Given：HTML 内嵌 General、Custom 和 D3A 三段可复制的 team-config v2 YAML 示例。
- When：从代码块提取 YAML，以 `yaml.safe_load` 解析，并与当前 schema、官方 Pack 和
  examples 核对。
- Then：三段都可解析；只含公开 placeholder；清楚展示 `domains.enabled/default/
  definitions` 的切换方式、Pack 引用和覆盖边界；D3A 启用时保持固定七层、团队 DT 与
  `tran_build` 完成条件，禁用时从 `domains.enabled` 省略，物理删除 D3A Pack 不影响
  未启用它的 Core，而显式启用缺失 Pack 必须有界失败。权属说明必须明确只有
  `team-config.yaml` 是团队配置源；team definition 覆盖对应 Pack ref/trigger/registry，
  registry 显式值整体替换而非合并；team Lane 只覆盖对应 Pack Lane，未配置 Lane 保留
  Pack 默认；bindings 覆盖 capability Skill ref，adapter extensions 只新增原子能力，
  alignment 只配置前置对齐步骤。

### DT-I：ordered 三 Lane Skills 强制生效

- Given：HTML 的 `fast`、`lite`、`complex` ordered Lane 示例与闭环图。
- When：核对每个配置 Skill 从配置到完成的证据路径。
- Then：明确说明 Lane profile 中每个 configured Skill 都进入 canonical graph 独立
  node；host ticket 绑定 authorization/graph/node/前驱/idempotency；前驱未成功时后继
  不可 claim；ledger 保留顺序和哈希链；缺失、插入或重排 Skill 以及缺证据均不能由
  completion verifier 判为 `DONE`。不得暗示三个 Lane 共享一套写死 Skill 列表。

### DT-J：配置强制生效追踪矩阵

- Given：HTML 的追踪矩阵。
- When：逐行检查五列“配置字段 → 消费组件 → 运行约束 → 失败结果 → 证据”。
- Then：至少覆盖 `domains`、definition/Pack refs、Lane profiles、ordered steps、
  bindings、adapter extensions、alignment、knowledge refs、D3A registry override、
  completion predicates、source/dependency hashes；消费者与当前 resolver、policy
  materializer、selector、graph compiler、authorizer、dispatch state、ledger 和
  completion verifier 一致，失败结果使用真实状态或错误码，不发明新组件。

### DT-K：fail-closed、信任边界与非目标

- Given：HTML 的安全边界区。
- When：核对 host control、dispatch state、哈希和 executor 权限说明。
- Then：说明 host-control record 与 dispatch state 位于 executor 不可写的宿主保护
  路径；请求内嵌声明不能自证或扩权；SHA-256 只提供字节完整性而非签名；unknown、
  shadowed、drift、未注册 Skill、顺序违例和缺 predicate evidence 均 fail closed；明确
  非目标包括签名服务、exactly-once 承诺、企业私有实现和第二份团队配置。

### DT-L：链接、自包含和静态 HTML 校验

- Given：HTML 的全部 `href`/`src`、内联 CSS 和 README 新入口。
- When：解析相对链接、fragment、资源 URL 和样式规则。
- Then：README 恰有一个清晰入口指向 HTML；仓库内目标和 fragment 均存在；页面无
  `http://`、`https://`、协议相对 URL、外部字体或脚本；无内联事件处理器；具有
  viewport、打印媒体规则和窄屏断点；静态 parser 不报告未闭合结构。

### DT-M：桌面、移动端与打印视觉验收

- Given：通过本地文件打开 HTML。
- When：分别以约 1440px 桌面宽度、390px 移动宽度和打印预览检查页面。
- Then：桌面首屏主链可读；移动端无页面级意外横向溢出，图和矩阵使用标记清楚的
  局部滚动或单列降级；无重叠、裁切或不可读字号；打印移除阴影和非必要背景，核心
  卡片与表格标题避免跨页断裂。视觉验收截图只写仓库外临时目录。

### DT-N：私有细节与 full harness

- Given：最终 HTML、README 和测试增量。
- When：执行 placeholder hygiene、HTML 验收测试及完整 `tests/test_harness.py`。
- Then：不出现真实企业 API、路径、命令、日志、测试名、构建系统或架构事实；HTML
  测试是 full harness 的真实组成部分并传播失败；全部既有测试保持 GREEN。

## 6. 实施步骤

1. Technical Plan Confirmation 后，为本单元生成限定上述 9 个本地化文件、HTML、
   README 单链接、`tests/test_harness.py` 最小验收增量和证据路径的 Execution
   Authorization，并派发给真实 executor。
2. 在仓库外临时目录记录翻译前的 YAML 结构投影、受保护 token manifest、Markdown
   code-block manifest 和目标文件 SHA-256。
3. 先翻译两个 Markdown reference 的标题和说明正文，不改代码块、行内协议 token、
   链接目标或命令。
4. 翻译 6 个 schema 的注释和 `rules` 自然语言；翻译 D3A completion predicate 的
   两条自然语言 requirements。不得机械替换整个 YAML scalar 集合。
5. 运行 DT-A 至 DT-C 的前后比较；任一差异超出 allowlist 时立即停止并回滚该文件。
6. 从当前实现和现有公开 HTML 的视觉语言构建单文件架构指南。先完成语义化 DOM 与
   九类必备内容，再实现响应式、打印和可访问样式；不得从现有页面复制无关正文。
7. 在 README 增加一个短入口链接；在 `tests/test_harness.py` 增加独立 HTML contract
   test，覆盖 DT-F 至 DT-L 并保证失败传播。视觉 DT-M 由真实桌面/移动端/打印预览
   记录，不用脆弱像素快照替代语义测试。
8. 运行真实 standalone、Skill validation、链接/HTML 静态检查和 full harness，记录
   RED/GREEN evidence、视觉验收结果与 knowledge consumption receipt。

## 7. 验证命令

```sh
python3 -c 'import pathlib, yaml; [yaml.safe_load(p.read_text()) for p in pathlib.Path(".claude/skills/idc-workflow/references").rglob("*.yaml")]'

python3 tests/test_team_config_surface.py
python3 tests/test_team_config_migration.py
python3 tests/test_final_security_review.py
python3 tests/test_runtime_integrity.py
python3 tests/test_v2_core_isolation.py
python3 tests/test_harness.py

python3 <SKILL_CREATOR_ROOT>/scripts/quick_validate.py \
  .claude/skills/idc-team-config

git diff --check
```

此外必须运行本单元的结构投影、受保护 token、代码块和本地链接比较脚本。比较脚本及
manifest 只写入仓库外临时目录，不新增产品文件。HTML 的 DOM、自包含、关键文案、
YAML 示例和链接检查必须由 full harness 内的测试执行；桌面、移动端和打印预览使用
本地浏览器，不访问网络。

## 8. 风险

- YAML prose、requirements 或注释的字节变化会改变 runtime dependency identity；
  若继续使用旧 effective config、graph 或 authorization，会产生错误的漂移判断。
- 机械翻译可能误改 `READY`、`BLOCKED`、`UNSUPPORTED`、`PASS`、`DONE` 等协议值，
  或误改 ref、路径和 CLI 参数，导致 resolver 或安全 gate 失效。
- 翻译 requirements 时若改变列表数量或顺序，可能改变 completion contract 语义。
- 修改已批准计划或 `.idc` evidence 会破坏既有 Technical Plan Confirmation 与
  provenance，因此严格排除。
- Python 中的用户可见英文诊断不属于本单元；若需要运行时消息本地化，必须另建带
  兼容策略和测试的 API/localization 单元。
- 架构图若只展示“理想流程”而非真实消费者，会掩盖配置未消费问题；每条关键配置
  必须在追踪矩阵中落到实现组件、失败结果和证据。
- 三个 Lane 若被画成固定 Skill 清单，会错误限制团队配置；示例只能展示 shape，正文
  必须说明实际节点由各 Lane 的 configured ordered steps 编译产生。
- 纯桌面大画布容易在移动端和打印时失真；主链、矩阵和代码示例必须有独立响应式与
  打印策略。

## 9. 回滚边界

- 回滚仅限上述 9 个目标文件的翻译差异、删除本单元新增 HTML、移除 README 的单个
  入口链接以及撤销 `tests/test_harness.py` 的本单元测试增量；不重置或覆盖共享 dirty
  worktree 的其他改动。
- 翻译失败时恢复对应文件的本单元前字节，并废弃由翻译后字节生成的临时 runtime、
  selection、graph 和 authorization。
- 不回滚此前已通过的 Domain Pack、resolver、migration、host-control 或 dispatch
  实现；不得通过修改测试、错误码或 token allowlist 来制造 GREEN。
- 只有 DT-A 至 DT-N、全部指定验证和 `git diff --check` 均 PASS，才能提交给 Main
  agent 进行 completion verification。

## 10. 完成标准

- 9 个目标文件中的获准自然语言已翻译为中文。
- API Contract 与所有受保护 token 完全不变。
- YAML 全部可解析，Markdown 代码块与本地链接保持有效。
- 中文 HTML 完整覆盖架构、配置方式和配置强制生效链，且自包含、响应式、可打印、
  语义化、可访问，不含外网依赖或企业私有细节。
- General、Custom、D3A 示例可解析；三个 ordered Lane、D3A 删除边界、追踪矩阵与
  host-control/dispatch 信任边界均与当前实现一致。
- README 只有一个发现入口，HTML contract test 已进入 full harness 并传播失败。
- Skill validation、standalone suites 和 full harness 全部 PASS。
- 有真实 authorization ID、dispatch tool-call ref、executor session ref、RED/GREEN
  evidence 和 VERIFIED knowledge receipt。
