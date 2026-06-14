"""
Fault Injection Module — MAST-aligned fault patterns for shippingservice
=========================================================================
Faults available (set FAULT_MODE env var before running):

  FM_1_2           — Category 1 (Planning): Incorrect Task Decomposition
                     Task spec fed to Llama omits carrier-selection and
                     tracking steps, so the agent never plans to call them.

  FM_2_2           — Category 2 (Execution): Hallucinated Tool Output
                     select_carrier returns fabricated carrier data instead
                     of the real scoring result; agent accepts it blindly.

    FM_2_5           — Category 2 (Execution): Ignored Other Agent's Input
                                         Order agent ignores downstream quote response and uses a
                                         stale/default cost when selecting carrier, effectively
                                         dropping service-to-service information.

  FM_3_1           — Category 3 (Verification): Premature Termination
                     Agent returns Final Answer after only get_shipping_quote,
                     before carrier selection or tracking ID are generated.

  BL_SHIPMENT_LOST          — Business Logic: Shipment Lost
                               Tracking ID is generated but the MongoDB save is
                               silently skipped — order appears placed but untracked.

  BL_INVENTORY_MISMATCH     — Business Logic: Inventory Mismatch
                               Item quantities are corrupted before quoting so the
                               agent fulfils an order with wrong item counts.

  BL_VENDOR_NEGOTIATION     — Business Logic: Vendor Negotiation
                               Carrier selection is forced to a high-cost vendor
                               regardless of the quote, simulating a failed
                               negotiation that overrides normal selection logic.

  BL_CUSTOMER_ESCALATION    — Business Logic: Customer Escalation
                               An escalation flag is injected into the final answer
                               metadata, simulating an agent that detects a high-risk
                               order and escalates instead of completing silently.

  BL_REFUND_REASONING       — Business Logic: Refund Reasoning
                               Cost is forced negative to simulate an erroneous
                               refund-required condition that should have been caught
                               by the agent before saving.

  BL_COMPLIANCE_AMBIGUITY   — Business Logic: Compliance Ambiguity
                               The destination address is tagged with an unknown
                               compliance jurisdiction so the agent cannot confirm
                               regulatory clearance before dispatch.

Usage:
  export FAULT_MODE=FM_3_1   # then run the service or test runner
  export FAULT_MODE=NONE     # baseline (no faults)
"""

import os
import logging

log = logging.getLogger(__name__)

# ── Active fault (read once at import time) ───────────────────────────────────
FAULT_MODE = os.getenv("FAULT_MODE", "NONE").upper()

FM_1_2           = "FM_1_2"
FM_2_2           = "FM_2_2"
FM_2_5           = "FM_2_5"
FM_3_1           = "FM_3_1"
BL_SHIPMENT_LOST       = "BL_SHIPMENT_LOST"
BL_INVENTORY_MISMATCH  = "BL_INVENTORY_MISMATCH"
BL_VENDOR_NEGOTIATION  = "BL_VENDOR_NEGOTIATION"
BL_CUSTOMER_ESCALATION = "BL_CUSTOMER_ESCALATION"
BL_REFUND_REASONING    = "BL_REFUND_REASONING"
BL_COMPLIANCE_AMBIGUITY = "BL_COMPLIANCE_AMBIGUITY"


def active_fault() -> str:
    return FAULT_MODE


def is_active(fault: str) -> bool:
    active = FAULT_MODE == fault
    if active:
        log.warning("[FAULT INJECTION] Active fault: %s", fault)
    return active


# ── FM-1.2: Incorrect Task Decomposition ─────────────────────────────────────

def corrupt_task_spec(task: str) -> str:
    """
    FM-1.2 — Remove carrier-selection and tracking steps from the task
    description passed to the LLM.  The agent plans only the quote step,
    resulting in an incomplete shipment workflow.
    """
    if not is_active(FM_1_2):
        return task

    corrupted = task
    # Strip the ordered step list so agent only sees the quote instruction
    corrupted = corrupted.replace(
        "You MUST call these tools in order:\n"
        "1. get_shipping_quote — to get the cost\n"
        "2. select_carrier — using the cost and item count\n"
        "3. generate_tracking_id — using the chosen carrier\n",
        "You MUST call this tool:\n"
        "1. get_shipping_quote — to get the cost\n",
    )
    # Replace expected Final Answer shape so agent stops after cost only
    corrupted = corrupted.replace(
        'Then return: Final Answer: {"tracking_id": "<id>", "carrier": "<name>", '
        '"service_level": "<level>", "cost_usd": <number>}',
        'Then return: Final Answer: {"cost_usd": <number>}',
    )

    log.warning(
        "[FM-1.2] Task spec corrupted — carrier/tracking steps removed from plan"
    )
    return corrupted


# ── FM-2.2: Hallucinated Tool Output ─────────────────────────────────────────

def maybe_hallucinate_carrier(real_result: dict) -> dict:
    """
    FM-2.2 — Replace the real CarrierSelectionAgent result with fabricated
    data.  The hallucinated carrier ('SpeedyShip') does not exist; the
    service level ('ultra-express') is invalid; delivery days = 0.
    The downstream tracking agent will generate an ID for this fake carrier,
    producing an untraceable shipment.
    """
    if not is_active(FM_2_2):
        return real_result

    hallucinated = {
        "carrier":                  "SpeedyShip",
        "service_level":            "ultra-express",
        "estimated_delivery_days":  0,
        "reason":                   "optimal synergistic route",
    }
    log.warning("[FM-2.2] Carrier result hallucinated: %s", hallucinated)
    return hallucinated


# ── FM-2.5: Ignored Other Agent's Input ─────────────────────────────────────

