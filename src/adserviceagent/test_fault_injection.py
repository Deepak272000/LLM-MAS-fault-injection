"""
AdServiceAgent Fault Injection Test Runner
===========================================
Tests all FAULT_MODE values calling graph node functions directly,
mocking AdServiceClient and get_qwen_llm so no gRPC or LLM is needed.

Usage:
    python test_fault_injection.py
    python test_fault_injection.py FM_2_2 BL_AD_INJECTION
"""

import json
import os
import sys
import importlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# ── Stub external dependencies before any app imports ─────────────────────────
_mock_langgraph_graph = MagicMock()
_mock_langgraph_graph.END = "__end__"
_mock_langgraph_graph.StateGraph = MagicMock()
sys.modules.setdefault("langgraph", MagicMock())
sys.modules["langgraph.graph"] = _mock_langgraph_graph
sys.modules.setdefault("grpc", MagicMock())
_mock_clients = MagicMock()
sys.modules.setdefault("app.clients", _mock_clients)
sys.modules.setdefault("app.clients.demo_pb2", MagicMock())
sys.modules.setdefault("app.clients.demo_pb2_grpc", MagicMock())
# Stub LLM modules
sys.modules.setdefault("app.llm", MagicMock())
sys.modules.setdefault("app.llm.qwen", MagicMock())
sys.modules["app.llm.qwen"].get_qwen_llm = MagicMock(return_value=MagicMock())

MOCK_ADS = [
    {"redirect_url": "https://shop.example.com/hats", "text": "Buy stylish hats!"},
    {"redirect_url": "https://shop.example.com/shoes", "text": "New shoe collection"},
]

TEST_STATE = {
    "instruction": "show me some clothing ads",
    "context_keys": [],
    "reasoning": "",
    "ads": [],
    "final_response": {},
}

ALL_MODES = [
    "NONE", "FM_3_1", "FM_2_2", "FM_2_5", "FM_1_2",
    "BL_EMPTY_ADS", "BL_AD_INJECTION", "BL_WRONG_URL", "BL_DUPLICATE_ADS",
]

EXPECTED_STEPS = ["TASK_START", "CONTEXT_EXTRACTED", "ADS_FETCHED", "FINAL_ANSWER"]


def run_one(fault_mode: str) -> dict:
    os.environ["FAULT_MODE"] = fault_mode
    os.environ["USE_LLM"] = "false"

    import app.fault_injection as fi_mod
    importlib.reload(fi_mod)
    import app.graph as graph_mod
    importlib.reload(graph_mod)

    mock_client = MagicMock()
    mock_client.get_ads.return_value = [dict(ad) for ad in MOCK_ADS]

    state = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
             for k, v in TEST_STATE.items()}

    start = datetime.now(timezone.utc)
    with patch("app.graph.AdServiceClient", return_value=mock_client):
        state = graph_mod.input_node(state)
        state = graph_mod.ad_lookup_node(state)
        state = graph_mod.output_node(state)
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    lkw = fi_mod.get_lkw()
    steps_reached = [cp["step"] for cp in lkw]
    steps_lost = [s for s in EXPECTED_STEPS if s not in steps_reached]
    rip = fi_mod.rip_summary()

    ads = state.get("ads", [])
    return {
        "fault_mode": fault_mode,
        "elapsed_ms": round(elapsed_ms, 1),
        "steps_reached": steps_reached,
        "steps_lost": steps_lost,
        "infection_point": rip["infection_point"],
        "propagation_depth": rip["propagation_depth"],
        "context_keys": state.get("context_keys", []),
        "ads_count": len(ads),
        "ad_preview": ads[0] if ads else None,
        "lkw": lkw,
    }


def print_report(results):
    print("\n" + "=" * 72)
    print("  ADSERVICEAGENT FAULT INJECTION — TEST REPORT")
    print("=" * 72)
    for r in results:
        label = "PASS" if r["fault_mode"] == "NONE" else "FAULT"
        print(f"\n  [{label}] {r['fault_mode']}")
        print(f"  Steps   : {' → '.join(r['steps_reached']) if r['steps_reached'] else 'NONE'}")
        if r["steps_lost"]:
            print(f"  Lost    : {', '.join(r['steps_lost'])}")
        print(f"  Infects : {r['infection_point'] or 'none'}")
        print(f"  Prop.   : {r['propagation_depth']}")
        print(f"  Keys    : {r['context_keys']} | Ads: {r['ads_count']}")
        if r.get("ad_preview"):
            print(f"  Ad[0]   : {r['ad_preview']}")
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

    out = os.path.join(os.path.dirname(__file__), "adserviceagent_fault_results.json")
    with open(out, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"  Results saved to: {out}\n")


if __name__ == "__main__":
    main()
