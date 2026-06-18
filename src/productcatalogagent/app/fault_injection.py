"""
Fault Injection Module — MAST-aligned fault patterns for productcatalogagent
=============================================================================
Set FAULT_MODE environment variable to activate a fault.

Fault modes:

  NONE                  — Baseline (no injection)

  FM_3_1                — Premature Termination
                          Agent returns before gRPC catalog call.

  FM_2_2                — Hallucinated Product Data
                          Real gRPC result replaced with fabricated product.

  FM_2_5                — Query Ignored
                          Search query silently replaced with different string.

  FM_1_2                — Wrong Action Routing
                          list_products routed to search_products (and vice versa).

  BL_PRODUCT_MISSING    — Products Removed from Result
                          Catalog result returned as empty list.

  BL_PRICE_MANIPULATION — Prices Inflated
                          All product prices multiplied by 10.

  BL_DUPLICATE_PRODUCT  — First Product Duplicated
                          First product entry duplicated in result list.

  BL_WRONG_CATEGORY     — Categories Replaced
                          All product categories replaced with wrong values.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)

FAULT_MODE = os.getenv("FAULT_MODE", "NONE").upper()

# ── LKW Checkpoint Logger ──────────────────────────────────────────────────────

EXPECTED_STEPS = ["TASK_START", "CATALOG_DONE", "FINAL_ANSWER"]

_global_lkw: list[dict] = []


def clear_lkw():
    global _global_lkw
    _global_lkw = []


def record_checkpoint(step: str, data: dict):
    entry = {
        "step": step,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fault_mode": FAULT_MODE,
        "data": data,
    }
    _global_lkw.append(entry)
    log.info(f"[LKW] {step} | fault={FAULT_MODE} | {json.dumps(data)}")


def get_lkw() -> list[dict]:
    return list(_global_lkw)


def rip_summary() -> dict:
    reached = [cp["step"] for cp in _global_lkw]
    missing = [s for s in EXPECTED_STEPS if s not in reached]
    infection = None
    for cp in _global_lkw:
        d = cp.get("data", {})
        if any([d.get("hallucinated"), d.get("query_tampered"), d.get("action_swapped"),
                d.get("products_missing"), d.get("price_manipulated"), d.get("duplicated"),
                d.get("category_wrong"), d.get("premature_termination")]):
            if infection is None:
                infection = cp["step"]
    return {
        "reachability": reached,
        "infection_point": infection,
        "propagation_depth": len(missing),
        "missing_steps": missing,
    }


# ── Fault injection helpers ───────────────────────────────────────────────────

def maybe_premature_termination() -> Optional[list]:
    """FM_3_1: return before gRPC call."""
    if FAULT_MODE == "FM_3_1":
        log.warning("[FAULT FM_3_1] Premature termination — returning before catalog call")
        return []
    return None


def maybe_tamper_query(query: str) -> tuple[str, bool]:
    """FM_2_5: replace query with unrelated string."""
    if FAULT_MODE == "FM_2_5":
        wrong = "nonexistent_item_xyz"
        log.warning(f"[FAULT FM_2_5] Query tampered: '{query}' → '{wrong}'")
        return wrong, True
    return query, False


def maybe_swap_action(action: str) -> str:
    """FM_1_2: swap list/search actions."""
    if FAULT_MODE == "FM_1_2":
        swapped = "search_products" if action == "list_products" else "list_products"
        log.warning(f"[FAULT FM_1_2] Action swapped: {action} → {swapped}")
        return swapped
    return action


def maybe_hallucinate_products(real_data: list) -> tuple[list, bool]:
    """FM_2_2: replace real product list with fabricated data."""
    if FAULT_MODE == "FM_2_2":
        log.warning("[FAULT FM_2_2] Hallucinated product data injected")
        return [
            {
                "id": "HALLUCINATED-001",
                "name": "Fabricated Product",
                "description": "This product does not exist",
                "price_usd": {"currency_code": "USD", "units": 9999, "nanos": 0},
                "categories": ["fake"],
            }
        ], True
    return real_data, False


def maybe_remove_products(data: list) -> tuple[list, bool]:
    """BL_PRODUCT_MISSING: return empty list."""
    if FAULT_MODE == "BL_PRODUCT_MISSING":
        log.warning("[FAULT BL_PRODUCT_MISSING] All products removed from result")
        return [], True
    return data, False


def maybe_manipulate_prices(data: list) -> tuple[list, bool]:
    """BL_PRICE_MANIPULATION: inflate all prices 10x."""
    if FAULT_MODE == "BL_PRICE_MANIPULATION":
        log.warning("[FAULT BL_PRICE_MANIPULATION] Prices inflated 10x")
        result = []
        for p in data:
            p = dict(p)
            if "price_usd" in p:
                p["price_usd"] = dict(p["price_usd"])
                p["price_usd"]["units"] = p["price_usd"].get("units", 0) * 10
            result.append(p)
        return result, True
    return data, False


def maybe_duplicate_product(data: list) -> tuple[list, bool]:
    """BL_DUPLICATE_PRODUCT: duplicate first product."""
    if FAULT_MODE == "BL_DUPLICATE_PRODUCT" and data:
        log.warning("[FAULT BL_DUPLICATE_PRODUCT] First product duplicated")
        return [data[0]] + data, True
    return data, False


def maybe_wrong_category(data: list) -> tuple[list, bool]:
    """BL_WRONG_CATEGORY: replace all categories."""
    if FAULT_MODE == "BL_WRONG_CATEGORY":
        log.warning("[FAULT BL_WRONG_CATEGORY] Product categories replaced")
        result = []
        for p in data:
            p = dict(p)
            p["categories"] = ["WRONG_CATEGORY"]
            result.append(p)
        return result, True
    return data, False
