#!/usr/bin/env python3
"""PreToolUse hook: verify a real AskUserQuestion interaction referencing
the plan file exists in the session transcript before allowing any
authorize_execution.py call. Fail-closed: any parse/IO error -> deny."""

import json
import os
import re
import sys

# PyYAML is optional. If unavailable, fall back to a simple regex extraction
# for the fields we need (status and confirmation_ref). This fallback only
# handles the flat / lightly-indented YAML shapes produced by IDC plan files;
# it is not a general YAML parser.
try:
    import yaml as _yaml
    def _yaml_load(text):
        return _yaml.safe_load(text)
except ImportError:
    _yaml = None
    def _yaml_load(text):
        # Fallback: regex-extract status and confirmation_ref from raw text
        return {"_raw": text}


def _deny(reason):
    print(json.dumps({"decision": "deny", "reason": reason}))
    sys.exit(0)


def _get_confirmation_block(doc):
    """Navigate to technical_plan_confirmation block, return it or None."""
    if not isinstance(doc, dict):
        return None
    # Try nested path first
    ear = doc.get("execution_authorization_request", {})
    if isinstance(ear, dict) and "technical_plan_confirmation" in ear:
        return ear["technical_plan_confirmation"]
    # Try top-level
    if "technical_plan_confirmation" in doc:
        return doc["technical_plan_confirmation"]
    return None


def _extract_from_raw(text, key):
    """Regex fallback: extract first value for a YAML key from raw text."""
    m = re.search(rf"^\s*{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip().strip('"\'')
    return None


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: hook failed to parse stdin JSON")

    # Step 1: only intercept Bash tool calls
    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "")

    # Step 2: only intercept authorize_execution.py calls
    if "authorize_execution.py" not in command:
        sys.exit(0)

    # Step 3: extract --request PATH
    m = re.search(r"--request\s+(\S+)", command)
    if not m:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: --request path not found in authorize_execution.py command")

    request_path = m.group(1)

    # Step 4: read and parse request YAML; check status
    try:
        with open(request_path, "r") as f:
            request_text = f.read()
        doc = _yaml_load(request_text)
    except Exception:
        _deny(f"BLOCKED_PLAN_CONFIRMATION_REQUIRED: cannot read request file {request_path}")

    if _yaml is None or isinstance(doc, dict) and "_raw" in doc:
        # Fallback path
        status = _extract_from_raw(request_text, "status")
        confirmation_ref = _extract_from_raw(request_text, "confirmation_ref")
    else:
        block = _get_confirmation_block(doc)
        if block is None:
            # No technical_plan_confirmation block at all -> passthrough;
            # authorize_execution.py will reject it.
            sys.exit(0)
        status = block.get("status")
        confirmation_ref = block.get("confirmation_ref")

    if status != "confirmed":
        sys.exit(0)

    # Step 5: check confirmation_ref present
    if not confirmation_ref:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: confirmation_ref missing")

    # Step 6: get basename of plan file
    plan_basename = os.path.basename(confirmation_ref)

    # Step 7: find transcript
    transcript_path = data.get("transcript_path") or os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    if not transcript_path:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: no transcript available to verify AskUserQuestion interaction for plan confirmation")

    # Step 8: scan transcript JSONL for AskUserQuestion + tool_result pair
    try:
        with open(transcript_path, "r") as f:
            lines = [l for l in f if l.strip()]
    except Exception:
        _deny(f"BLOCKED_PLAN_CONFIRMATION_REQUIRED: cannot read transcript at {transcript_path}")

    ask_tool_use_id = None
    ask_timestamp = None
    result_timestamp = None

    for line in lines:
        try:
            entry = json.loads(line)
        except Exception:
            continue

        if ask_tool_use_id is None:
            # Looking for the AskUserQuestion tool_use
            if (entry.get("type") == "tool_use"
                    and entry.get("name") == "AskUserQuestion"):
                input_str = json.dumps(entry.get("input", ""))
                if plan_basename in input_str or confirmation_ref in input_str:
                    ask_tool_use_id = entry.get("tool_use_id") or entry.get("id")
                    ask_timestamp = entry.get("timestamp")
        else:
            # Looking for the matching tool_result
            if (entry.get("type") == "tool_result"
                    and entry.get("tool_use_id") == ask_tool_use_id):
                if entry.get("is_error") is True:
                    # Error result — reset and keep scanning
                    ask_tool_use_id = None
                    ask_timestamp = None
                    continue
                # Check content list for error
                content = entry.get("content", [])
                if isinstance(content, list):
                    has_err = any(
                        isinstance(c, dict) and c.get("is_error") is True
                        for c in content
                    )
                    if has_err:
                        ask_tool_use_id = None
                        ask_timestamp = None
                        continue
                result_timestamp = entry.get("timestamp")
                break

    if ask_tool_use_id is None or result_timestamp is None:
        _deny(
            f"BLOCKED_PLAN_CONFIRMATION_REQUIRED: no AskUserQuestion interaction found in transcript that references plan file '{plan_basename}'"
        )

    # Step 9: timestamp check
    try:
        plan_mtime = os.path.getmtime(confirmation_ref)
    except Exception:
        plan_mtime = None

    if ask_timestamp is None or result_timestamp is None:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: timestamp missing in transcript, cannot verify ask occurred after plan was written")

    try:
        from datetime import datetime, timezone

        def _parse_ts(ts):
            if isinstance(ts, (int, float)):
                return float(ts)
            ts = str(ts).replace("Z", "+00:00")
            return datetime.fromisoformat(ts).timestamp()

        result_ts_val = _parse_ts(result_timestamp)
    except Exception:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: timestamp missing in transcript, cannot verify ask occurred after plan was written")

    if plan_mtime is not None and result_ts_val < plan_mtime:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: AskUserQuestion interaction predates plan file — possible attempt to fake confirmation")

    # Step 10: all checks pass
    sys.exit(0)


if __name__ == "__main__":
    main()
