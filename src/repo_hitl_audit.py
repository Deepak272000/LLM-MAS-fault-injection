"""Repo-wide HITL audit and boundary coverage sweep.

This script combines:
- existing HITL classification reports
- stability summary data
- static instrumentation coverage across Python packages

It is meant to answer two questions quickly:
1. Which scenarios are auto-detectable vs manual-review HITL cases?
2. Which agent/service packages already carry boundary flags, and which do not?
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
OUTPUT = RESULTS / "repo_hitl_audit.json"

MARKERS = ("BOUNDARY_CHECK", "boundary_contract", "handoff_contract", "failure_class", "rip_summary")
BOUNDARY_PROXY_GROUPS = {
    "shippingservice": "shippingagent",
}
REPORT_SOURCES = {
    "root_hitl": RESULTS / "hitl_classification_report.json",
    "shipping_hitl": BASE / "shippingservice" / "hitl_classification_report.json",
    "boundary_summary": RESULTS / "boundary_detection_summary.json",
    "cross_agent": RESULTS / "cross_agent_propagation.json",
    "stability": RESULTS / "stability_summary.json",
}


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize_hitl_report(report: dict | None) -> dict:
    if not isinstance(report, dict):
        return {"present": False}

    if isinstance(report.get("agents"), dict):
        total = 0
        hitl_required = 0
        tier_counts = {"tier_0": 0, "tier_1": 0, "tier_2": 0, "tier_3": 0}
        for rows in report.get("agents", {}).values():
            for row in rows:
                total += 1
                tier = row.get("tier")
                if tier == 0:
                    tier_counts["tier_0"] += 1
                elif tier == 1:
                    tier_counts["tier_1"] += 1
                elif tier == 2:
                    tier_counts["tier_2"] += 1
                elif tier == 3:
                    tier_counts["tier_3"] += 1
                if row.get("hitl_required"):
                    hitl_required += 1
        return {
            "present": True,
            "kind": "agent_fault_results",
            "total_scenarios": total,
            "hitl_required": hitl_required,
            "summary": report.get("summary", tier_counts),
        }

    if "classifications" in report or "tier_counts" in report:
        return {
            "present": True,
            "kind": "scenario_classification",
            "total_scenarios": report.get("total_scenarios", len(report.get("classifications", []))),
            "hitl_required": report.get("hitl_required_count", 0),
            "summary": report.get("tier_counts", {}),
        }

    if "totals" in report and "shipping" in report:
        shipping = report.get("shipping", [])
        fault_induced = sum(1 for item in shipping if item.get("failure_class") == "fault_induced")
        infra_failures = sum(1 for item in shipping if item.get("failure_class") == "infra_timeout")
        return {
            "present": True,
            "kind": "boundary_detection_summary",
            "total_scenarios": len(shipping),
            "hitl_required": report.get("totals", {}).get("manual_review_candidates", 0),
            "summary": {
                "boundary_alerts": report.get("totals", {}).get("boundary_alerts", 0),
                "signal_escapes": report.get("totals", {}).get("signal_escapes", 0),
                "fault_induced": fault_induced,
                "infra_failures": infra_failures,
            },
        }

    if "chains" in report and "summary" in report:
        summary = report.get("summary", {})
        return {
            "present": True,
            "kind": "cross_agent_propagation",
            "total_scenarios": summary.get("total_chains", len(report.get("chains", []))),
            "hitl_required": summary.get("manual_review_candidates", 0),
            "summary": {
                "boundary_alerts": summary.get("boundary_alerts", 0),
                "signal_escapes": summary.get("signal_escapes", 0),
                "downstream_clean": summary.get("downstream_clean", 0),
            },
        }

    return {"present": True, "kind": "unrecognized", "summary": {}}


def summarize_stability(report: dict | None) -> dict:
    if not isinstance(report, dict):
        return {"present": False}

    agents = report.get("agents", [])
    if not isinstance(agents, list):
        return {"present": True, "agent_count": 0, "runs_per_agent": report.get("runs_per_agent")}

    return {
        "present": True,
        "agent_count": len(agents),
        "runs_per_agent": report.get("runs_per_agent"),
        "stable_pass_total": sum(agent.get("stable_pass", 0) for agent in agents),
        "stable_fault_total": sum(agent.get("stable_fault", 0) for agent in agents),
        "unstable_total": sum(agent.get("unstable", 0) for agent in agents),
        "mean_stability_rate": round(mean(agent.get("stability_rate", 0.0) for agent in agents), 2) if agents else 0.0,
    }


def scan_python_coverage() -> dict:
    groups = defaultdict(lambda: {
        "python_files": 0,
        "boundary_files": 0,
        "analysis_files": 0,
        "marker_counts": {marker: 0 for marker in MARKERS},
        "files": [],
    })

    for path in BASE.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(BASE).as_posix()
        top = rel.split("/")[0]
        text = path.read_text(encoding="utf-8", errors="ignore")
        counts = {marker: text.count(marker) for marker in MARKERS}
        group = groups[top]
        group["python_files"] += 1

        if any(counts.values()):
            group["files"].append(rel)
            for marker, count in counts.items():
                group["marker_counts"][marker] += count
            if counts["BOUNDARY_CHECK"] or counts["boundary_contract"] or counts["handoff_contract"]:
                group["boundary_files"] += 1
            if counts["failure_class"] or counts["rip_summary"]:
                group["analysis_files"] += 1

    summaries = []
    for group_name, data in sorted(groups.items()):
        boundary_marker_total = (
            data["marker_counts"]["BOUNDARY_CHECK"]
            + data["marker_counts"]["boundary_contract"]
            + data["marker_counts"]["handoff_contract"]
        )
        summaries.append({
            "group": group_name,
            "python_files": data["python_files"],
            "boundary_files": data["boundary_files"],
            "analysis_files": data["analysis_files"],
            "boundary_marker_total": boundary_marker_total,
            "marker_counts": data["marker_counts"],
            "files": sorted(data["files"]),
        })

    groups_with_boundary_flags = [item["group"] for item in summaries if item["boundary_marker_total"] > 0]
    groups_without_boundary_flags = [
        item["group"]
        for item in summaries
        if item["boundary_marker_total"] == 0 and ("agent" in item["group"] or "service" in item["group"])
    ]
    for group, proxy_group in BOUNDARY_PROXY_GROUPS.items():
        if proxy_group in groups_with_boundary_flags and group in groups_without_boundary_flags:
            groups_without_boundary_flags.remove(group)
            groups_with_boundary_flags.append(group)

    groups_with_boundary_flags = sorted(groups_with_boundary_flags)
    groups_without_boundary_flags = sorted(groups_without_boundary_flags)

    return {
        "groups": summaries,
        "boundary_proxy_groups": BOUNDARY_PROXY_GROUPS,
        "groups_with_boundary_flags": groups_with_boundary_flags,
        "groups_without_boundary_flags": groups_without_boundary_flags,
    }


def build_report() -> dict:
    loaded_reports = {
        name: summarize_hitl_report(load_json(path))
        for name, path in REPORT_SOURCES.items()
        if name != "stability"
    }
    stability_report = summarize_stability(load_json(REPORT_SOURCES["stability"]))
    coverage = scan_python_coverage()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {name: str(path) for name, path in REPORT_SOURCES.items()},
        "hitl_reports": loaded_reports,
        "stability": stability_report,
        "coverage": coverage,
        "recommendations": {
            "boundary_flag_targets": coverage["groups_without_boundary_flags"],
            "priority": [
                "Add boundary_contract / BOUNDARY_CHECK to remaining agent handoffs.",
                "Keep shippingservice as a shim and extend coverage in shippingagent/app.",
                "Use repo_hitl_audit.json as the current snapshot for HITL readiness."
            ],
        },
    }
    return report


def print_report(report: dict) -> None:
    print("\n" + "=" * 78)
    print("  REPO-WIDE HITL AUDIT")
    print("=" * 78)

    for name, summary in report["hitl_reports"].items():
        if not summary.get("present"):
            continue
        print(f"\n  {name}: {summary.get('kind')}")
        print(f"    total_scenarios : {summary.get('total_scenarios', 'n/a')}")
        print(f"    hitl_required   : {summary.get('hitl_required', 'n/a')}")
        if summary.get("summary"):
            print(f"    summary         : {summary['summary']}")

    stability = report["stability"]
    if stability.get("present"):
        print("\n  stability")
        print(f"    agent_count       : {stability.get('agent_count', 0)}")
        print(f"    runs_per_agent    : {stability.get('runs_per_agent')}")
        print(f"    stable_pass_total : {stability.get('stable_pass_total', 0)}")
        print(f"    stable_fault_total: {stability.get('stable_fault_total', 0)}")
        print(f"    unstable_total    : {stability.get('unstable_total', 0)}")
        print(f"    mean_stability    : {stability.get('mean_stability_rate', 0.0)}%")

    coverage = report["coverage"]
    print("\n  coverage")
    print(f"    groups scanned            : {len(coverage['groups'])}")
    print(f"    groups with boundary flags : {len(coverage['groups_with_boundary_flags'])}")
    print(f"    groups without flags       : {len(coverage['groups_without_boundary_flags'])}")
    if coverage["groups_with_boundary_flags"]:
        print(f"    flag groups                : {', '.join(coverage['groups_with_boundary_flags'])}")
    if coverage["groups_without_boundary_flags"]:
        preview = coverage["groups_without_boundary_flags"][:10]
        suffix = " ..." if len(coverage["groups_without_boundary_flags"]) > 10 else ""
        print(f"    missing groups             : {', '.join(preview)}{suffix}")

    print("\n  recommendation")
    for item in report["recommendations"]["priority"]:
        print(f"    - {item}")
    print("=" * 78 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repo-wide HITL audit and coverage sweep")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    report = build_report()
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
        print(f"  Report saved: {OUTPUT}")


if __name__ == "__main__":
    main()
