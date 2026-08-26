# Error Pattern Library

Accumulated known build/test failure patterns for fast-fix routing.
Auto-appended by the Error Pattern Library Hook in automated-closure-loop.md.
Human may edit or remove entries. Never include real paths, APIs, or internal symbols.

## Schema

Each pattern entry:
- `pattern_id`: unique id (run_id + error hash)
- `error_signature`: redacted fingerprint of the error (type, location category, message shape)
- `fast_fix_hint`: the fix approach that resolved it
- `first_seen_run`: run_id when first observed
- `occurrence_count`: how many times this pattern has been matched

## Known Patterns

<!-- Entries are appended here by the Error Pattern Library Hook -->
<!-- Format:
### <pattern_id>
- error_signature: <redacted fingerprint>
- fast_fix_hint: <fix approach>
- first_seen_run: <run_id>
- occurrence_count: <n>
-->