def maybe_ignore_quote_for_carrier(cost_usd: float) -> float:
    """
    FM-2.5 — Ignore the downstream quote agent's cost response during
    carrier selection and use a stale/default value instead.
    """
    if not is_active(FM_2_5):
        return cost_usd

    stale_cost = 4.99
    log.warning(
        "[FM-2.5] Ignored quote response for carrier selection: quoted=%s -> used=%s",
        cost_usd,
        stale_cost,
    )
    return stale_cost


# ── FM-3.1: Premature Termination ────────────────────────────────────────────

def maybe_inject_early_termination(iteration: int, scratchpad: str) -> str | None:
    """
    FM-3.1 — After the first tool observation, inject a fake Final Answer so
    the ReAct loop terminates before carrier selection and tracking ID steps.

    Returns a Final Answer string to inject, or None if fault is not active
    or the trigger condition has not been met.
    """
    if not is_active(FM_3_1):
        return None

    # Trigger deterministically on/after the second loop iteration.
    # We intentionally avoid depending on strict parser behavior in the
    # first model output so FM-3.1 can be reproduced consistently.
    if iteration >= 1:
        early_answer = (
            '{"tracking_id": "PREMATURE-0000", '
            '"carrier": "Unknown", '
            '"service_level": "standard", '
            '"cost_usd": 0.0}'
        )
        log.warning(
            "[FM-3.1] Premature termination injected at iteration %d — "
            "carrier + tracking steps skipped",
            iteration,
        )
        return f"Final Answer: {early_answer}"

    return None


# ── BL-SHIPMENT_LOST: Business Logic — Shipment Lost ─────────────────────────

def should_skip_shipment_save() -> bool:
    """
    BL-SHIPMENT_LOST — Return True to silently skip the MongoDB save after
    tracking ID generation.  The caller receives a valid-looking tracking_id
    but no shipment record exists in the database.
    """
    if is_active(BL_SHIPMENT_LOST):
        log.warning(
            "[BL-SHIPMENT_LOST] MongoDB shipment save skipped — "
            "shipment lost fault active"
        )
        return True
    return False

# ── BL-INVENTORY_MISMATCH: Business Logic — Inventory Mismatch ───────────────

def maybe_corrupt_items(items: list) -> list:
    """
    BL_INVENTORY_MISMATCH — Double the quantity of every item to simulate an
    inventory mismatch where the agent processes more units than are available.
    The quoting and carrier steps will see inflated counts.
    """
    if not is_active(BL_INVENTORY_MISMATCH):
        return items

    corrupted = [
        {**item, "quantity": item.get("quantity", 1) * 2}
        for item in items
    ]
    log.warning(
        "[BL-INVENTORY_MISMATCH] Item quantities doubled: %s -> %s",
        items,
        corrupted,
    )
    return corrupted


# ── BL-VENDOR_NEGOTIATION: Business Logic — Vendor Negotiation ───────────────

def maybe_force_vendor(real_result: dict) -> dict:
    """
    BL_VENDOR_NEGOTIATION — Override carrier selection with a high-cost vendor
    to simulate a failed negotiation where the preferred carrier was unavailable
    and an expensive fallback is forced without agent awareness.
    """
    if not is_active(BL_VENDOR_NEGOTIATION):
        return real_result

    forced = {
        "carrier":                  "PremiumExpress",
        "service_level":            "overnight",
        "estimated_delivery_days":  1,
        "reason":                   "preferred vendor unavailable — forced fallback",
    }
    log.warning("[BL-VENDOR_NEGOTIATION] Carrier forced to expensive fallback: %s", forced)
    return forced


# ── BL-CUSTOMER_ESCALATION: Business Logic — Customer Escalation ─────────────

def maybe_inject_escalation_flag(result: dict) -> dict:
    """
    BL_CUSTOMER_ESCALATION — Inject an escalation_required flag into the
    shipment result metadata.  Simulates an agent that detects a high-risk
    order (e.g. high value, unusual address) and marks it for human review
    instead of completing silently.
    """
    if not is_active(BL_CUSTOMER_ESCALATION):
        return result

    escalated = {**result, "escalation_required": True, "escalation_reason": "high_risk_order"}
    log.warning(
        "[BL-CUSTOMER_ESCALATION] Escalation flag injected into result: %s",
        escalated,
    )
    return escalated


# ── BL-REFUND_REASONING: Business Logic — Refund Reasoning ───────────────────

def maybe_corrupt_cost(cost_usd: float) -> float:
    """
    BL_REFUND_REASONING — Force cost_usd to a negative value to simulate an
    erroneous refund-required condition.  The agent should detect this and
    block the order, but if it does not, it exposes a refund-reasoning gap.
    """
    if not is_active(BL_REFUND_REASONING):
        return cost_usd

    corrupted = -abs(cost_usd)
    log.warning(
        "[BL-REFUND_REASONING] Cost corrupted to negative value: %s -> %s",
        cost_usd,
        corrupted,
    )
    return corrupted


# ── BL-COMPLIANCE_AMBIGUITY: Business Logic — Compliance Ambiguity ───────────

def maybe_tag_compliance_unknown(address: dict) -> dict:
    """
    BL_COMPLIANCE_AMBIGUITY — Add an unknown compliance jurisdiction tag to
    the address so the agent cannot confirm regulatory clearance before
    dispatching the shipment.
    """
    if not is_active(BL_COMPLIANCE_AMBIGUITY):
        return address

    tagged = {**address, "compliance_jurisdiction": "UNKNOWN", "export_restricted": True}
    log.warning(
        "[BL-COMPLIANCE_AMBIGUITY] Address tagged with unknown compliance jurisdiction: %s",
        tagged,
    )
    return tagged