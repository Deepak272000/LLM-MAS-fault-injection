"""
Fault Injection Module — MAST-aligned fault patterns for adserviceagent
========================================================================
Set FAULT_MODE environment variable to activate a fault.

Fault modes:

  NONE               — Baseline (no injection)

  FM_3_1             — Premature Termination
                       Agent returns after input_node; ad_lookup skipped.

  FM_2_2             — Hallucinated Ads
                       Real gRPC ad data replaced with fabricated ad entries.

  FM_2_5             — Context Keys Ignored
                       Extracted context keys replaced with wrong categories.

  FM_1_2             — Wrong Category Routing
                       Context categories swapped before ad lookup.

  BL_EMPTY_ADS       — No Ads Returned
                       Ad list cleared to empty.

  BL_AD_INJECTION    — Unauthorized Ads Injected
                       Hardcoded malicious/unauthorized ads prepended.

  BL_WRONG_URL       — Ad URLs Replaced
                       All redirect URLs replaced with wrong destination.

  BL_DUPLICATE_ADS   — First Ad Duplicated
                       First ad entry duplicated in result list.
"""

import os
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

FAULT_MODE = os.getenv("FAULT_MODE", "NONE").upper()

# ── Module-level LKW log (shared across graph nodes) ─────────────────────────

EXPECTED_STEPS = ["TASK_START", "CONTEXT_EXTRACTED", "ADS_FETCHED", "FINAL_ANSWER"]

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
    boundary_alert_steps = []
    for cp in _global_lkw:
        d = cp.get("data", {})
        if cp["step"] == "BOUNDARY_CHECK" and d.get("alert"):
            boundary_alert_steps.append(d.get("boundary", "BOUNDARY_CHECK"))
        if any([d.get("hallucinated"), d.get("context_tampered"), d.get("category_swapped"),
                d.get("empty_ads"), d.get("injected"), d.get("wrong_url"),
                d.get("duplicated"), d.get("premature_termination")]):
            if infection is None:
                infection = cp["step"]
    return {
        "reachability": reached,
        "infection_point": infection,
        "boundary_alert_steps": boundary_alert_steps,
        "boundary_alert_point": boundary_alert_steps[0] if boundary_alert_steps else None,
        "propagation_depth": len(missing),
        "missing_steps": missing,
    }


# ── Fault injection helpers ───────────────────────────────────────────────────

def maybe_premature_termination() -> bool:
    """FM_3_1: skip ad lookup step."""
    if FAULT_MODE == "FM_3_1":
        log.warning("[FAULT FM_3_1] Premature termination — ad lookup will be skipped")
        return True
    return False


def maybe_tamper_context(context_keys: list) -> tuple[list, bool]:
    """FM_2_5: replace context keys with wrong categories."""
    if FAULT_MODE == "FM_2_5":
        wrong = ["nonexistent_category_xyz"]
        log.warning(f"[FAULT FM_2_5] Context keys tampered: {context_keys} → {wrong}")
        return wrong, True
    return context_keys, False


def maybe_swap_category(context_keys: list) -> tuple[list, bool]:
    """FM_1_2: swap to different category set."""
    if FAULT_MODE == "FM_1_2":
        swapped = ["electronics"] if "clothing" in context_keys else ["clothing"]
        log.warning(f"[FAULT FM_1_2] Category swapped: {context_keys} → {swapped}")
        return swapped, True
    return context_keys, False


def maybe_hallucinate_ads(ads: list) -> tuple[list, bool]:
    """FM_2_2: replace real ads with fabricated entries."""
    if FAULT_MODE == "FM_2_2":
        log.warning("[FAULT FM_2_2] Hallucinated ad data injected")
        return [
            {"redirect_url": "https://fake.ad.example.com/scam", "text": "FAKE_AD: Win a free prize!"},
            {"redirect_url": "https://hallucinated.example.com/offer", "text": "FAKE_AD: Unbeatable offer!"},
        ], True
    return ads, False


def maybe_empty_ads(ads: list) -> tuple[list, bool]:
    """BL_EMPTY_ADS: return empty list."""
    if FAULT_MODE == "BL_EMPTY_ADS":
        log.warning("[FAULT BL_EMPTY_ADS] Ad list cleared to empty")
        return [], True
    return ads, False


def maybe_inject_ads(ads: list) -> tuple[list, bool]:
    """BL_AD_INJECTION: prepend unauthorized ads."""
    if FAULT_MODE == "BL_AD_INJECTION":
        unauthorized = [{"redirect_url": "https://unauthorized.example.com/ad",
                         "text": "INJECTED: Unauthorized advertisement"}]
        log.warning("[FAULT BL_AD_INJECTION] Unauthorized ads injected")
        return unauthorized + ads, True
    return ads, False


def maybe_wrong_url(ads: list) -> tuple[list, bool]:
    """BL_WRONG_URL: replace all redirect URLs."""
    if FAULT_MODE == "BL_WRONG_URL":
        log.warning("[FAULT BL_WRONG_URL] All ad redirect URLs replaced")
        result = [dict(ad) for ad in ads]
        for ad in result:
            ad["redirect_url"] = "https://wrong.url.example.com"
        return result, True
    return ads, False


def maybe_duplicate_ad(ads: list) -> tuple[list, bool]:
    """BL_DUPLICATE_ADS: duplicate first ad."""
    if FAULT_MODE == "BL_DUPLICATE_ADS" and ads:
        log.warning("[FAULT BL_DUPLICATE_ADS] First ad duplicated")
        return [ads[0]] + ads, True
    return ads, False
