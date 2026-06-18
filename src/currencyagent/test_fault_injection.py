"""
CurrencyAgent Fault Injection Test Runner
==========================================
Tests all FAULT_MODE values by calling CurrencyAgent.run() directly,
mocking the gRPC client so no CurrencyService needs to be running.

Usage:
    python test_fault_injection.py
    python test_fault_injection.py FM_2_2
"""

import json
import os
import sys
import importlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

MOCK_CONVERT_RESULT = {"currency_code": "EUR", "units": 9, "nanos": 230000000}
MOCK_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]

TEST_PAYLOAD = {
    "query":         "convert 10 USD to EUR",
    "action":        "convert",
    "from_currency": "USD",
    "units":         10,
    "nanos":         0,
    "to_currency":   "EUR",
}

ALL_MODES = [
    "NONE", "FM_3_1", "FM_2_2", "FM_2_5", "FM_1_2",
    "BL_RATE_MANIPULATION", "BL_CURRENCY_UNAVAILABLE",
    "BL_STALE_RATE", "BL_CONVERSION_OVERFLOW",
]

EXPECTED_STEPS = ["TASK_START", "CONVERT_DONE", "FINAL_ANSWER"]


def run_one(fault_mode: str) -> dict:
    os.environ["FAULT_MODE"] = fault_mode

    import app.fault_injection as fi_mod
    importlib.reload(fi_mod)
    import app.agent as agent_mod
    importlib.reload(agent_mod)

    mock_client = MagicMock()
    mock_client.convert.return_value = dict(MOCK_CONVERT_RESULT)
    mock_client.get_supported_currencies.return_value = list(MOCK_CURRENCIES)

    agent_mod.client = mock_client
    agent = agent_mod.CurrencyAgent()

    start = datetime.now(timezone.utc)
    result = agent.run(**TEST_PAYLOAD)
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    lkw = result.get("lkw", [])
    steps_reached = [cp["step"] for cp in lkw]
    steps_lost = [s for s in EXPECTED_STEPS if s not in steps_reached]

    infection = None
    for cp in lkw:
        d = cp.get("data", {})
        if any([d.get("hallucinated"), d.get("amount_tampered"), d.get("currency_swapped"),
                d.get("rate_manipulated"), d.get("stale_rate"), d.get("overflow"),
                d.get("premature_termination"), d.get("unavailable")]):
            if infection is None:
                infection = cp["step"]

    return {
        "fault_mode": fault_mode,
        "elapsed_ms": round(elapsed_ms, 1),
        "steps_reached": steps_reached,
        "steps_lost": steps_lost,
        "infection_point": infection,
        "propagation_depth": len(steps_lost),
        "data": result.get("data", {}),
        "lkw": lkw,
    }


def print_report(results):
    print("\n" + "=" * 70)
    print("  CURRENCYAGENT FAULT INJECTION — TEST REPORT")
    print("=" * 70)
    for r in results:
        label = "PASS" if r["fault_mode"] == "NONE" else "FAULT"
        print(f"\n  [{label}] {r['fault_mode']}")
        print(f"  Steps   : {' → '.join(r['steps_reached']) if r['steps_reached'] else 'NONE'}")
        if r["steps_lost"]:
            print(f"  Lost    : {', '.join(r['steps_lost'])}")
        print(f"  Infects : {r['infection_point'] or 'none'}")
        print(f"  Prop.   : {r['propagation_depth']}")
        print(f"  Data    : {r['data']}")
    faults_with_evidence = sum(1 for r in results if r["fault_mode"] != "NONE" and
                                (r["steps_lost"] or r["infection_point"]))
    print(f"\n  Faults with evidence: {faults_with_evidence} / {len(results)-1}")
    print("=" * 70 + "\n")


def main():
    modes = sys.argv[1:] if len(sys.argv) > 1 else ALL_MODES
    if "NONE" not in modes:
        modes = ["NONE"] + modes

    print(f"\nRunning {len(modes)} fault modes...")
    results = []
    for mode in modes:
        print(f"  → {mode} ...", end=" ", flush=True)
        try:
            r = run_one(mode)
            results.append(r)
            print(f"done | steps={len(r['steps_reached'])}/{len(EXPECTED_STEPS)} | infects={r['infection_point']}")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"fault_mode": mode, "error": str(e)})

    os.environ["FAULT_MODE"] = "NONE"
    print_report(results)

    out = os.path.join(os.path.dirname(__file__), "currencyagent_fault_results.json")
    with open(out, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"  Results saved to: {out}\n")


if __name__ == "__main__":
    main()
