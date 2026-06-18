"""
Fault Injection Module — MAST-aligned fault patterns for recommendationagent
=============================================================================
Set FAULT_MODE environment variable to activate a fault.

Fault modes:

  NONE                  — Baseline (no injection)

  FM_3_1                — Premature Termination
                          Agent returns before gRPC recommendation call.

  FM_2_2                — Hallucinated Recommendation IDs
                          Real gRPC result replaced with fabricated product IDs.

  FM_2_5                — User ID Ignored
                          user_id silently replaced before gRPC call.

  FM_1_2                — Wrong Method Routed
                          get_recommendations routed to explain_recommendations
                          (and vice versa).

  BL_EMPTY_RECS         — Empty Recommendations Returned
                          Recommendation list cleared to empty.

  BL_SELF_RECOMMENDATION — Input Products Echoed as Recommendations
                           Recommended IDs set to the same as input product IDs.

  BL_INJECTION_RECS     — Sponsored IDs Injected
                          Hardcoded sponsored IDs prepended to result.

  BL_SHUFFLED_RECS      — Recommendations Reversed
                          Result list returned in reversed order.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)

FAULT_MODE = os.getenv("FAULT_MODE", "NONE").upper()

# ── Module-level LKW log ──────────────────────────────────────────────────────

EXPECTED_STEPS = ["TASK_START", "RECOMMEND_DONE", "FINAL_ANSWER"]

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
        if any([d.get("hallucinated"), d.get("user_id_swapped"), d.get("method_swapped"),
                d.get("empty_recs"), d.get("self_rec"), d.get("injection"),
                d.get("shuffled"), d.get("premature_termination")]):
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
    """FM_3_1: skip gRPC call."""
    if FAULT_MODE == "FM_3_1":
        log.warning("[FAULT FM_3_1] Premature termination — recommendation call skipped")
        return []
    return None


def maybe_swap_user_id(user_id: str) -> tuple[str, bool]:
    """FM_2_5: replace user_id."""
    if FAULT_MODE == "FM_2_5":
        wrong = "WRONG_USER_000"
        log.warning(f"[FAULT FM_2_5] user_id swapped: '{user_id}' → '{wrong}'")
        return wrong, True
    return user_id, False


def maybe_hallucinate_recs(real_ids: list) -> tuple[list, bool]:
    """FM_2_2: replace real IDs with fabricated ones."""
    if FAULT_MODE == "FM_2_2":
        log.warning("[FAULT FM_2_2] Hallucinated recommendation IDs injected")
        return ["HALLUCINATED-001", "HALLUCINATED-002", "HALLUCINATED-003"], True
    return real_ids, False


def maybe_empty_recs(ids: list) -> tuple[list, bool]:
    """BL_EMPTY_RECS: return empty list."""
    if FAULT_MODE == "BL_EMPTY_RECS":
        log.warning("[FAULT BL_EMPTY_RECS] Recommendations cleared to empty list")
        return [], True
    return ids, False


def maybe_self_recommendation(ids: list, input_product_ids: list) -> tuple[list, bool]:
    """BL_SELF_RECOMMENDATION: echo input IDs as recommendations."""
    if FAULT_MODE == "BL_SELF_RECOMMENDATION":
        log.warning("[FAULT BL_SELF_RECOMMENDATION] Input product IDs echoed as recommendations")
        return list(input_product_ids), True
    return ids, False


def maybe_inject_sponsored(ids: list) -> tuple[list, bool]:
    """BL_INJECTION_RECS: prepend hardcoded sponsored IDs."""
    if FAULT_MODE == "BL_INJECTION_RECS":
        sponsored = ["SPONSORED-001", "SPONSORED-002"]
        log.warning(f"[FAULT BL_INJECTION_RECS] Sponsored IDs injected: {sponsored}")
        return sponsored + ids, True
    return ids, False


def maybe_shuffle_recs(ids: list) -> tuple[list, bool]:
    """BL_SHUFFLED_RECS: reverse recommendation order."""
    if FAULT_MODE == "BL_SHUFFLED_RECS" and len(ids) > 1:
        log.warning("[FAULT BL_SHUFFLED_RECS] Recommendations reversed")
        return list(reversed(ids)), True
    return ids, False
