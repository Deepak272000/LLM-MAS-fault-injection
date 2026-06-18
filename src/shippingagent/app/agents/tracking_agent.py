"""
TrackingAgent
=============
Sub-agent that generates a unique, carrier-formatted tracking ID
and "registers" the shipment (mock  in production this would call
the carrier's API).

Tracking ID format per carrier:
  FedEx:  12-digit numeric  ? 7489[timestamp][random]
  UPS:    1Z + 16 alphanumeric
  USPS:   22-digit numeric  ? 9400[timestamp][random]
  DHL:    10-digit numeric
  Default: UUID-based fallback
"""

import logging
import random
import string
import time
import uuid

log = logging.getLogger(__name__)


class TrackingAgent:
    """
    Generates a unique tracking ID for a shipment.
    Invoked as a tool by the Claude orchestrator.
    """

    def generate(self, carrier: str, address: dict, item_count: int) -> dict:
        """
        Generate a tracking ID.

        Args:
            carrier:    carrier name (e.g. "FedEx", "UPS", "USPS", "DHL")
            address:    destination address dict
            item_count: number of items in shipment

        Returns:
            dict with keys:
              - tracking_id: str
              - carrier: str
              - registered: bool
        """
        ts = str(int(time.time()))[-8:]  # last 8 digits of unix timestamp
        rand4 = "".join(random.choices(string.digits, k=4))
        carrier_upper = carrier.upper()

        if carrier_upper == "FEDEX":
            tracking_id = f"7489{ts}{rand4}"
        elif carrier_upper == "UPS":
            alphanum = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
            tracking_id = f"1Z{alphanum}"
        elif carrier_upper == "USPS":
            tracking_id = f"9400{ts}{rand4}{rand4}"
        elif carrier_upper == "DHL":
            rand2 = "".join(random.choices(string.digits, k=2))
            tracking_id = f"{ts}{rand2}"  # 10 digits: 8 ts + 2 rand
        else:
            tracking_id = str(uuid.uuid4()).replace("-", "").upper()[:20]

        log.info(
            f"TrackingAgent: generated {tracking_id} for carrier={carrier}, "
            f"destination={address.get('city', 'unknown')}, items={item_count}"
        )

        # In production: call carrier.registerShipment(tracking_id, address, items)
        registered = True

        return {
            "tracking_id": tracking_id,
            "carrier": carrier,
            "registered": registered,
        }
