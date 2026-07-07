"""
Fault Injection Module — MAST-aligned fault patterns for emailserviceagent
===========================================================================
Set FAULT_MODE environment variable to activate a fault.

Fault modes:

  NONE               — Baseline (no injection)

  FM_3_1             — Premature Termination
                       Agent returns before email content is generated.

  FM_2_2             — Hallucinated Email Content
                       Subject and body replaced with fabricated content.

  FM_2_5             — Recipient Address Ignored
                       Email recipient silently swapped to wrong address.

  FM_1_2             — Wrong Email Type Classification
                       Email classified as wrong type before generation.

  BL_SEND_SKIPPED    — Send Step Bypassed
                       Email content generated but gRPC send call skipped.

  BL_DOUBLE_SEND     — Duplicate Send Flagged
                       Send marked for duplicate delivery.

  BL_CORRUPTED_BODY  — Email Body Corrupted
                       Body content truncated to 20 characters.

  BL_WRONG_CUSTOMER  — Wrong Customer Injected
                       Customer name replaced with wrong value in body.
"""

import os
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

FAULT_MODE = os.getenv("FAULT_MODE", "NONE").upper()

# ── Module-level LKW log (shared across graph nodes) ─────────────────────────

EXPECTED_STEPS = ["TASK_START", "EMAIL_GENERATED", "EMAIL_SENT", "FINAL_ANSWER"]

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
        if any([d.get("hallucinated"), d.get("recipient_swapped"), d.get("type_wrong"),
                d.get("send_skipped"), d.get("double_send"), d.get("corrupted"),
                d.get("wrong_customer"), d.get("premature_termination")]):
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
    """FM_3_1: skip all processing."""
    if FAULT_MODE == "FM_3_1":
        log.warning("[FAULT FM_3_1] Premature termination — email will not be generated")
        return True
    return False


def maybe_wrong_email_type(email_type: str) -> str:
    """FM_1_2: return wrong classification."""
    if FAULT_MODE == "FM_1_2":
        wrong = "promotional" if email_type != "promotional" else "cancellation"
        log.warning(f"[FAULT FM_1_2] Email type swapped: {email_type} → {wrong}")
        return wrong
    return email_type


def maybe_swap_recipient(email: str) -> str:
    """FM_2_5: replace recipient address."""
    if FAULT_MODE == "FM_2_5":
        wrong = "wrong.address@devnull.test"
        log.warning(f"[FAULT FM_2_5] Recipient swapped: {email} → {wrong}")
        return wrong
    return email


def maybe_hallucinate_email(result: dict) -> dict:
    """FM_2_2: replace generated email content with fabricated data."""
    if FAULT_MODE == "FM_2_2":
        log.warning("[FAULT FM_2_2] Hallucinated email content injected")
        return {
            "email_type": result.get("email_type", "order_confirmation"),
            "subject": "CONGRATULATIONS! You've won a prize",
            "body": "Click here to claim your reward. (hallucinated content)",
            "llm_used": False,
            "total_tokens": 0,
            "hallucinated": True,
        }
    return result


def maybe_corrupt_body(body: str) -> str:
    """BL_CORRUPTED_BODY: truncate email body."""
    if FAULT_MODE == "BL_CORRUPTED_BODY":
        truncated = body[:20]
        log.warning(f"[FAULT BL_CORRUPTED_BODY] Body truncated: {len(body)} chars → 20")
        return truncated
    return body


def maybe_wrong_customer(body: str) -> tuple[str, bool]:
    """BL_WRONG_CUSTOMER: replace customer name in body."""
    if FAULT_MODE == "BL_WRONG_CUSTOMER":
        patched = body.replace("Customer", "WRONG_CUSTOMER").replace("Hello ", "Hello WRONG_")
        log.warning("[FAULT BL_WRONG_CUSTOMER] Customer name replaced in email body")
        return patched, True
    return body, False


def maybe_skip_send() -> bool:
    """BL_SEND_SKIPPED: bypass gRPC send call."""
    if FAULT_MODE == "BL_SEND_SKIPPED":
        log.warning("[FAULT BL_SEND_SKIPPED] Email send bypassed — gRPC not called")
        return True
    return False


def maybe_double_send_marker() -> bool:
    """BL_DOUBLE_SEND: flag for duplicate email send."""
    if FAULT_MODE == "BL_DOUBLE_SEND":
        log.warning("[FAULT BL_DOUBLE_SEND] Duplicate send marker injected")
        return True
    return False
