"""
PaymentAgent Fault Injection Test Runner
=========================================
Tests all FAULT_MODE values by calling PaymentAgent.run() directly,
bypassing the LangGraph router and mocking MongoDB so no external
services are required.

Usage:
    python test_fault_injection.py              # all modes
    python test_fault_injection.py FM_3_1       # single mode
    python test_fault_injection.py NONE         # baseline only

Output: console report + paymentagent_fault_results.json
"""

import asyncio
import json
import os
import sys
import importlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

# ── Test payload (valid VISA card) ─────────────────────────────────────────────
TEST_PAYLOAD = {
    "query":                         "Process payment for order",
    "currency_code":                 "USD",
    "units":                         10,
    "nanos":                         990000000,
    "credit_card_number":            "4111111111111111",  # Visa test number
    "credit_card_cvv":               123,
    "credit_card_expiration_year":   2030,
    "credit_card_expiration_month":  12,
}

ALL_MODES = [
    "NONE",
    "FM_3_1",
    "FM_2_2",
    "FM_2_5",
    "FM_1_2",
    "BL_TRANSACTION_LOST",
    "BL_DOUBLE_CHARGE",
    "BL_AMOUNT_TAMPERING",
    "BL_CARD_DECLINED",
]

EXPECTED_STEPS = ["TASK_START", "CARD_VALIDATED", "CHARGE_DONE", "SAVE_DONE", "FINAL_ANSWER"]


async def run_one(fault_mode: str) -> dict:
    """Run PaymentAgent with a specific FAULT_MODE and collect results."""
    # Set env var BEFORE importing fault_injection so FAULT_MODE is picked up
    os.environ["FAULT_MODE"] = fault_mode

    # Force-reload fault_injection so FAULT_MODE constant is refreshed
    import app.fault_injection as fi_mod
    importlib.reload(fi_mod)

    # Also reload agent so it picks up the reloaded fi module
    import app.agent as agent_mod
    importlib.reload(agent_mod)

    AgentClass = agent_mod.PaymentAgent

    agent = AgentClass()
    start = datetime.now(timezone.utc)

    # Mock save_transaction so MongoDB is not required
    with patch("app.agent.save_transaction", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = "mock-db-id-123"
        result = await agent.run(**TEST_PAYLOAD)

    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    lkw = result.get("lkw", [])
    steps_reached = [cp["step"] for cp in lkw]
    steps_lost = [s for s in EXPECTED_STEPS if s not in steps_reached]

    # Compute infection point
    infection = None
    for cp in lkw:
        d = cp.get("data", {})
        if any([
            d.get("hallucinated"), d.get("amount_tampered"),
            d.get("validation_bypassed"), d.get("save_skipped"),
            d.get("double_charge"), d.get("forced_decline"),
            d.get("premature_termination"),
            "FAKE" in str(d.get("transaction_id", "")),
            "PREMATURE" in str(d.get("transaction_id", "")),
        ]):
            if infection is None:
                infection = cp["step"]

    return {
        "fault_mode":        fault_mode,
        "elapsed_ms":        round(elapsed_ms, 1),
        "steps_reached":     steps_reached,
        "steps_lost":        steps_lost,
        "infection_point":   infection,
        "propagation_depth": len(steps_lost),
        "success":           result.get("data", {}).get("success"),
        "transaction_id":    result.get("data", {}).get("transaction_id"),
        "error":             result.get("data", {}).get("error"),
        "lkw":               lkw,
    }


def print_report(results: list[dict]):
    print("\n" + "=" * 70)
    print("  PAYMENTAGENT FAULT INJECTION — TEST REPORT")
    print("=" * 70)
    baseline = next((r for r in results if r["fault_mode"] == "NONE"), None)
    baseline_steps = set(baseline["steps_reached"]) if baseline else set(EXPECTED_STEPS)

    for r in results:
        status = "PASS" if r["fault_mode"] == "NONE" else "FAULT"
        print(f"\n  [{status}] {r['fault_mode']}")
        print(f"  Elapsed       : {r['elapsed_ms']} ms")
        print(f"  Steps reached : {' → '.join(r['steps_reached']) if r['steps_reached'] else 'NONE'}")
        if r["steps_lost"]:
            print(f"  Steps lost    : {', '.join(r['steps_lost'])}")
        print(f"  Infection at  : {r['infection_point'] or 'none detected'}")
        print(f"  Propagation   : {r['propagation_depth']}")
        print(f"  Success       : {r['success']}")
        print(f"  Transaction   : {r['transaction_id'] or r.get('error', 'N/A')}")

    print("\n" + "=" * 70)
    passed = sum(1 for r in results if not r["steps_lost"] and r["fault_mode"] == "NONE")
    faults_with_evidence = sum(1 for r in results if r["fault_mode"] != "NONE" and
                                (r["steps_lost"] or r["infection_point"]))
    print(f"  Baseline clean    : {'YES' if passed else 'NO'}")
    print(f"  Faults with evidence: {faults_with_evidence} / {len(results)-1}")
    print("=" * 70 + "\n")


async def main():
    modes = sys.argv[1:] if len(sys.argv) > 1 else ALL_MODES

    # Always run NONE first as baseline
    if "NONE" not in modes:
        modes = ["NONE"] + modes

    print(f"\nRunning {len(modes)} fault modes: {', '.join(modes)}")

    results = []
    for mode in modes:
        print(f"  → {mode} ...", end=" ", flush=True)
        try:
            r = await run_one(mode)
            results.append(r)
            print(f"done ({r['elapsed_ms']} ms) | steps={len(r['steps_reached'])}/{len(EXPECTED_STEPS)}")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"fault_mode": mode, "error": str(e)})

    # Reset FAULT_MODE to NONE after all runs
    os.environ["FAULT_MODE"] = "NONE"

    print_report(results)

    out_path = os.path.join(os.path.dirname(__file__), "paymentagent_fault_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "results": results
        }, f, indent=2)
    print(f"  Results saved to: {out_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
