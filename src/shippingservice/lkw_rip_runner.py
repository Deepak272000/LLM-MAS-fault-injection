"""
LKW + RIP Test Runner — Shippingservice Fault Injection Experiment
==================================================================
Runs paired experiments (baseline vs. each fault mode) against the
ShippingOrchestrator and produces a structured RIP analysis report.

LKW (Last Known Well) checkpoints:
  TASK_START, QUOTE_DONE, CARRIER_DONE, TRACKING_DONE, SAVE_DONE, FINAL_ANSWER

RIP (Reachability → Infection → Propagation) analysis:
  Reachability   — which checkpoints were reached
  Infection      — which checkpoint first shows deviant data
  Propagation    — how many downstream steps were skipped or corrupted

Faults tested:
  NONE              — baseline (no fault)
  FM_1_2            — Category 1: Incorrect Task Decomposition
  FM_2_2            — Category 2: Hallucinated Tool Output
  FM_3_1            — Category 3: Premature Termination
  BL_SHIPMENT_LOST  — Business Logic: Shipment Lost

Usage:
  python lkw_rip_runner.py

  Results are printed to stdout as a formatted report and saved to:
    lkw_rip_results.json
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone


# ── Test inputs (deterministic, used identically for every run) ───────────────

TEST_ADDRESS = {
    "street_address": "123 Main St",
    "city":           "Springfield",
    "state":          "IL",
    "country":        "US",
    "zip_code":       62701,
}

TEST_ITEMS = [
    {"product_id": "OLJCESPC7Z", "quantity": 2},
    {"product_id": "66VCHSJNUP", "quantity": 1},
]

FAULTS_TO_TEST = [
    "NONE",
    "FM_1_2",
    "FM_2_2",
    "FM_2_5",
    "FM_3_1",
    "BL_SHIPMENT_LOST",
    "BL_INVENTORY_MISMATCH",
    "BL_VENDOR_NEGOTIATION",
    "BL_CUSTOMER_ESCALATION",
    "BL_REFUND_REASONING",
    "BL_COMPLIANCE_AMBIGUITY",
]


# ── Run a single experiment ───────────────────────────────────────────────────

async def run_experiment(fault_mode: str) -> dict:
    """
    Set FAULT_MODE env var, reimport orchestrator with fresh fault state,
    run ship_order, and return the LKW trace + RIP summary.
    """
    os.environ["FAULT_MODE"] = fault_mode

    # Force reimport of fault_injection so FAULT_MODE is picked up fresh
    if "fault_injection" in sys.modules:
        del sys.modules["fault_injection"]
    if "orchestrator" in sys.modules:
        del sys.modules["orchestrator"]

    # pylint: disable=import-outside-toplevel
    from orchestrator import ShippingOrchestrator  # noqa: PLC0415

    orchestrator = ShippingOrchestrator()

    start = datetime.now(timezone.utc)
    try:
        result = await orchestrator.ship_order(TEST_ADDRESS, TEST_ITEMS, capture_partial_trace=True)
        lkw    = result.get("_lkw", {})
        error  = None
    except Exception as exc:
        lkw   = {}
        error = str(exc)

    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return {
        "fault_mode":  fault_mode,
        "elapsed_ms":  round(elapsed_ms, 1),
        "error":       error,
        "lkw":         lkw,
    }


# ── Compare baseline vs fault ─────────────────────────────────────────────────

def compare_to_baseline(baseline: dict, fault: dict) -> dict:
    """
    Produce a side-by-side RIP deviation report showing what the fault
    caused relative to the clean baseline run.
    """
    b_rip = baseline.get("lkw", {}).get("rip_summary", {})
    f_rip = fault.get("lkw", {}).get("rip_summary", {})

    b_reached  = set(b_rip.get("reachability", []))
    f_reached  = set(f_rip.get("reachability", []))
    lost_steps = sorted(b_reached - f_reached)

    return {
        "fault_mode":            fault["fault_mode"],
        "elapsed_ms":            fault["elapsed_ms"],
        "baseline_steps":        sorted(b_reached),
        "fault_steps":           sorted(f_reached),
        "steps_lost":            lost_steps,
        "infection_point":       f_rip.get("infection_point"),
        "propagation_depth":     f_rip.get("propagation_depth", 0),
        "error":                 fault.get("error"),
    }


# ── Print formatted report ────────────────────────────────────────────────────

def print_report(comparisons: list[dict]):
    sep = "=" * 70
    print(f"\n{sep}")
    print("  LKW + RIP FAULT INJECTION REPORT — ShippingService")
    print(f"  Run at: {datetime.now(timezone.utc).isoformat()}")
    print(sep)

    for c in comparisons:
        print(f"\n  Fault Mode   : {c['fault_mode']}")
        print(f"  Elapsed      : {c['elapsed_ms']} ms")
        print(f"  Baseline Steps : {c['baseline_steps']}")
        print(f"  Fault Steps    : {c['fault_steps']}")
        print(f"  Steps Lost     : {c['steps_lost'] or 'None (full path reached)'}")
        print(f"  Infection Point: {c['infection_point'] or 'None detected'}")
        print(f"  Propagation Depth: {c['propagation_depth']}")
        if c["error"]:
            print(f"  Error        : {c['error']}")
        print(f"  {'-' * 66}")

    print(f"\n{sep}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    print("\n[LKW-RIP Runner] Starting experiments...\n")
    results = []

    for fault in FAULTS_TO_TEST:
        print(f"  Running: FAULT_MODE={fault} ...")
        result = await run_experiment(fault)
        results.append(result)
        print(f"  Done.  elapsed={result['elapsed_ms']}ms  "
              f"error={result['error'] or 'None'}")

    # Identify baseline
    baseline = next(r for r in results if r["fault_mode"] == "NONE")

    # Build comparisons (skip baseline itself)
    comparisons = [
        compare_to_baseline(baseline, r)
        for r in results
        if r["fault_mode"] != "NONE"
    ]

    print_report(comparisons)

    # Save full results for analysis
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_address": TEST_ADDRESS,
        "test_items":   TEST_ITEMS,
        "raw_results":  results,
        "rip_analysis": comparisons,
    }
    out_path = os.path.join(os.path.dirname(__file__), "lkw_rip_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[LKW-RIP Runner] Results saved to: {out_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
