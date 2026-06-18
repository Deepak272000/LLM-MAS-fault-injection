"""
ProductCatalogAgent Fault Injection Test Runner
================================================
Tests all FAULT_MODE values by calling ProductCatalogAgent.run() directly,
mocking ProductCatalogGrpcClient so no gRPC server is needed.

Usage:
    python test_fault_injection.py
    python test_fault_injection.py FM_2_2 BL_PRICE_MANIPULATION
"""

import json
import os
import sys
import importlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Stub gRPC and proto stubs at module load time
sys.modules.setdefault("grpc", MagicMock())
_mock_clients = MagicMock()
sys.modules.setdefault("app.clients", _mock_clients)
sys.modules.setdefault("app.clients.demo_pb2", MagicMock())
sys.modules.setdefault("app.clients.demo_pb2_grpc", MagicMock())

MOCK_PRODUCT = {
    "id": "PROD-001",
    "name": "Sunglasses",
    "description": "Stylish sunglasses",
    "picture": "/static/img/products/sunglasses.jpg",
    "categories": ["accessories"],
    "price_usd": {"currency_code": "USD", "units": 19, "nanos": 990000000},
}
MOCK_PRODUCT_2 = {
    "id": "PROD-002",
    "name": "Candle Holder",
    "description": "Elegant candle holder",
    "picture": "",
    "categories": ["home"],
    "price_usd": {"currency_code": "USD", "units": 12, "nanos": 500000000},
}

MOCK_PRODUCTS = [MOCK_PRODUCT, MOCK_PRODUCT_2]

ALL_MODES = [
    "NONE", "FM_3_1", "FM_2_2", "FM_2_5", "FM_1_2",
    "BL_PRODUCT_MISSING", "BL_PRICE_MANIPULATION",
    "BL_DUPLICATE_PRODUCT", "BL_WRONG_CATEGORY",
]

EXPECTED_STEPS = ["TASK_START", "CATALOG_DONE", "FINAL_ANSWER"]


def run_one(fault_mode: str) -> dict:
    os.environ["FAULT_MODE"] = fault_mode

    import app.fault_injection as fi_mod
    importlib.reload(fi_mod)
    import app.agent as agent_mod
    importlib.reload(agent_mod)

    mock_client = MagicMock()
    mock_client.list_products.return_value = [dict(p) for p in MOCK_PRODUCTS]
    mock_client.get_product.return_value = dict(MOCK_PRODUCT)
    mock_client.search_products.return_value = [dict(MOCK_PRODUCT)]

    agent_mod.client = mock_client
    agent = agent_mod.ProductCatalogAgent()

    start = datetime.now(timezone.utc)
    result = agent.run(query="list all products")
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
        "count": len(result.get("data", [])),
        "action": result.get("action"),
        "data_preview": result.get("data", [{}])[0] if result.get("data") else None,
        "lkw": lkw,
    }


def print_report(results):
    print("\n" + "=" * 72)
    print("  PRODUCTCATALOGAGENT FAULT INJECTION — TEST REPORT")
    print("=" * 72)
    for r in results:
        label = "PASS" if r["fault_mode"] == "NONE" else "FAULT"
        print(f"\n  [{label}] {r['fault_mode']}")
        print(f"  Steps   : {' → '.join(r['steps_reached']) if r['steps_reached'] else 'NONE'}")
        if r["steps_lost"]:
            print(f"  Lost    : {', '.join(r['steps_lost'])}")
        print(f"  Infects : {r['infection_point'] or 'none'}")
        print(f"  Prop.   : {r['propagation_depth']}")
        print(f"  Action  : {r['action']} | Count: {r['count']}")
        if r.get("data_preview"):
            print(f"  Preview : {r['data_preview']}")
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

    out = os.path.join(os.path.dirname(__file__), "productcatalogagent_fault_results.json")
    with open(out, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"  Results saved to: {out}\n")


if __name__ == "__main__":
    main()
