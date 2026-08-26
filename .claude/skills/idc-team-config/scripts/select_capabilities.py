#!/usr/bin/env python3

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml


def safe_yaml_load(source):
    return yaml.safe_load(source)


def load_yaml(path):
    try:
        return safe_yaml_load(Path(path).resolve().read_text()) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


parser = argparse.ArgumentParser(
    description="Usage: select_capabilities.py --effective PATH --demand PATH [--output PATH]"
)
parser.add_argument("--effective", metavar="PATH")
parser.add_argument("--demand", metavar="PATH")
parser.add_argument("--output", metavar="PATH")
args = parser.parse_args()

if not args.effective or not args.demand:
    print("ERROR: --effective and --demand are required", file=sys.stderr)
    sys.exit(1)

effective = load_yaml(args.effective)
demand_doc = load_yaml(args.demand)
demand = demand_doc.get("capability_demand") or demand_doc

stage = demand.get("selected_stage")
lane_applicability = demand.get("lane_applicability")
lane = demand.get("selected_lane")
profile = demand.get("execution_profile")
required_keys = list(demand.get("required_capability_keys") or [])
optional_keys = list(demand.get("optional_capability_keys") or [])
signals = list(demand.get("observed_signals") or [])
available = list(effective.get("available_capabilities") or [])

profiles = (effective.get("capability_selection") or {}).get("lane_profiles") or {}
if lane_applicability == "applicable":
    budget = (profiles.get(lane) or {}).get("max_optional_skills")
else:
    budget = ((effective.get("capability_selection") or {}).get("d3a_profile") or {}).get("max_optional_skills")

lane_profile = {}
if lane_applicability == "applicable":
    lane_profile = ((effective.get("lane") or {}).get("profiles") or {}).get(lane) or {}
skill_policy = lane_profile.get("skills") or {}
allowed_skill_ids = list(skill_policy.get("allow") or [])
denied_skill_ids = list(skill_policy.get("deny") or [])
configured_required_ids = list(skill_policy.get("required") or [])

domain_modules = (effective.get("domains") or {}).get("modules") or {}
selected_domain_id = str(demand.get("selected_domain") or "")
domain_module = domain_modules.get(selected_domain_id)
if domain_module is None:
    custom_mod = domain_modules.get("custom")
    if isinstance(custom_mod, dict) and str(custom_mod.get("id") or "") == selected_domain_id:
        domain_module = custom_mod
if domain_module is None:
    if str((effective.get("domain") or {}).get("id") or "") == selected_domain_id:
        domain_module = effective.get("domain")

domain_orchestration = (domain_module or {}).get("orchestration") or {} if isinstance(domain_module, dict) else {}
domain_ordered = domain_orchestration.get("mode") == "ordered"
if domain_ordered:
    orchestration = domain_orchestration
else:
    orchestration = lane_profile.get("orchestration") or {}

if domain_ordered:
    orchestration_mode = "ordered"
elif lane_applicability == "applicable":
    orchestration_mode = orchestration.get("mode") or "autonomous"
else:
    orchestration_mode = "execution_profile"

