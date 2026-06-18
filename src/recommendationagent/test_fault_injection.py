"""
RecommendationAgent Fault Injection Test Runner
================================================
Tests all FAULT_MODE values calling RecommendationAgent.get_recommendations()
directly, mocking RecommendationGrpcClient so no gRPC server is needed.

Usage:
    python test_fault_injection.py
    python test_fault_injection.py FM_2_2 BL_EMPTY_RECS
"""

import json
import os
import sys
import importlib
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Stub gRPC and proto stubs at module load time
sys.modules.setdefault("grpc", MagicMock())
_mock_clients = MagicMock()
sys.modules.setdefault("app.clients", _mock_clients)
sys.modules.setdefault("app.clients.demo_pb2", MagicMock())
sys.modules.setdefault("app.clients.demo_pb2_grpc", MagicMock())

MOCK_REC_IDS = ["PROD-042", "PROD-017", "PROD-009"]
TEST_USER_ID = "user-abc123"
TEST_PRODUCT_IDS = ["PROD-001", "PROD-002"]

ALL_MODES = [
    "NONE", "FM_3_1", "FM_2_2", "FM_2_5", "FM_1_2",
    "BL_EMPTY_RECS", "BL_SELF_RECOMMENDATION",
    "BL_INJECTION_RECS", "BL_SHUFFLED_RECS",
]

EXPECTED_STEPS = ["TASK_START", "RECOMMEND_DONE", "FINAL_ANSWER"]


def run_one(fault_mode: str) -> dict:
    os.environ["FAULT_MODE"] = fault_mode

    import app.fault_injection as fi_mod
    importlib.reload(fi_mod)
    import app.agent as agent_mod
    importlib.reload(agent_mod)

    mock_client = MagicMock()
    mock_client.list_recommendations.return_value = list(MOCK_REC_IDS)

    agent_mod.client = mock_client
    agent = agent_mod.RecommendationAgent()

    start = datetime.now(timezone.utc)
    result = agent.get_recommendations(
        user_id=TEST_USER_ID,
        product_ids=TEST_PRODUCT_IDS,
    )
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    lkw = fi_mod.get_lkw()
    steps_reached = [cp["step"] for cp in lkw]
    steps_lost = [s for s in EXPECTED_STEPS if s not in steps_reached]
    rip = fi_mod.rip_summary()

    return {
        "fault_mode": fault_mode,
        "elapsed_ms": round(elapsed_ms, 1),
        "steps_reached": steps_reached,
        "steps_lost": steps_lost,
        "infection_point": rip["infection_point"],
        "propagation_depth": rip["propagation_depth"],
        "action": result.get("action"),
        "recs": result.get("recommended_product_ids", []),
        "lkw": lkw,
    }


def print_report(results):
    print("\n" + "=" * 72)
    print("  RECOMMENDATIONAGENT FAULT INJECTION — TEST REPORT")
    print("=" * 72)
    for r in results:
        label = "PASS" if r["fault_mode"] == "NONE" else "FAULT"
        print(f"\n  [{label}] {r['fault_mode']}")
        print(f"  Steps   : {' → '.join(r['steps_reached']) if r['steps_reached'] else 'NONE'}")
        if r["steps_lost"]:
            print(f"  Lost    : {', '.join(r['steps_lost'])}")
        print(f"  Infects : {r['infection_point'] or 'none'}")
        print(f"  Prop.   : {r['propagation_depth']}")
        print(f"  Action  : {r['action']} | Recs: {r['recs']}")
    faults_with_evidence = sum(
        1 for r in results if r["fault_mode"] != "NONE" and
        (r["steps_lost"] or r["infection_point"])
    )
    print(f"\n  Faults with evidence: {faults_with_evidence} / {len(results)-1}")
    print("=" * 72 + "\n")


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
            import traceback; traceback.print_exc()
            results.append({"fault_mode": mode, "error": str(e)})

    os.environ["FAULT_MODE"] = "NONE"
    print_report(results)

    out = os.path.join(os.path.dirname(__file__), "recommendationagent_fault_results.json")
    with open(out, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"  Results saved to: {out}\n")


if __name__ == "__main__":
    main()
