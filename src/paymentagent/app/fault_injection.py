"""
Fault Injection Module — MAST-aligned fault patterns for paymentagent
======================================================================
Set the FAULT_MODE environment variable before running to activate a fault.

Fault modes:

  NONE               — Baseline (no injection)

  FM_3_1             — Category 3 (Verification): Premature Termination
                       Agent returns a result before the charge is executed,
                       leaving the transaction unprocessed and unsaved.

  FM_2_2             — Category 2 (Execution): Hallucinated Transaction ID
                       charge_payment returns a fabricated transaction ID
                       instead of the real result; agent accepts it blindly.

  FM_2_5             — Category 2 (Execution): Ignored Amount Input
                       The amount passed to charge_payment is silently replaced
                       with a stale/wrong value before the charge executes.

  FM_1_2             — Category 1 (Planning): Validation Bypassed
                       Card validation is skipped entirely; any card (including
                       invalid/expired) is accepted and charged.

  BL_TRANSACTION_LOST   — Business Logic: Transaction Lost
                          charge executes and returns a transaction_id but the
                          MongoDB save is silently bypassed — no record persisted.

  BL_DOUBLE_CHARGE      — Business Logic: Double Charge
                          The card is flagged as charged twice; a duplicate
                          transaction marker is injected into the save payload.

  BL_AMOUNT_TAMPERING   — Business Logic: Amount Tampered
                          The charge amount is inflated before processing,
                          simulating a pricing or currency conversion error.

  BL_CARD_DECLINED      — Business Logic: Forced Decline
                          A valid card is forced to decline regardless of
                          card type or expiry, simulating a PSP rejection.
"""

import os
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)

FAULT_MODE = os.getenv("FAULT_MODE", "NONE").upper()

# ── LKW (Last Known Well) Checkpoint Logger ────────────────────────────────────

class LKWCheckpoint:
    """
    Records the state at each well-defined step of the payment workflow.
    Used by the RIP (Reachability → Infection → Propagation) harness to
    detect where quality deviation first occurs and how far it spreads.

    Checkpoints:
      TASK_START      — inputs received, fault mode recorded
      CARD_VALIDATED  — card passed (or bypassed) validation
      CHARGE_DONE     — charge_payment returned a transaction_id
      SAVE_DONE       — transaction persisted to MongoDB
      FINAL_ANSWER    — result returned to caller
    """

    EXPECTED_STEPS = [
        "TASK_START",
        "CARD_VALIDATED",
        "CHARGE_DONE",
        "SAVE_DONE",
        "FINAL_ANSWER",
    ]

    def __init__(self):
        self.checkpoints: list[dict] = []

    def record(self, step: str, data: dict):
        entry = {
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fault_mode": FAULT_MODE,
            "data": data,
        }
        self.checkpoints.append(entry)
        log.info(f"[LKW] {step} | fault={FAULT_MODE} | {json.dumps(data)}")

    def rip_summary(self) -> dict:
        reached = [cp["step"] for cp in self.checkpoints]
        missing = [s for s in self.EXPECTED_STEPS if s not in reached]
        infection = None
        for cp in self.checkpoints:
            data = cp.get("data", {})
            if (
                data.get("hallucinated")
                or data.get("amount_tampered")
                or data.get("validation_bypassed")
                or data.get("save_skipped")
                or data.get("double_charge")
                or data.get("forced_decline")
                or data.get("premature_termination")
                or "FAKE" in str(data.get("transaction_id", ""))
            ):
                if infection is None:
                    infection = cp["step"]
        return {
            "reachability": reached,
            "infection_point": infection,
            "propagation_depth": len(missing),
            "missing_steps": missing,
        }


# ── Fault injection helpers ────────────────────────────────────────────────────

def maybe_premature_termination() -> Optional[dict]:
    """FM_3_1: return a fake result before any charge executes."""
    if FAULT_MODE == "FM_3_1":
        log.warning("[FAULT FM_3_1] Premature termination — returning before charge")
        return {
            "success": False,
            "transaction_id": "PREMATURE-0000",
            "premature_termination": True,
        }
    return None


def maybe_bypass_validation(card_number: str) -> bool:
    """FM_1_2: return True to skip card validation entirely."""
    if FAULT_MODE == "FM_1_2":
        log.warning(f"[FAULT FM_1_2] Validation bypassed for card ending {card_number[-4:]}")
        return True
    return False


def maybe_tamper_amount(units: int, nanos: int) -> tuple[int, int]:
    """FM_2_5 / BL_AMOUNT_TAMPERING: replace amount with a different value."""
    if FAULT_MODE in ("FM_2_5", "BL_AMOUNT_TAMPERING"):
        tampered_units = units * 3 if units > 0 else 999
        log.warning(
            f"[FAULT {FAULT_MODE}] Amount tampered: {units}.{nanos:09d} → "
            f"{tampered_units}.{nanos:09d}"
        )
        return tampered_units, nanos
    return units, nanos


def maybe_hallucinate_transaction(real_result: dict) -> dict:
    """FM_2_2: replace the real transaction_id with a fabricated one."""
    if FAULT_MODE == "FM_2_2":
        fake_id = f"FAKE-TXN-{uuid.uuid4().hex[:8].upper()}"
        log.warning(f"[FAULT FM_2_2] Hallucinated transaction_id: {fake_id}")
        return {
            "transaction_id": fake_id,
            "hallucinated": True,
            "original_suppressed": real_result.get("transaction_id"),
        }
    return real_result


def maybe_force_decline() -> bool:
    """BL_CARD_DECLINED: force a valid card to be declined."""
    if FAULT_MODE == "BL_CARD_DECLINED":
        log.warning("[FAULT BL_CARD_DECLINED] Forcing card decline on valid card")
        return True
    return False


def maybe_skip_save() -> bool:
    """BL_TRANSACTION_LOST: skip the MongoDB save silently."""
    if FAULT_MODE == "BL_TRANSACTION_LOST":
        log.warning("[FAULT BL_TRANSACTION_LOST] Save bypassed — transaction not persisted")
        return True
    return False


def maybe_inject_double_charge(save_payload: dict) -> dict:
    """BL_DOUBLE_CHARGE: mark transaction as a duplicate charge."""
    if FAULT_MODE == "BL_DOUBLE_CHARGE":
        log.warning("[FAULT BL_DOUBLE_CHARGE] Injecting double-charge marker")
        save_payload["double_charge"] = True
        save_payload["duplicate_of"] = save_payload.get("transaction_id", "unknown")
    return save_payload
