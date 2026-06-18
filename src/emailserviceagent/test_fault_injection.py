"""
EmailServiceAgent Fault Injection Test Runner
===============================================
Tests all FAULT_MODE values by calling graph nodes directly,
mocking generate_email_content and EmailServiceClient so no
LLM or gRPC server is needed.

Usage:
    python test_fault_injection.py
    python test_fault_injection.py FM_2_2 BL_SEND_SKIPPED
"""

import json
import os
import sys
import importlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# ── Stub langgraph so graph.py can be imported without the package installed ──
_mock_langgraph_graph = MagicMock()
_mock_langgraph_graph.END = "__end__"
_mock_langgraph_graph.StateGraph = MagicMock()
sys.modules.setdefault("langgraph", MagicMock())
sys.modules["langgraph.graph"] = _mock_langgraph_graph
# Stub gRPC and proto stubs (grpc_client.py imports these at module level)
sys.modules.setdefault("grpc", MagicMock())
sys.modules.setdefault("demo_pb2", MagicMock())
sys.modules.setdefault("demo_pb2_grpc", MagicMock())

MOCK_GENERATE_RESULT = {
    "email_type": "order_confirmation",
    "subject": "Your order has been confirmed",
    "body": "Hello Customer, your order ORDER-123 is confirmed. Total: 29.99 USD.",
    "llm_used": False,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_llm_calls": 0,
    "total_tokens": 0,
}

MOCK_SEND_RESULT = {"status": "sent"}

TEST_PAYLOAD = {
    "email":            "customer@example.com",
    "order_id":         "ORDER-123",
    "user_name":        "Customer",
    "currency_code":    "USD",
    "total":            29.99,
    "items":            [{"name": "Hat", "quantity": 1, "price": "29.99"}],
    "shipping_address": {"street_address": "123 Main St", "city": "Springfield",
                         "state": "IL", "country": "US", "zip_code": 62701},
}

INITIAL_STATE = {
    "request":            TEST_PAYLOAD,
    "email_type":         "",
    "subject":            "",
    "body":               "",
    "llm_used":           False,
    "microservice_status": "",
}

ALL_MODES = [
    "NONE", "FM_3_1", "FM_2_2", "FM_2_5", "FM_1_2",
    "BL_SEND_SKIPPED", "BL_DOUBLE_SEND", "BL_CORRUPTED_BODY", "BL_WRONG_CUSTOMER",
]

EXPECTED_STEPS = ["TASK_START", "EMAIL_GENERATED", "EMAIL_SENT", "FINAL_ANSWER"]


def run_one(fault_mode: str) -> dict:
    os.environ["FAULT_MODE"] = fault_mode

    # Evict only the two modules that hold per-run state so each call gets a
    # fresh import.  importlib.reload() is unreliable on Python 3.9/SPEED —
    # it can return a new module object while graph_mod still holds the old fi
    # reference, causing record_checkpoint() and get_lkw() to diverge.
    sys.modules.pop("app.fault_injection", None)
    sys.modules.pop("app.graph", None)

    import app.fault_injection as fi_mod   # fresh: FAULT_MODE read from env, _global_lkw=[]
    import app.graph as graph_mod          # fresh: graph_mod.fi IS fi_mod (same sys.modules entry)
    # DIAG: confirm fi identity and FAULT_MODE before running nodes
    _nfi = graph_mod.run_agent_node.__globals__.get("fi")
    print(f"  [DIAG] env={os.environ.get('FAULT_MODE')} fi.FM={fi_mod.FAULT_MODE} same={fi_mod is graph_mod.fi} node_fi_same={fi_mod is _nfi}", flush=True)

    state = dict(INITIAL_STATE)
    state["request"] = dict(TEST_PAYLOAD)

    mock_client = MagicMock()
    mock_client.send_confirmation_email.return_value = dict(MOCK_SEND_RESULT)

    start = datetime.now(timezone.utc)
    with patch("app.graph.generate_email_content", return_value=dict(MOCK_GENERATE_RESULT)):
        with patch("app.graph.EmailServiceClient", return_value=mock_client):
            # Call node functions directly (skip LangGraph routing overhead)
            state = graph_mod.run_agent_node(state)
            state = graph_mod.send_via_microservice_node(state)
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
        "state": {
            "email_type":          state.get("email_type"),
            "subject":             state.get("subject", "")[:60],
            "body_len":            len(state.get("body", "")),
            "microservice_status": state.get("microservice_status"),
        },
        "lkw": lkw,
    }


def print_report(results):
    print("\n" + "=" * 72)
    print("  EMAILSERVICEAGENT FAULT INJECTION — TEST REPORT")
    print("=" * 72)
    for r in results:
        label = "PASS" if r["fault_mode"] == "NONE" else "FAULT"
        print(f"\n  [{label}] {r['fault_mode']}")
        print(f"  Steps    : {' → '.join(r['steps_reached']) if r['steps_reached'] else 'NONE'}")
        if r["steps_lost"]:
            print(f"  Lost     : {', '.join(r['steps_lost'])}")
        print(f"  Infects  : {r['infection_point'] or 'none'}")
        print(f"  Prop.    : {r['propagation_depth']}")
        print(f"  State    : {r['state']}")
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

    out = os.path.join(os.path.dirname(__file__), "emailserviceagent_fault_results.json")
    with open(out, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"  Results saved to: {out}\n")


if __name__ == "__main__":
    main()
