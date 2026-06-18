"""
CarrierSelectionAgent
=====================
Sub-agent that selects the optimal shipping carrier given:
  - Destination address (country, state, zip)
  - Estimated cost in USD
  - Number of items

Selection logic uses a rule-based scoring system:
  - Domestic (US) ? prefers FedEx or USPS
  - International ? prefers DHL or UPS
  - Large orders ? prefers carriers with better bulk rates
  - Urgency threshold ? upgrades to express service
"""

import logging

log = logging.getLogger(__name__)


CARRIERS = [
    {
        "name": "FedEx",
        "domestic_score": 9,
        "international_score": 7,
        "bulk_score": 8,
        "base_days": 3,
        "express_days": 1,
        "express_threshold_usd": 15.0,
    },
    {
        "name": "UPS",
        "domestic_score": 8,
        "international_score": 9,
        "bulk_score": 9,
        "base_days": 4,
        "express_days": 2,
        "express_threshold_usd": 18.0,
    },
    {
        "name": "USPS",
        "domestic_score": 10,
        "international_score": 4,
        "bulk_score": 5,
        "base_days": 5,
        "express_days": 2,
        "express_threshold_usd": 12.0,
    },
    {
        "name": "DHL",
        "domestic_score": 6,
        "international_score": 10,
        "bulk_score": 8,
        "base_days": 5,
        "express_days": 2,
        "express_threshold_usd": 20.0,
    },
]


class CarrierSelectionAgent:
    """
    Selects the best shipping carrier for a given shipment profile.
    Invoked as a tool by the Claude orchestrator.
    """

    BULK_THRESHOLD = 10  # items

    def select(self, address: dict, cost_usd: float, item_count: int) -> dict:
        """
        Select the best carrier.

        Args:
            address:    dict with keys: country, state (optional), zip_code (optional)
            cost_usd:   estimated shipping cost
            item_count: total number of items

        Returns:
            dict with keys:
              - carrier: str
              - service_level: str ("standard" | "express")
              - estimated_delivery_days: int
              - reason: str
        """
        country = (address.get("country") or "US").upper().strip()
        is_domestic = country == "US"
        is_bulk = item_count >= self.BULK_THRESHOLD

        best_carrier = None
        best_score = -1

        for carrier in CARRIERS:
            score = 0
            if is_domestic:
                score += carrier["domestic_score"]
            else:
                score += carrier["international_score"]

            if is_bulk:
                score += carrier["bulk_score"] * 0.5

            if score > best_score:
                best_score = score
                best_carrier = carrier

        # Determine service level
        service_level = "standard"
        delivery_days = best_carrier["base_days"]
        if cost_usd >= best_carrier["express_threshold_usd"]:
            service_level = "express"
            delivery_days = best_carrier["express_days"]

        reason = (
            f"Selected {best_carrier['name']} (score={best_score:.1f}) for "
            f"{'domestic' if is_domestic else 'international'} "
            f"{'bulk ' if is_bulk else ''}shipment to {country}. "
            f"Service: {service_level}, ETA: {delivery_days} day(s)."
        )

        log.info(f"CarrierSelectionAgent: {reason}")

        return {
            "carrier": best_carrier["name"],
            "service_level": service_level,
            "estimated_delivery_days": delivery_days,
            "reason": reason,
        }
