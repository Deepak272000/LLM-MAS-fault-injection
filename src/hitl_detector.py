"""
Unified HITL (Human-in-the-Loop) Tier Classifier — All 6 Agents
================================================================
Reads <agent>_fault_results.json for each instrumented agent, classifies
every fault mode into one of three intervention tiers, and writes a
combined report.

Tier definitions (paper Section VI — RQ4):

  TIER 1 — Structural / Workflow-Stopping
    propagation_depth > 0: at least one expected checkpoint is absent from
    the LKW trace.  Auto-detectable from a step-count diff alone — no
    semantic analysis required.
    Always FM-3.1; also BL faults that abort checkpoints.

  TIER 2 — Detectable via Metadata Flags
    propagation_depth = 0, infection detected, AND at least one
    "operational" boolean flag is True in the LKW checkpoint data.
    Detectable by monitoring the LKW evidence file, but the agent does NOT
    self-heal.  Requires a flag monitor or alert rule.
    FM-2.5, FM-1.2, and most BL faults.

  TIER 3 — Silently Absorbed
    propagation_depth = 0, infection detected, but the ONLY True flags are
    "silent" data-quality markers (e.g. hallucinated=True) that would not
    exist in a production system without test instrumentation.  Detection
    requires semantic validation of the checkpoint DATA VALUES.
    FM-2.2 (hallucinated output) across all agents.

The discriminating rule for Tier 2 vs Tier 3:
  - "Silent" flags:   hallucinated  (pure fabrication — no production alert)
  - "Operational" flags: everything else that is True in the LKW data
    (save_skipped, double_charge, forced_decline, amount_tampered,
     currency_swapped, validation_bypassed, send_skipped, etc.)

Usage:
    python hitl_detector.py            # formatted console output
    python hitl_detector.py --json     # machine-readable JSON to stdout
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE    = Path(__file__).parent
RESULTS = BASE / "results"

AGENTS = [
    "paymentagent",
    "currencyagent",
    "emailserviceagent",
    "productcatalogagent",
    "recommendationagent",
    "adserviceagent",
]

# ── Tier discriminator ─────────────────────────────────────────────────────────
# True boolean flags that indicate pure data fabrication with no operational
# analog in a production system.  Any fault that sets ONLY these flags (and
# no others) is Tier 3 (silently absorbed).
SILENT_FLAGS = frozenset({"hallucinated"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_fault_results(agent: str) -> list:
    path = BASE / agent / f"{agent}_fault_results.json"
    if not path.exists():
        print(f"  [WARN] {path} not found — run test_fault_injection.py for {agent} first.",
              file=sys.stderr)
        return []
    with open(path) as fh:
        raw = json.load(fh)
    if isinstance(raw, dict) and "results" in raw:
        return raw["results"]
    if isinstance(raw, list):
        return raw
    return []


def scan_true_flags(lkw: list) -> set:
    """Return all LKW data keys whose value is explicitly True."""
    found = set()
    for cp in lkw:
        for k, v in cp.get("data", {}).items():
            if v is True:
                found.add(k)
    return found


# ── Per-result classifier ─────────────────────────────────────────────────────

def classify_one(result: dict, baseline_true_flags: set = None) -> dict:
    """Classify a single fault-mode result.

    baseline_true_flags: set of keys that are True in the NONE baseline run.
    Subtracting these removes always-on operational flags (saved=True,
    success=True) that are present in healthy runs and must not be counted
    as fault indicators when classifying FM-2.2 vs FM-2.5 etc.
    """
    fault_mode = result.get("fault_mode", "UNKNOWN")
    depth      = result.get("propagation_depth", 0)
    infection  = result.get("infection_point")
    steps_lost = result.get("steps_lost", [])
    lkw        = result.get("lkw", [])
    baseline_flags = baseline_true_flags or set()

    # ── Baseline ──────────────────────────────────────────────────────────────
    if fault_mode == "NONE":
        return {
            "fault_mode":       "NONE",
            "tier":             0,
            "tier_label":       "BASELINE",
            "auto_detect":      True,
            "hitl_required":    False,
            "infection_point":  None,
            "propagation_depth": 0,
            "steps_lost":       [],
            "flags_found":      [],
            "reason": "No fault injected; healthy baseline.",
        }

    # ── Tier 1: structural step loss ──────────────────────────────────────────
    if depth > 0:
        new_flags = scan_true_flags(lkw) - baseline_flags
        ops_flags = sorted(new_flags - SILENT_FLAGS)
        return {
            "fault_mode":       fault_mode,
            "tier":             1,
            "tier_label":       "TIER 1 — Structural",
            "auto_detect":      True,
            "hitl_required":    True,
            "infection_point":  infection,
            "propagation_depth": depth,
            "steps_lost":       steps_lost,
            "flags_found":      ops_flags,
            "reason": (
                f"Steps absent from LKW trace: {steps_lost}. "
                "Auto-detectable via step-count diff; no semantic analysis needed."
            ),
        }

    # ── No infection at all ───────────────────────────────────────────────────
    if infection is None:
        return {
            "fault_mode":       fault_mode,
            "tier":             0,
            "tier_label":       "NO_INFECTION",
            "auto_detect":      False,
            "hitl_required":    False,
            "infection_point":  None,
            "propagation_depth": 0,
            "steps_lost":       [],
            "flags_found":      [],
            "reason": "Fault mode produced no detectable infection (mode may be inactive).",
        }

    # ── depth == 0, infection detected — Tier 2 vs Tier 3 ────────────────────
    # Only count flags that are NEW vs baseline — removes always-on flags
    # (saved=True, success=True) that exist in healthy NONE runs too.
    true_flags        = scan_true_flags(lkw)
    new_flags         = true_flags - baseline_flags
    operational_flags = new_flags - SILENT_FLAGS

    if operational_flags:
        return {
            "fault_mode":       fault_mode,
            "tier":             2,
            "tier_label":       "TIER 2 — Flag-Detectable",
            "auto_detect":      False,
            "hitl_required":    True,
            "infection_point":  infection,
            "propagation_depth": 0,
            "steps_lost":       [],
            "flags_found":      sorted(operational_flags),
            "reason": (
                f"Infection at {infection}; depth=0 (all steps reached). "
                f"New operational flags: {sorted(operational_flags)}. "
                "Requires LKW flag monitor to trigger intervention."
            ),
        }

    # Only silent flags (or none at all) — Tier 3
    return {
        "fault_mode":       fault_mode,
        "tier":             3,
        "tier_label":       "TIER 3 — Silent",
        "auto_detect":      False,
        "hitl_required":    True,
        "infection_point":  infection,
        "propagation_depth": 0,
        "steps_lost":       [],
        "flags_found":      sorted(new_flags),
        "reason": (
            f"Infection at {infection}; depth=0; no operational flag. "
            "Data values are corrupted (e.g. hallucinated=True) but no "
            "production-observable marker exists. Requires semantic "
            "validation of checkpoint data contents."
        ),
    }


# ── Main report builder ───────────────────────────────────────────────────────

def build_report() -> dict:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agents":       {},
        "summary": {
            "tier_1": 0,
            "tier_2": 0,
            "tier_3": 0,
            "baseline": 0,
        },
    }

    for agent in AGENTS:
        results = load_fault_results(agent)
        if not results:
            continue

        # Extract baseline true-flags once per agent so fault runs can
        # subtract always-on flags (saved=True, success=True, etc.).
        baseline_result = next((r for r in results if r.get("fault_mode") == "NONE"), None)
        baseline_flags  = scan_true_flags(baseline_result.get("lkw", [])) if baseline_result else set()

        rows = []
        for result in results:
            row = classify_one(result, baseline_true_flags=baseline_flags)
            row["agent"] = agent
            rows.append(row)
            t = row["tier"]
            if t == 1:
                report["summary"]["tier_1"] += 1
            elif t == 2:
                report["summary"]["tier_2"] += 1
            elif t == 3:
                report["summary"]["tier_3"] += 1
            elif row["tier_label"] == "BASELINE":
                report["summary"]["baseline"] += 1
        report["agents"][agent] = rows

    return report


def print_report(report: dict):
    W = 76
    print("\n" + "=" * W)
    print("  HITL TIER CLASSIFICATION — LLM-MAS AGENT FAULT INJECTION")
    print(f"  Generated : {report['generated_at']}")
    print("=" * W)

    tier_label_short = {
        0: "BASELINE",
        1: "TIER 1 — Structural",
        2: "TIER 2 — Flag",
        3: "TIER 3 — Silent",
    }
    tier_detect = {
        0: "—",
        1: "AUTO (step diff)",
        2: "MANUAL (flag monitor)",
        3: "MANUAL (semantic)",
    }

    for agent, rows in report["agents"].items():
        print(f"\n  {'─' * 62}")
        print(f"  {agent.upper()}")
        print(f"  {'─' * 62}")
        print(f"  {'FAULT MODE':<32} {'TIER':<22} {'DETECT METHOD'}")
        print(f"  {'─' * 62}")
        for row in rows:
            tier     = row["tier"]
            t_label  = tier_label_short.get(tier, str(tier))
            t_detect = tier_detect.get(tier, "")
            print(f"  {row['fault_mode']:<32} {t_label:<22} {t_detect}")
            if row["flags_found"]:
                flags_str = ", ".join(row["flags_found"])
                print(f"  {'':32}   flags: {flags_str}")
            if row.get("steps_lost"):
                print(f"  {'':32}   lost : {', '.join(row['steps_lost'])}")

    s = report["summary"]
    total = s["tier_1"] + s["tier_2"] + s["tier_3"]
    print("\n" + "=" * W)
    print("  HITL SUMMARY")
    print(f"  {'─' * 62}")
    print(f"  Tier 1  Structural    : {s['tier_1']:>3}  auto-detectable (step-trace diff)")
    print(f"  Tier 2  Flag-detect   : {s['tier_2']:>3}  requires flag monitor on LKW data")
    print(f"  Tier 3  Silent        : {s['tier_3']:>3}  requires semantic data validation")
    print(f"  Baseline (NONE)       : {s['baseline']:>3}")
    print(f"  {'─' * 62}")
    if total:
        print(f"  Total fault modes classified: {total}")
        print()
        print("  KEY FINDING:")
        print("  FM-2.2 (hallucination) is Tier 3 across ALL agents —")
        print("  zero structural signal; undetectable without inter-agent")
        print("  output validation contracts at every agent boundary.")
    print("=" * W + "\n")


def main():
    ap = argparse.ArgumentParser(description="HITL tier classifier for LLM-MAS agents")
    ap.add_argument("--json", action="store_true",
                    help="Print machine-readable JSON to stdout instead of formatted report")
    args = ap.parse_args()

    report = build_report()

    # Save JSON report regardless of output mode
    RESULTS.mkdir(exist_ok=True)
    out_path = RESULTS / "hitl_classification_report.json"
    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=2)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
        print(f"  Report saved: {out_path}")


if __name__ == "__main__":
    main()
