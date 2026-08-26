---
name: gc-cleancode-scan
capability_key: static_scan
stage: verification
---

# GC Cleancode Scan

Enterprise atomic capability: static analysis and clean code gate.

Produces:
- `<ENTERPRISE_SCAN_REPORT_REF>` — static scan findings (blocker / warning / info)

Input: changed_paths
Output: gc_atomic_result; status BLOCKED when blocker findings present

<!-- placeholder: real SOP content lives in the enterprise repository -->