orchestration_steps = list(orchestration.get("steps") or [])
stage_order = list(dict.fromkeys(
    step.get("stage") for step in orchestration_steps
    if isinstance(step, dict) and step.get("stage")
))
configured_execution_plan = [
    {
        "step_id": step.get("id"),
        "stage": step.get("stage"),
        "step_order": step_index + 1,
        "skill_ids": list(step.get("skill_ids") or []),
        "trigger_signals": list(step.get("trigger_signals") or []),
    }
    for step_index, step in enumerate(orchestration_steps)
    if isinstance(step, dict)
]
config_identity = {
    "source_ref": effective.get("source_ref"),
    "source_sha256": effective.get("source_sha256"),
}
config_identity["orchestration_sha256"] = hashlib.sha256(
    json.dumps(
        {
            "selected_domain": demand.get("selected_domain"),
            "selected_lane": lane,
            "mode": orchestration_mode,
            "steps": configured_execution_plan,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()
capability_signals = [s for cap in available for s in (cap.get("trigger_signals") or [])]
step_signals = []
if orchestration_mode == "ordered" or lane_applicability == "applicable":
    for step in orchestration_steps:
        step_signals.extend(step.get("trigger_signals") or [])
known_signals = list(dict.fromkeys(capability_signals + step_signals))
unknown_signals = [s for s in signals if s not in known_signals]

if unknown_signals:
    result = {
        "capability_selection_result": {
            "execution_unit_ref": demand.get("execution_unit_ref"),
            "selected_domain": demand.get("selected_domain"),
            "selected_stage": stage,
            "strategy": "autonomous_minimal_sufficient",
            "orchestration": {
                "mode": orchestration_mode,
                "stage_order": stage_order,
                "execution_plan": configured_execution_plan,
                "matched_step_ids": [],
                "configured_skill_ids": [],
            },
            "config_identity": config_identity,
            "ordered_execution": [],
            "selected": [],
            "skipped": [],
            "unresolved_required_capabilities": list(required_keys),
            "unresolved_configured_skill_ids": [],
            "status": "NEEDS_SIGNAL_MAPPING",
            "unknown_signals": unknown_signals,
            "known_signals_count": len(known_signals),
        }
    }
    output = yaml.dump(result, allow_unicode=True)
    if args.output:
        Path(args.output).resolve().write_text(output)
    else:
        print(output, end="")
    print(
        f"NEEDS_SIGNAL_MAPPING: unknown observed_signals: {', '.join(unknown_signals)}; "
        "not declared by any capability.trigger_signals or lane step.trigger_signals",
        file=sys.stderr,
    )
    sys.exit(1)

matching_steps = []
for step in orchestration_steps:
    if not isinstance(step, dict) or step.get("stage") != stage:
        continue
    required_sigs = list(step.get("trigger_signals") or [])
    if all(s in signals for s in required_sigs):
        matching_steps.append(step)

step_skill_ids = list(
    dict.fromkeys(sid for step in matching_steps for sid in (step.get("skill_ids") or []))
)
skill_step = {}
for step_index, step in enumerate(matching_steps):
    for skill_index, skill_id in enumerate(step.get("skill_ids") or []):
        skill_step.setdefault(skill_id, {
            "stage": step.get("stage"),
            "step_id": step.get("id"),
            "step_order": next(
                (idx + 1 for idx, configured in enumerate(orchestration_steps) if configured is step),
                step_index + 1,
            ),
            "skill_order": skill_index + 1,
        })
orchestration_missing = orchestration_mode == "ordered" and not matching_steps

available_by_id = {cap["id"]: cap for cap in available if isinstance(cap, dict)}
configured_required_for_stage = [
    sid for sid in configured_required_ids
    if sid in available_by_id and stage in (available_by_id[sid].get("allowed_stages") or [])
]
forced_skill_ids = list(dict.fromkeys(step_skill_ids + configured_required_for_stage))

selected = []
skipped = []
eligible = []

for capability in available:
    cid = capability.get("id")
    if stage not in (capability.get("allowed_stages") or []):
        skipped.append({"capability_id": cid, "reason": "stage_mismatch"})
        continue

    if lane_applicability == "applicable":
        if lane not in (capability.get("eligible_lanes") or []):
            skipped.append({"capability_id": cid, "reason": "lane_ineligible"})
            continue
        if cid in denied_skill_ids:
            skipped.append({"capability_id": cid, "reason": "team_lane_denied"})
            continue
        if allowed_skill_ids and cid not in allowed_skill_ids:
            skipped.append({"capability_id": cid, "reason": "team_lane_not_allowed"})
            continue

    if orchestration_mode == "ordered" and cid not in step_skill_ids:
        skipped.append({"capability_id": cid, "reason": "orchestration_step_excluded"})
        continue
    elif lane_applicability != "applicable":
        declared_profiles = list(capability.get("execution_profiles") or [])
        if declared_profiles and profile not in declared_profiles:
            skipped.append({"capability_id": cid, "reason": "profile_ineligible"})
            continue

    keys = list(capability.get("capability_keys") or [])
    required_coverage = [k for k in keys if k in required_keys]
    optional_coverage = [k for k in keys if k in optional_keys]
    signal_coverage = [s for s in (capability.get("trigger_signals") or []) if s in signals]
    forced_by_config = cid in forced_skill_ids

    if not forced_by_config and not required_coverage and not optional_coverage and not signal_coverage:
        skipped.append({"capability_id": cid, "reason": "signal_missing"})
        continue

    eligible.append({
        **capability,
        "required_coverage": required_coverage,
        "optional_coverage": optional_coverage,
        "signal_coverage": signal_coverage,
        "forced_by_config": forced_by_config,
    })

superseded_ids = list(
    dict.fromkeys(tid for cap in eligible for tid in (cap.get("supersedes") or []))
)
if superseded_ids:
    new_eligible = []
    for cap in eligible:
        if cap["id"] in superseded_ids:
            skipped.append({"capability_id": cap["id"], "reason": "superseded"})
        else:
            new_eligible.append(cap)
    eligible = new_eligible

unresolved_configured = []
selected_ids = set()
for skill_id in forced_skill_ids:
    candidate = next((item for item in eligible if item["id"] == skill_id), None)
    if candidate:
        source = "orchestration step" if skill_id in step_skill_ids else "Lane required skills"
        selected.append({**candidate, "requirement": "configured", "selection_reason": f"selected by {source}"})
        selected_ids.add(skill_id)
    else:
        unresolved_configured.append(skill_id)

covered_by_config = list(
    dict.fromkeys(k for item in selected for k in item.get("required_coverage", []))
)
uncovered = [k for k in required_keys if k not in covered_by_config]

while uncovered:
    remaining_eligible = [item for item in eligible if item["id"] not in selected_ids]
    candidate = max(
        (item for item in remaining_eligible if any(k in uncovered for k in item.get("required_coverage", []))),
        key=lambda item: len([k for k in item.get("required_coverage", []) if k in uncovered]),
        default=None,
    )
    if not candidate:
        break
    covered = [k for k in candidate.get("required_coverage", []) if k in uncovered]
    if not covered:
        break
    selected.append({**candidate, "requirement": "required", "selection_reason": f"covers required capability keys: {', '.join(covered)}"})
    selected_ids.add(candidate["id"])
    uncovered = [k for k in uncovered if k not in covered]

optional_candidates = sorted(
    [item for item in eligible if item["id"] not in selected_ids],
    key=lambda item: -(len(item.get("optional_coverage", [])) * 2 + len(item.get("signal_coverage", []))),
)
optional_count = sum(1 for item in selected if item.get("requirement") == "optional")
for candidate in optional_candidates:
    if budget is not None and optional_count >= budget:
        skipped.append({"capability_id": candidate["id"], "reason": "optional_budget_exhausted"})
        continue
    reason_parts = []
    if candidate.get("optional_coverage"):
        reason_parts.append(f"optional keys: {', '.join(candidate['optional_coverage'])}")
    if candidate.get("signal_coverage"):
        reason_parts.append(f"signals: {', '.join(candidate['signal_coverage'])}")
    selected.append({**candidate, "requirement": "optional", "selection_reason": "; ".join(reason_parts)})
    selected_ids.add(candidate["id"])
    optional_count += 1

if orchestration_missing or unresolved_configured:
    final_status = "NEEDS_ORCHESTRATION_MAPPING" if orchestration_missing else "NEEDS_TEAM_CONFIG"
elif not uncovered:
    final_status = "READY"
else:
    final_status = "NEEDS_ADAPTER_MAPPING"

selected_output = [
    {
        "capability_id": item["id"],
        "skill_ref": item.get("skill_ref"),
        "stage": (skill_step.get(item["id"]) or {}).get("stage", stage),
        "step_id": (skill_step.get(item["id"]) or {}).get("step_id"),
        "step_order": (skill_step.get(item["id"]) or {}).get("step_order"),
        "skill_order": (skill_step.get(item["id"]) or {}).get("skill_order"),
        "requirement": item["requirement"],
        "execution_order": idx + 1,
        "reason": item["selection_reason"],
    }
    for idx, item in enumerate(selected)
]
ordered_execution = [
    {
        "step_id": item.get("step_id"),
        "stage": item.get("stage"),
        "capability_id": item.get("capability_id"),
        "skill_ref": item.get("skill_ref"),
        "execution_order": item.get("execution_order"),
    }
    for item in selected_output
] if orchestration_mode == "ordered" else []

result = {
    "capability_selection_result": {
        "execution_unit_ref": demand.get("execution_unit_ref"),
        "selected_domain": demand.get("selected_domain"),
        "selected_stage": stage,
        "strategy": "autonomous_minimal_sufficient",
        "orchestration": {
            "mode": orchestration_mode,
            "stage_order": stage_order,
            "execution_plan": configured_execution_plan,
            "matched_step_ids": [step.get("id") for step in matching_steps],
            "configured_skill_ids": forced_skill_ids,
        },
        "config_identity": config_identity,
        "selected": selected_output,
        "skipped": list({(s["capability_id"], s["reason"]): s for s in skipped}.values()),
        "ordered_execution": ordered_execution,
        "unresolved_required_capabilities": uncovered,
        "unresolved_configured_skill_ids": unresolved_configured,
        "status": final_status,
    }
}

output = yaml.dump(result, allow_unicode=True)
if args.output:
    Path(args.output).resolve().write_text(output)
else:
    print(output, end="")

if orchestration_missing or unresolved_configured:
    sys.exit(3)
elif not uncovered:
    sys.exit(0)
else:
    sys.exit(2)
