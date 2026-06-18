"""
Cross-Agent Fault Propagation Study
=====================================
Demonstrates multi-hop fault propagation across agent boundaries.

Chain A — Financial Impact:
  CurrencyAgent (FM_2_2: hallucinated rate)
    -> PaymentAgent (NONE: baseline-correct, but receives inflated price)
    -> Outcome: correct agent charges WRONG amount due to upstream fault

Chain B — Catalog Corruption Cascade:
  ProductCatalogAgent (FM_2_2: hallucinated product)
    -> RecommendationAgent (NONE: baseline-correct, but uses phantom product_id)
    -> Outcome: recommendations generated for a non-existent product

KEY FINDING:
  Even a fault-free downstream agent cannot recover from upstream FM-2.2.
  FM-2.2 (hallucination) is the highest-risk cross-boundary fault type:
  it propagates silently with zero structural step loss.

Usage:
    python cross_agent_propagation.py
"""

import asyncio
import importlib
import json
import os
import sys
from contextlib import contextmanager
from typing import Optional
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

SRC = Path(__file__).parent

# ── Shared stubs (loaded once) ────────────────────────────────────────────────
sys.modules.setdefault("grpc", MagicMock())
sys.modules.setdefault("motor", MagicMock())
sys.modules.setdefault("motor.motor_asyncio", MagicMock())
sys.modules.setdefault("pymongo", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

_mock_lggraph = MagicMock()
_mock_lggraph.END = "__end__"
_mock_lggraph.StateGraph = MagicMock()
sys.modules.setdefault("langgraph", MagicMock())
sys.modules["langgraph.graph"] = _mock_lggraph


@contextmanager
def agent_context(agent_dir: Path, fault_mode: str, extra_stubs: Optional[dict] = None):
    """
    Temporarily configure sys.path and sys.modules for a single agent.
    Clears all app.* modules before and after to prevent cross-agent conflicts.
    """
    os.environ["FAULT_MODE"] = fault_mode
    for key in list(sys.modules):
        if key.startswith("app"):
            del sys.modules[key]
    if extra_stubs:
        sys.modules.update(extra_stubs)
    sys.path.insert(0, str(agent_dir))
    try:
        yield
    finally:
        sys.path.remove(str(agent_dir))
        for key in list(sys.modules):
            if key.startswith("app"):
                del sys.modules[key]
        os.environ["FAULT_MODE"] = "NONE"


# ── Constants ─────────────────────────────────────────────────────────────────

CLEAN_CURRENCY_RESULT = {"currency_code": "EUR", "units": 9, "nanos": 230000000}

MOCK_CARD = {
    "credit_card_number":           "4111111111111111",
    "credit_card_cvv":              123,
    "credit_card_expiration_year":  2027,
    "credit_card_expiration_month": 9,
}

PROTO_STUBS = {
    "app.clients":               MagicMock(),
    "app.clients.demo_pb2":      MagicMock(),
    "app.clients.demo_pb2_grpc": MagicMock(),
}

MOCK_PRODUCTS_CLEAN = [
    {"id": "PROD-001", "name": "Sunglasses", "categories": ["accessories"],
     "price_usd": {"currency_code": "USD", "units": 19, "nanos": 990000000}},
]
MOCK_RECS = ["PROD-042", "PROD-017", "PROD-009"]

_INFECTION_FLAGS = [
    "hallucinated", "amount_tampered", "currency_swapped", "rate_manipulated",
    "stale_rate", "overflow", "premature_termination", "unavailable",
    "products_missing", "price_manipulated", "duplicated", "category_wrong",
    "query_tampered", "action_swapped", "user_id_swapped", "empty_recs",
    "self_rec", "injection", "shuffled", "context_tampered", "empty_ads",
    "injected", "wrong_url", "save_skipped", "double_charge",
]


def _rip_from_lkw(lkw: list, expected_steps: list) -> dict:
    """Compute RIP summary from a list of LKW checkpoint dicts."""
    reached = [cp["step"] for cp in lkw]
    missing = [s for s in expected_steps if s not in reached]
    infection = None
    for cp in lkw:
        if any(cp.get("data", {}).get(f) for f in _INFECTION_FLAGS):
            if infection is None:
                infection = cp["step"]
    return {"reachability": reached, "infection_point": infection,
            "propagation_depth": len(missing), "missing_steps": missing}


# ── Agent runner functions ────────────────────────────────────────────────────

def run_currency_agent(fault_mode: str) -> dict:
    """Run CurrencyAgent — LKW is embedded in result dict (class-based LKW)."""
    agent_dir = SRC / "currencyagent"
    captured = {}
    with agent_context(agent_dir, fault_mode, PROTO_STUBS):
        import app.fault_injection as fi
        import app.agent as agent_mod
        importlib.reload(fi)
        fi.FAULT_MODE = fault_mode  # force-set in case env-var timing differs on Python 3.9
        importlib.reload(agent_mod)
        fi.FAULT_MODE = fault_mode  # re-apply after agent reload
        mock_client = MagicMock()
        mock_client.convert.return_value = dict(CLEAN_CURRENCY_RESULT)
        agent_mod.client = mock_client
        result = agent_mod.CurrencyAgent().run(
            query="convert 10 USD to EUR", action="convert",
            from_currency="USD", units=10, nanos=0, to_currency="EUR",
        )
        captured["result"] = result
        captured["lkw"] = result.get("lkw", [])
    rip = _rip_from_lkw(captured["lkw"], ["TASK_START", "CONVERT_DONE", "FINAL_ANSWER"])
    return {"result": captured["result"], "lkw": captured["lkw"], "rip": rip}


async def run_payment_agent(units: int, currency_code: str, fault_mode: str = "NONE") -> dict:
    """Run PaymentAgent — LKW is embedded in result dict (class-based LKW)."""
    agent_dir = SRC / "paymentagent"
    mock_repo = MagicMock()
    mock_repo.save_transaction = AsyncMock(return_value="TXN-CROSS-AGENT")
    captured = {}
    with agent_context(agent_dir, fault_mode, {"app.repository": mock_repo}):
        import app.fault_injection as fi
        import app.tools as tools_mod
        import app.agent as agent_mod
        importlib.reload(fi)
        fi.FAULT_MODE = fault_mode
        importlib.reload(tools_mod)
        importlib.reload(agent_mod)
        fi.FAULT_MODE = fault_mode
        try:
            result = await agent_mod.PaymentAgent().run(
                query="charge payment",
                currency_code=currency_code, units=units, nanos=0, **MOCK_CARD,
            )
        except Exception as _exc:
            print(f"  [WARN] PaymentAgent.run() raised {type(_exc).__name__}: {_exc}")
            result = {"mode": "error", "action": "charge", "data": {}, "lkw": []}
        captured["result"] = result
        captured["lkw"] = result.get("lkw", [])
    rip = _rip_from_lkw(captured["lkw"],
                         ["TASK_START", "CARD_VALIDATED", "CHARGE_DONE", "SAVE_DONE", "FINAL_ANSWER"])
    return {"result": captured["result"], "lkw": captured["lkw"], "rip": rip}


def run_catalog_agent(fault_mode: str) -> dict:
    """Run ProductCatalogAgent — module-level get_lkw() called inside context."""
    agent_dir = SRC / "productcatalogagent"
    captured = {}
    with agent_context(agent_dir, fault_mode, PROTO_STUBS):
        import app.fault_injection as fi
        import app.agent as agent_mod
        importlib.reload(fi)
        fi.FAULT_MODE = fault_mode
        importlib.reload(agent_mod)
        fi.FAULT_MODE = fault_mode
        mock_client = MagicMock()
        mock_client.list_products.return_value = [dict(p) for p in MOCK_PRODUCTS_CLEAN]
        mock_client.search_products.return_value = [dict(p) for p in MOCK_PRODUCTS_CLEAN]
        agent_mod.client = mock_client
        result = agent_mod.ProductCatalogAgent().run(query="list all products")
        captured["result"] = result
        captured["lkw"] = fi.get_lkw()
        captured["rip"] = fi.rip_summary()
    return captured


def run_recommendation_agent(product_ids: list, fault_mode: str = "NONE") -> dict:
    """Run RecommendationAgent — module-level get_lkw() called inside context."""
    agent_dir = SRC / "recommendationagent"
    captured = {}
    with agent_context(agent_dir, fault_mode, PROTO_STUBS):
        import app.fault_injection as fi
        import app.agent as agent_mod
        importlib.reload(fi)
        fi.FAULT_MODE = fault_mode
        importlib.reload(agent_mod)
        fi.FAULT_MODE = fault_mode
        mock_client = MagicMock()
        mock_client.list_recommendations.return_value = list(MOCK_RECS)
        agent_mod.client = mock_client
        result = agent_mod.RecommendationAgent().get_recommendations(
            user_id="user-test", product_ids=product_ids)
        captured["result"] = result
        captured["lkw"] = fi.get_lkw()
        captured["rip"] = fi.rip_summary()
    return captured


# ── Chain A ───────────────────────────────────────────────────────────────────

async def run_chain_a():
    print("\n" + "=" * 70)
    print("  CHAIN A — CurrencyAgent FM_2_2  ->  PaymentAgent NONE")
    print("  Financial Impact: Hallucinated exchange rate causes wrong charge")
    print("=" * 70)

    print("\n  [HOP 1] CurrencyAgent | FAULT_MODE=NONE")
    c_clean = run_currency_agent("NONE")
    clean_units = c_clean["result"]["data"]["units"]
    print(f"  --> Converted amount : {clean_units} EUR  (expected)")
    print(f"  --> Infection point  : {c_clean['rip']['infection_point']}")

    print(f"\n  [HOP 2] PaymentAgent  | FAULT_MODE=NONE | charge_units={clean_units}")
    p_clean = await run_payment_agent(units=clean_units, currency_code="EUR")
    print(f"  --> Steps reached    : {[cp['step'] for cp in p_clean['lkw']]}")
    print(f"  --> Infection point  : {p_clean['rip']['infection_point']}")
    print(f"  --> Result           : CORRECT baseline")

    print(f"\n  {'--'*35}")
    print(f"\n  [HOP 1] CurrencyAgent | FAULT_MODE=FM_2_2  <<< FAULT INJECTED")
    c_infected = run_currency_agent("FM_2_2")
    infected_units = c_infected["result"]["data"]["units"]
    print(f"  --> Converted amount : {infected_units} EUR  (HALLUCINATED, was {clean_units})")
    print(f"  --> Infection point  : {c_infected['rip']['infection_point']}")
    print(f"  --> Hallucinated     : {c_infected['result']['data'].get('hallucinated')}")

    print(f"\n  [HOP 2] PaymentAgent  | FAULT_MODE=NONE | charge_units={infected_units}  <<< PROPAGATED")
    p_infected = await run_payment_agent(units=infected_units, currency_code="EUR")
    print(f"  --> Steps reached    : {[cp['step'] for cp in p_infected['lkw']]}")
    print(f"  --> Infection point  : {p_infected['rip']['infection_point']}  (None = agent is correct)")
    print(f"  --> Amount charged   : {infected_units} EUR  (WRONG -- should be {clean_units})")

    overcharge = infected_units - clean_units
    overcharge_pct = round(overcharge / clean_units * 100, 1) if clean_units else 0
    print(f"\n  PROPAGATION RESULT:")
    print(f"    Expected charge   : {clean_units} EUR")
    print(f"    Actual charge     : {infected_units} EUR")
    print(f"    Overcharge        : +{overcharge} EUR  (+{overcharge_pct}%)")
    print(f"    PaymentAgent acts : correctly (no fault of its own)")
    print(f"    HITL tier         : Tier 3 -- financial loss, zero structural alert")

    return {
        "chain": "A",
        "description": "CurrencyAgent FM_2_2 -> PaymentAgent NONE",
        "hop1_fault": "FM_2_2", "hop2_fault": "NONE",
        "baseline_units": clean_units, "propagated_units": infected_units,
        "overcharge_eur": overcharge, "overcharge_pct": overcharge_pct,
        "hop1_infection": c_infected["rip"]["infection_point"],
        "hop2_infection": p_infected["rip"]["infection_point"],
        "hop2_steps": [cp["step"] for cp in p_infected["lkw"]],
        "finding": ("FM-2.2 hallucination propagates silently across agent boundary; "
                    "PaymentAgent is fault-free but charges inflated amount"),
    }


# ── Chain B ───────────────────────────────────────────────────────────────────

def run_chain_b():
    print("\n" + "=" * 70)
    print("  CHAIN B — ProductCatalogAgent FM_2_2  ->  RecommendationAgent NONE")
    print("  Catalog Corruption: Phantom product ID forwarded to recommender")
    print("=" * 70)

    print("\n  [HOP 1] ProductCatalogAgent | FAULT_MODE=NONE")
    cat_clean = run_catalog_agent("NONE")
    clean_ids = [p["id"] for p in cat_clean["result"]["data"]]
    print(f"  --> Products returned: {clean_ids}")
    print(f"  --> Infection point  : {cat_clean['rip']['infection_point']}")

    print(f"\n  [HOP 2] RecommendationAgent | FAULT_MODE=NONE | input={clean_ids}")
    rec_clean = run_recommendation_agent(product_ids=clean_ids)
    print(f"  --> Recommendations  : {rec_clean['result']['recommended_product_ids']}")
    print(f"  --> Infection point  : {rec_clean['rip']['infection_point']}")
    print(f"  --> Result           : CORRECT -- valid product IDs used")

    print(f"\n  {'--'*35}")
    print(f"\n  [HOP 1] ProductCatalogAgent | FAULT_MODE=FM_2_2  <<< FAULT INJECTED")
    cat_infected = run_catalog_agent("FM_2_2")
    infected_ids = [p["id"] for p in cat_infected["result"]["data"]]
    print(f"  --> Products returned: {infected_ids}  (HALLUCINATED)")
    print(f"  --> Infection point  : {cat_infected['rip']['infection_point']}")

    print(f"\n  [HOP 2] RecommendationAgent | FAULT_MODE=NONE | input={infected_ids}  <<< PROPAGATED")
    rec_infected = run_recommendation_agent(product_ids=infected_ids)
    infected_recs = rec_infected["result"]["recommended_product_ids"]
    print(f"  --> Input used       : {infected_ids}  (HALLUCINATED-001 does not exist)")
    print(f"  --> Recommendations  : {infected_recs}")
    print(f"  --> Infection point  : {rec_infected['rip']['infection_point']}  (None = agent correct)")
    print(f"  --> Steps reached    : {[cp['step'] for cp in rec_infected['lkw']]}")

    print(f"\n  PROPAGATION RESULT:")
    print(f"    Input used           : HALLUCINATED-001 (phantom catalog entry)")
    print(f"    Recommendations for  : non-existent product")
    print(f"    RecommendationAgent  : executes correctly on bad input")
    print(f"    No structural loss   : all 3 checkpoints reached at hop 2")
    print(f"    HITL tier            : Tier 2 -- detectable via product ID cross-check")

    return {
        "chain": "B",
        "description": "ProductCatalogAgent FM_2_2 -> RecommendationAgent NONE",
        "hop1_fault": "FM_2_2", "hop2_fault": "NONE",
        "baseline_product_ids": clean_ids,
        "propagated_product_ids": infected_ids,
        "baseline_recs": rec_clean["result"]["recommended_product_ids"],
        "propagated_recs": infected_recs,
        "hop1_infection": cat_infected["rip"]["infection_point"],
        "hop2_infection": rec_infected["rip"]["infection_point"],
        "hop2_steps": [cp["step"] for cp in rec_infected["lkw"]],
        "finding": ("FM-2.2 phantom product ID propagates silently to recommender; "
                    "no structural step loss at hop 2; garbage-in garbage-out"),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 70)
    print("  LLM-MAS CROSS-AGENT FAULT PROPAGATION STUDY")
    print("  Multi-hop fault propagation across agent boundaries")
    print("=" * 70)

    result_a = await run_chain_a()
    result_b = run_chain_b()

    print("\n" + "=" * 70)
    print("  CROSS-AGENT PROPAGATION SUMMARY")
    print("=" * 70)
    print(f"  Chain A  Currency FM-2.2 -> Payment NONE")
    print(f"           Overcharge: +{result_a['overcharge_eur']} EUR (+{result_a['overcharge_pct']}%)")
    print(f"           Hop-2 infection: {result_a['hop2_infection']}  (downstream agent correct)")
    print(f"           HITL Tier: 3 (financial loss, silent)")
    print()
    print(f"  Chain B  ProductCatalog FM-2.2 -> Recommendation NONE")
    print(f"           Phantom ID: {result_b['propagated_product_ids']}")
    print(f"           Hop-2 infection: {result_b['hop2_infection']}  (downstream agent correct)")
    print(f"           HITL Tier: 2 (semantic corruption, detectable)")
    print()
    print("  KEY FINDING: FM-2.2 (hallucination) is the highest-risk cross-boundary")
    print("  fault -- zero structural loss at downstream; undetectable without explicit")
    print("  inter-agent data contracts or output validation gates.")
    print("=" * 70)

    out = SRC / "results" / "cross_agent_propagation.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "chains": [result_a, result_b],
        }, f, indent=2)
    print(f"\n  Results saved: {out}\n")


if __name__ == "__main__":
    asyncio.run(main())
