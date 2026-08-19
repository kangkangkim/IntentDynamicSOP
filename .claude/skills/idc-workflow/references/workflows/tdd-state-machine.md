# TDD State Machine

## Layer 状态

```text
SPEC_READY
TEST_PREPARING
RED_CONFIRMED
IMPLEMENTING
IMPL_REVIEW
GREEN_CONFIRMED
SCAN_RUNNING
SCAN_GREEN
ATOMIC_COMMIT_CREATED
LAYER_COMPLETE
```

允许的状态迁移：

```yaml
SPEC_READY: [TEST_PREPARING]
TEST_PREPARING: [RED_CONFIRMED]
RED_CONFIRMED: [IMPLEMENTING]
IMPLEMENTING: [IMPL_REVIEW, GREEN_CONFIRMED]
IMPL_REVIEW: [GREEN_CONFIRMED, DT_REVERIFY]
GREEN_CONFIRMED: [SCAN_RUNNING, ATOMIC_COMMIT_CREATED, LAYER_COMPLETE]
SCAN_RUNNING: [SCAN_GREEN, DEFECT_FIX]
SCAN_GREEN: [ATOMIC_COMMIT_CREATED, LAYER_COMPLETE]
ATOMIC_COMMIT_CREATED: [LAYER_COMPLETE]
```

禁止 shortcut：

```text
SPEC_READY -> IMPLEMENTING -> DONE
```

## Task 状态

```text
ALL_LAYERS_GREEN
TRAN_BUILD
BUILD_GREEN
KNOWLEDGE_ARCHIVE
TRANSFER_TO_TEST
DONE
TRAN_BUILD_FAIL
ERROR_ANALYSIS
TARGET_LAYER_FIX
DT_REVERIFY
DEFECT_FIX
```

完成条件：

- 每个 required DT domain 都有 GREEN evidence。
- `tran_build` 有 PASS evidence。
- Completion 必须基于 tool evidence，而不是模型自信。

## Team Config Driven Extensions

These workflow extensions are shared by all teams and read their enterprise
skill refs from `team-config.yaml`. They must not hard-code internal paths,
commands, or skill names:

```text
workflows/impl-review.md
workflows/scan-and-fix-loop.md
workflows/atomic-commit.md
workflows/knowledge-archive.md
workflows/transfer-to-test.md
```

Extension bindings:

```text
team-config.yaml.bindings.impl_review.skill_ref
team-config.yaml.bindings.coding_standard.skill_ref
team-config.yaml.bindings.static_scan.skill_ref
team-config.yaml.bindings.defect_fix.skill_ref
team-config.yaml.bindings.git_commit.skill_ref
team-config.yaml.bindings.knowledge_archive.skill_ref
team-config.yaml.bindings.system_test.skill_ref
```

If a required extension binding is null, return `NEEDS_TEAM_CONFIG` instead of
guessing a command or internal skill.
