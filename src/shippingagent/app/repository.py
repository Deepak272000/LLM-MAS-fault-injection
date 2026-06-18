from datetime import datetime, timezone
from database import quotes_collection, shipments_collection


async def save_quote(address: dict, items: list, cost_usd: float, breakdown: dict) -> str:
    doc = {
        "address":    address,
        "items":      items,
        "cost_usd":   cost_usd,
        "breakdown":  breakdown,
        "created_at": datetime.now(timezone.utc),
    }
    result = await quotes_collection.insert_one(doc)
    return str(result.inserted_id)


async def save_shipment(
    address:       dict,
    items:         list,
    cost_usd:      float,
    carrier:       str,
    service_level: str,
    tracking_id:   str,
) -> str:
    doc = {
        "address":       address,
        "items":         items,
        "cost_usd":      cost_usd,
        "carrier":       carrier,
        "service_level": service_level,
        "tracking_id":   tracking_id,
        "created_at":    datetime.now(timezone.utc),
    }
    result = await shipments_collection.insert_one(doc)
    return str(result.inserted_id)


async def get_shipment_by_tracking(tracking_id: str):
    doc = await shipments_collection.find_one({"tracking_id": tracking_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc