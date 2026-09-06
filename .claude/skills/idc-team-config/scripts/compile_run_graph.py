#!/usr/bin/env python3

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml
sys.path.insert(0, str(Path(__file__).resolve().parent))
from domain_policy_runtime import LANES, ordered_rows, policy_view


def load_yaml(path):
    try:
        return yaml.safe_load(Path(path).resolve().read_text(encoding="utf-8")) or {}
    except (FileNotFoundError, OSError, yaml.YAMLError) as error:
        raise ValueError(str(error)) from error


def canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def collect_known_signals(effective):
    known = set()
    for capability in effective.get("available_capabilities") or []:
        if isinstance(capability, dict):
            known.update(capability.get("trigger_signals") or [])

    for profile in (effective.get("lane") or {}).get("profiles", {}).values():
        orchestration = profile.get("orchestration") if isinstance(profile, dict) else {}
        for step in (orchestration or {}).get("steps") or []:
            if isinstance(step, dict):
                known.update(step.get("trigger_signals") or [])

    domains = (effective.get("domains") or {}).get("modules") or {}
    for domain in domains.values():
        orchestration = domain.get("orchestration") if isinstance(domain, dict) else {}
        for step in (orchestration or {}).get("steps") or []:
            if isinstance(step, dict):
                known.update(step.get("trigger_signals") or [])
    return known


def invalid_graph(request, errors):
    return {
        "status": "INVALID",
        "graph_id": None,
        "config_sha256": None,
        "graph_sha256": None,
        "selected_domain": request.get("selected_domain"),
        "selected_lane": request.get("selected_lane"),
        "nodes": [],
        "edges": [],
        "errors": errors,
    }


def write_result(path, graph):
    output = yaml.safe_dump({"run_graph": graph}, allow_unicode=True, sort_keys=False)
    Path(path).resolve().write_text(output, encoding="utf-8")


def compile_graph(effective, selection, request):
    errors = []
    if selection.get("status") != "READY":
        errors.append({"code": "SELECTION_NOT_READY", "message": "selection must be READY"})

    selected_domain = request.get("selected_domain")
    selected_lane = request.get("selected_lane")
    if selected_lane is not None and selected_lane not in LANES:
        errors.append({"code": "LANE_MISMATCH", "message": "unsupported Lane"})
    try:
        effective = policy_view(effective, selected_domain, selected_lane)
    except (ValueError, OSError, TypeError, KeyError) as error:
        errors.append({"code": "CONFIG_DRIFT", "message": str(error)})
    if selection.get("selected_domain") != selected_domain:
        errors.append({"code": "DOMAIN_MISMATCH", "message": "selected domain changed"})

    effective_sha256 = effective.get("source_sha256")
    selection_sha256 = (selection.get("config_identity") or {}).get("source_sha256")
    if not effective_sha256 or effective_sha256 != selection_sha256:
        errors.append(
            {
                "code": "CONFIG_DRIFT",
                "message": "effective config and capability selection identities differ",
            }
        )
    dependency_sha = effective.get("runtime_dependency_sha256")
    if dependency_sha and dependency_sha != (selection.get("config_identity") or {}).get("runtime_dependency_sha256"):
        errors.append({"code": "CONFIG_DRIFT", "message": "selection dependency identity differs"})

    observed_signals = request.get("observed_signals") or []
    if not isinstance(observed_signals, list):
        errors.append({"code": "INVALID_SIGNALS", "message": "observed_signals must be a list"})
        observed_signals = []
    unknown_signals = sorted(
        str(signal)
        for signal in observed_signals
        if signal not in collect_known_signals(effective)
    )
    if unknown_signals:
        errors.append(
            {
                "code": "UNKNOWN_SIGNAL",
                "message": "unknown observed signal(s): {}".format(", ".join(unknown_signals)),
            }
        )

    ordered = selection.get("ordered_execution") or []
    if (selection.get("orchestration") or {}).get("mode") != "ordered" or not ordered:
        errors.append(
            {
                "code": "ORDERED_SELECTION_REQUIRED",
                "message": "ordered_execution is required for an ordered Run Graph",
            }
        )

    expected_orders = list(range(1, len(ordered) + 1))
    actual_orders = [
        item.get("execution_order") if isinstance(item, dict) else None for item in ordered
    ]
    if actual_orders != expected_orders:
        errors.append(
            {
                "code": "INVALID_EXECUTION_ORDER",
                "message": "ordered_execution must use contiguous one-based order",
            }
        )

    # Reconstruct all configured stages, then authenticate the supplied stage slice.
    try:
        module = (effective.get("domains") or {}).get("modules", {}).get(selected_domain)
        if not isinstance(module, dict):
            raise ValueError("DOMAIN_MISMATCH: configured module is required")
        mode = (module.get("lane_policy") or {}).get("mode") or module.get("lane_applicability")
        if ((mode == "not_applicable" and selected_lane is not None)
                or (mode in {"applicable", "dynamic", "fixed"} and selected_lane not in LANES)
                or (mode == "fixed" and selected_lane != module["lane_policy"].get("selected_lane"))):
            raise ValueError("LANE_MISMATCH: Lane violates module policy")
        profile = (effective.get("lane") or {}).get("profiles", {}).get(selected_lane, {})
        complete_order = ordered_rows(profile, module, effective.get("available_capabilities") or [],
                                      selected_lane, observed_signals)
        stage = selection.get("selected_stage")
        expected_slice = [dict(row, execution_order=index + 1) for index, row in enumerate(
            row for row in complete_order if stage is None or row["stage"] == stage)]
        keys = ("step_id", "stage", "capability_id", "skill_ref", "execution_order")
        supplied = [{key: row.get(key) for key in keys} for row in ordered]
        if supplied != expected_slice or not expected_slice:
            raise ValueError("SELECTION_MISMATCH: ordered selection is not the configured stage slice")
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        errors.append({"code": "SELECTION_MISMATCH", "message": str(error)})

    if errors:
        return invalid_graph(request, errors)

    capabilities = {
        item.get("id"): item
        for item in effective.get("available_capabilities") or []
        if isinstance(item, dict)
    }
    nodes = []
    for item in complete_order:
        skill_id = item.get("capability_id")
        capability = capabilities.get(skill_id) or {}
        nodes.append(
            {
                "node_id": "{:04d}-{}".format(item.get("execution_order"), skill_id),
                "execution_order": item.get("execution_order"),
                "stage": item.get("stage"),
                "step_id": item.get("step_id"),
                "skill_id": skill_id,
                "skill_ref": item.get("skill_ref"),
                "required": True,
                "trigger_signals": capability.get("trigger_signals") or [],
            }
        )
    edges = [
        {"from": nodes[index]["node_id"], "to": nodes[index + 1]["node_id"]}
        for index in range(len(nodes) - 1)
    ]
    canonical_graph = {
        "status": "READY",
        "config_sha256": effective_sha256,
        "selected_domain": selected_domain,
        "selected_lane": selected_lane,
        "nodes": nodes,
        "edges": edges,
        "errors": [],
    }
    if dependency_sha:
        canonical_graph["runtime_dependency_sha256"] = dependency_sha
    graph_sha256 = canonical_sha256(canonical_graph)
    return dict(canonical_graph, graph_id="graph-{}".format(graph_sha256[:16]), graph_sha256=graph_sha256)


def main():
    parser = argparse.ArgumentParser(
        description="Compile a canonical Run Graph from effective config and capability selection"
    )
    parser.add_argument("--effective", required=True, metavar="PATH")
    parser.add_argument("--selection", required=True, metavar="PATH")
    parser.add_argument("--request", required=True, metavar="PATH")
    parser.add_argument("--output", required=True, metavar="PATH")
    args = parser.parse_args()

    try:
        effective_document = load_yaml(args.effective)
        selection_document = load_yaml(args.selection)
        request_document = load_yaml(args.request)
        effective = effective_document.get("effective_runtime") or effective_document
        selection = selection_document.get("capability_selection_result") or selection_document
        request = request_document.get("run_graph_compile_request") or request_document
        graph = compile_graph(effective, selection, request)
    except (ValueError, TypeError, AttributeError, KeyError) as error:
        request = {}
        graph = invalid_graph(
            request,
            [{"code": "INVALID_INPUT", "message": str(error)}],
        )

    write_result(args.output, graph)
    if graph.get("status") != "READY":
        for error in graph.get("errors") or []:
            print("{}: {}".format(error.get("code"), error.get("message")), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
