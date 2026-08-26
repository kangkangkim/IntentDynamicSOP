#!/usr/bin/env python3
"""PreToolUse hook: verify a real AskUserQuestion interaction referencing
the plan file exists in the session transcript before allowing any
authorize_execution.py call. Fail-closed: any parse/IO error -> deny."""

import json
import os
import re
import shlex
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
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
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

    # Step 3: extract --request PATH without breaking quoted paths.
    try:
        command_args = shlex.split(command)
    except ValueError:
        command_args = []
    request_path = None
    for index, argument in enumerate(command_args):
        if argument == "--request" and index + 1 < len(command_args):
            request_path = command_args[index + 1]
            break
        if argument.startswith("--request="):
            request_path = argument.split("=", 1)[1]
            break
    if not request_path:
        _deny("BLOCKED_PLAN_CONFIRMATION_REQUIRED: --request path not found in authorize_execution.py command")

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

    matching_asks = {}
    ask_timestamp = None
    result_timestamp = None

    def content_blocks(entry):
        """Yield both legacy flat fixture blocks and real transcript blocks."""
        if entry.get("type") in ("tool_use", "tool_result"):
            yield entry
        message = entry.get("message")
        if not isinstance(message, dict):
            return
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    yield block

    for line in lines:
        try:
            entry = json.loads(line)
        except Exception:
            continue

        entry_timestamp = entry.get("timestamp")
        for block in content_blocks(entry):
            if (block.get("type") == "tool_use"
                    and block.get("name") == "AskUserQuestion"):
                input_str = json.dumps(block.get("input", ""))
                if plan_basename in input_str or confirmation_ref in input_str:
                    tool_use_id = block.get("tool_use_id") or block.get("id")
                    if tool_use_id:
                        matching_asks[tool_use_id] = block.get("timestamp") or entry_timestamp
            elif (block.get("type") == "tool_result"
                    and block.get("tool_use_id") in matching_asks):
                tool_use_id = block.get("tool_use_id")
                if block.get("is_error") is True:
                    matching_asks.pop(tool_use_id, None)
                    continue
                content = block.get("content", [])
                if isinstance(content, list):
                    has_err = any(
                        isinstance(c, dict) and c.get("is_error") is True
                        for c in content
                    )
                    if has_err:
                        matching_asks.pop(tool_use_id, None)
                        continue
                ask_timestamp = matching_asks[tool_use_id]
                result_timestamp = block.get("timestamp") or entry_timestamp
                break
        if result_timestamp is not None:
            break

    if result_timestamp is None:
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
        from datetime import datetime

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
