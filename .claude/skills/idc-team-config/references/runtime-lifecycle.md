# 运行时生命周期

执行或诊断已批准的 IDC run 时，请阅读本参考。

## 必需顺序

不可绕过的生命周期为：

```text
prepare
-> plan context / knowledge and select capabilities
-> compile canonical run graph
-> host creates an independent protected control record
-> authorize that exact graph against the control record
-> host initialize / acquire / record success and predicates
-> host export and deterministic ledger replay
-> completion verification against protected dispatch state
```

可执行顺序为：

1. 运行 `scripts/prepare_runtime.py`；只消费 READY effective runtime。
2. 为同一 execution-unit identity 运行 `scripts/plan_context.py`、
   `scripts/plan_knowledge.py` 和 `scripts/select_capabilities.py`。
3. 运行 `scripts/compile_run_graph.py`；配置的 ordered Skill 按精确顺序成为 graph
   node，包括重复 occurrence。
4. host 而不是 executor 在 host 选择、且不在 executor 可写 `allowed_paths` 内的路径创建
   control record。它绑定 task 和 execution-unit ID、Domain/Lane、graph hash、effective
   source 与 runtime-dependency hash、capability-selection bytes、knowledge plan、plan
   confirmation、alignment 与 delegation bytes、executor identity、allowed path 和 expected output。
5. 只针对该独立提供的 record 授权 request：
   ```sh
   python3 .claude/skills/idc-workflow/scripts/authorize_execution.py \
     --request <REQUEST> \
     --host-control-record <HOST_PROTECTED_CONTROL_RECORD> \
     --output <AUTHORIZATION_RESULT>
   ```
6. host 调用 `scripts/dispatch_state.py` 中的 Python API：`initialize_state`、
   `acquire_dispatch`、`record_success`、`record_predicate`，再调用 `export_snapshot`。
   此模块不是 CLI。
7. replay 使用带独立 host record 的 `scripts/run_event_ledger.py`。
8. 运行 `scripts/verify_completion.py --request <REQUEST> --dispatch-state
   <HOST_PROTECTED_STATE>`。只有返回 DONE 才可报告 DONE。

以上所有 `scripts/` path 都相对于 `idc-team-config` skill。

## 信任与恢复边界

- dispatch state path 和 host-record input 必须受保护，不能由 executor 写入。request
  内嵌副本、ticket 或 hash 不能自证。
- host control record 同样是受保护 input。其绑定 byte hash 可检测 content drift，但不是
  signature；把同样的 claim 嵌入 request 不能证明 host control，也不能授权更宽的 path set。
- SHA-256 值检测 identity 和 byte drift；它们不是 signature，也不证明由谁控制文件。
- source、Pack、policy、workflow、registry、completion、knowledge、contract 或 Skill 的
  byte drift 会使 stale effective state、selection、graph 或 authorization 失效。
- dispatch claim 绑定 authorization、graph、node、predecessor state、host dispatch ref、
  executor session 和 idempotency key。
- replay 相同的 idempotent claim 返回同一 ticket。crash 后，不支持相同 idempotency key 的
  downstream operation 返回 `RECOVERY_REQUIRED`；不得再次自动执行。
- predecessor success 前不能 claim successor。缺失或重排的 configured Skill 以及缺失的
  predicate evidence 都 fail closed。

每个 attempt 的 run state 和 evidence 都属于新的
`.idc/runs/<task-id>/attempt-<n>/` directory。只有 effective team config 是全局再生状态文件。
