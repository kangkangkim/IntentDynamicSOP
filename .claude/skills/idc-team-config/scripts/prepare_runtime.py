#!/usr/bin/env python3
"""Migrated from prepare_runtime.py; behavior is intended to be identical."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
HARNESS_ROOT = SCRIPTS_DIR.parents[3]


def to_array(value):
    """Ruby Array(): nil -> [], list -> itself, scalar -> wrap."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [[key, child] for key, child in value.items()]
    return [value]


def dig(node, *keys):
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def uniq(items):
    seen = set()
    output = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def safe_yaml_load(text):
    return yaml.safe_load(text)


def emit_preflight(payload, exit_code):
    print(
        yaml.dump({"runtime_preflight": payload}, allow_unicode=True, sort_keys=False)
    )
    sys.exit(exit_code)


def main():
    parser = argparse.ArgumentParser(
        prog="prepare_runtime.py",
        description="Usage: prepare_runtime.py [--config PATH] [--output PATH]",
    )
    parser.add_argument(
        "--config", dest="config", default=str(HARNESS_ROOT / "team-config.yaml")
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=str(HARNESS_ROOT / ".idc/effective-team-config.yaml"),
    )
    options = parser.parse_args()

    config_path = Path(os.path.abspath(options.config))
    output_path = Path(os.path.abspath(options.output))
    if not config_path.is_file():
        emit_preflight(
            {
                "status": "NEEDS_TEAM_CONFIG",
                "config_ref": str(config_path),
                "reason": "team-config.yaml is missing; copy team-config.yaml.template and fill it",
            },
            2,
        )

    resolver = SCRIPTS_DIR / "resolve_team_config.py"
    resolved = subprocess.run(
        [
            sys.executable,
            str(resolver),
            "--config",
            str(config_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(HARNESS_ROOT),
    )
    if resolved.returncode != 0:
        emit_preflight(
            {
                "status": "NEEDS_TEAM_CONFIG",
                "config_ref": str(config_path),
                "reason": [
                    line.strip()
                    for line in resolved.stderr.splitlines()
                    if line.strip()
                ],
            },
            resolved.returncode,
        )

    with open(output_path, "r", encoding="utf-8") as handle:
        effective = safe_yaml_load(handle.read()) or {}
    selector = SCRIPTS_DIR / "select_capabilities.py"
    context_planner = SCRIPTS_DIR / "plan_context.py"
    policy_checks = []
    policy_errors = []
    profiles = dig(effective, "lane", "profiles") or {}
    capabilities = {
        capability.get("id"): capability
        for capability in to_array(effective.get("available_capabilities"))
        if isinstance(capability, dict)
    }

    def check_selection(lane_id, check_id, stage, skill_ids, trigger_signals):
        demand = {
            "capability_demand": {
                "execution_unit_ref": "preflight-{}".format(check_id),
                "selected_stage": stage,
                "selected_domain": "general",
                "lane_applicability": "applicable",
                "selected_lane": lane_id,
                "execution_profile": "lane_driven",
                "required_capability_keys": [],
                "optional_capability_keys": [],
                "observed_signals": trigger_signals,
                "contract_refs": [],
            }
        }
        descriptor, temp_name = tempfile.mkstemp(prefix="idc-capability-demand", suffix=".yaml")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(yaml.dump(demand, allow_unicode=True))
            selection_proc = subprocess.run(
                [
                    sys.executable,
                    str(selector),
                    "--effective",
                    str(output_path),
                    "--demand",
                    temp_name,
                ],
                capture_output=True,
                text=True,
                cwd=str(HARNESS_ROOT),
            )
            if selection_proc.returncode != 0:
                policy_errors.append(
                    "{}: selector failed: {} {}".format(
                        check_id, selection_proc.stderr.strip(), selection_proc.stdout.strip()
                    )
                )
                return
            selection = safe_yaml_load(selection_proc.stdout) or {}
            selected_ids = [
                item.get("capability_id")
                for item in to_array(dig(selection, "capability_selection_result", "selected"))
            ]
            if selected_ids[: len(skill_ids)] != skill_ids:
                policy_errors.append(
                    "{}: expected ordered prefix {!r}, got {!r}".format(
                        check_id, skill_ids, selected_ids
                    )
                )
                return
            policy_checks.append(
                {
                    "id": check_id,
                    "lane": lane_id,
                    "stage": stage,
                    "selected_skill_ids": selected_ids,
                    "status": "PASS",
                }
            )
        finally:
            os.unlink(temp_name)

    for lane_id, profile in profiles.items():
        orchestration = (profile or {}).get("orchestration") or {}
        for step in to_array(orchestration.get("steps")):
            if not isinstance(step, dict):
                continue
            check_selection(
                lane_id,
                "{}-step-{}".format(lane_id, step.get("id")),
                step.get("stage"),
                to_array(step.get("skill_ids")),
                to_array(step.get("trigger_signals")),
            )
        for skill_id in to_array(dig(profile, "skills", "required")):
            capability = capabilities.get(skill_id)
            if capability is None:
                continue
            matching_step = next(
                (
                    step
                    for step in to_array(orchestration.get("steps"))
                    if isinstance(step, dict) and skill_id in to_array(step.get("skill_ids"))
                ),
                None,
            )
            stage = (
                matching_step.get("stage")
                if matching_step
                else next(iter(to_array(capability.get("allowed_stages"))), None)
            )
            signals = to_array(matching_step.get("trigger_signals")) if matching_step else []
            check_selection(lane_id, "{}-required-{}".format(lane_id, skill_id), stage, [skill_id], signals)

    alignment = effective.get("alignment") or {}
    alignment_bindings = alignment.get("bindings") or {}
    alignment_steps = to_array(dig(alignment, "orchestration", "steps"))
    alignment_checks = []
    alignment_floor_signals = [
        "raw_idea",
        "critical_gaps_remain",
        "structured_requirement_input",
        "tr3_input",
    ]
    covered_alignment_signals = [
        signal
        for step in alignment_steps
        if isinstance(step, dict)
        for signal in to_array(step.get("trigger_signals"))
    ]
    alignment_floor_missing = [
        signal
        for signal in uniq(alignment_floor_signals)
        if signal not in covered_alignment_signals
    ]
    alignment_gate_present = any(
        isinstance(step, dict) and step.get("stage") == "alignment_check"
        for step in alignment_steps
    )

    for step in alignment_steps:
        if not isinstance(step, dict):
            continue
        check_id = "alignment-step-{}".format(step.get("id"))
        check = {
            "id": check_id,
            "stage": step.get("stage"),
            "skill_ids": to_array(step.get("skill_ids")),
            "trigger_signals": to_array(step.get("trigger_signals")),
            "status": "PASS",
        }
        step_errors = []
        if (
            not str(step.get("id") or "")
            or not str(step.get("stage") or "")
            or not to_array(step.get("skill_ids"))
        ):
            step_errors.append("ordered alignment step is missing id/stage/skill_ids")
        for skill_id in to_array(step.get("skill_ids")):
            skill_ref = str(dig(alignment_bindings, skill_id, "skill_ref") or "")
            if not skill_ref:
                step_errors.append(
                    "skill_id {} has no alignment.bindings entry".format(skill_id)
                )
                continue
            candidate = Path(skill_ref)
            if not candidate.is_absolute():
                candidate = HARNESS_ROOT / candidate
            if not candidate.is_file():
                step_errors.append("bound skill_ref does not exist: {}".format(skill_ref))
        if step_errors:
            check["status"] = "FAIL"
            check["reason"] = step_errors
            policy_errors.extend(
                "{}: {}".format(check_id, message) for message in step_errors
            )
        alignment_checks.append(check)

    if not alignment_gate_present:
        policy_errors.append(
            "alignment.orchestration ordered steps must keep the alignment_check gate step"
        )
    if alignment_floor_missing:
        policy_errors.append(
            "alignment.orchestration trigger_signals must cover the framework signal "
            "floor: {}".format(", ".join(str(item) for item in alignment_floor_missing))
        )

    if policy_errors:
        emit_preflight(
            {
                "status": "NEEDS_TEAM_CONFIG",
                "config_ref": str(config_path),
                "effective_config_ref": str(output_path),
                "reason": policy_errors,
                "alignment_policy_check_count": len(alignment_checks),
                "alignment_policy_checks": alignment_checks,
            },
            3,
        )

    context_proc = subprocess.run(
        [
            sys.executable,
            str(context_planner),
            "--effective",
            str(output_path),
            "--phase",
            "bootstrap",
        ],
        capture_output=True,
        text=True,
        cwd=str(HARNESS_ROOT),
    )
    if context_proc.returncode != 0:
        emit_preflight(
            {
                "status": "NEEDS_TEAM_CONFIG",
                "config_ref": str(config_path),
                "effective_config_ref": str(output_path),
                "reason": "context load planning failed: {} {}".format(
                    context_proc.stderr.strip(), context_proc.stdout.strip()
                ),
            },
            4,
        )
    bootstrap_load_plan = safe_yaml_load(context_proc.stdout)["context_load_plan"]

    emit_preflight(
        {
            "status": "READY",
            "config_ref": str(config_path),
            "effective_config_ref": str(output_path),
            "source_sha256": effective.get("source_sha256"),
            "available_capability_count": len(to_array(effective.get("available_capabilities"))),
            "registration_audit_status": dig(effective, "registration_audit", "status"),
            "declared_registration_override_count": len(
                to_array(dig(effective, "registration_audit", "declared_overrides"))
            ),
            "bootstrap_load_plan": bootstrap_load_plan,
            "lane_policy_check_count": len(policy_checks),
            "lane_policy_checks": policy_checks,
            "alignment_policy_check_count": len(alignment_checks),
            "alignment_policy_checks": alignment_checks,
        },
        0,
    )


if __name__ == "__main__":
    main()
