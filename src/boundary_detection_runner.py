"""Generate a structured summary of boundary checks and failure classes.

This runner is intentionally lightweight: it reuses the already-generated
cross-agent results and runs a few ShippingService monkeypatched scenarios so
we can verify the new boundary-style validation and infra-vs-fault separation
before updating the report.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CROSS_AGENT_RESULTS = RESULTS_DIR / "cross_agent_propagation.json"
SUMMARY_OUT = RESULTS_DIR / "boundary_detection_summary.json"

# Make sure both the repository root and the shipping app directory are importable.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shippingagent" / "app"))

from shippingagent.app import fault_injection as ship_fi  # noqa: E402
from shippingagent.app.orchestrator import ShippingOrchestrator  # noqa: E402


def _count_boundary_alerts(lkw_trace: dict) -> int:
    checkpoints = lkw_trace.get("checkpoints", []) if isinstance(lkw_trace, dict) else []
    return sum(1 for cp in checkpoints if cp.get("step") == "BOUNDARY_CHECK" and cp.get("data", {}).get("alert"))


def _extract_boundary_checks(lkw_trace: dict) -> list[dict]:
    checkpoints = lkw_trace.get("checkpoints", []) if isinstance(lkw_trace, dict) else []
    return [cp.get("data", {}) for cp in checkpoints if cp.get("step") == "BOUNDARY_CHECK"]


async def _run_shipping_clean() -> dict:
    ship_fi.FAULT_MODE = "NONE"
    orch = ShippingOrchestrator()
    orch._run_agent_loop = lambda task: json.dumps({
        "tracking_id": "TRACK-001",
        "carrier": "FedEx",
        "service_level": "ground",
        "cost_usd": 12.34,
    })
    result = await orch.ship_order(
        {"street_address": "1 Main St", "city": "Montreal", "state": "QC", "country": "CA", "zip_code": 12345},
        [{"product_id": "PROD-001", "quantity": 1}],
        capture_partial_trace=True,
    )
    lkw = result["_lkw"]
    return {
        "scenario": "shipping_clean",
        "failure_class": result.get("failure_class", "ok"),
        "boundary_alerts": _count_boundary_alerts(lkw),
        "boundary_checks": _extract_boundary_checks(lkw),
        "rip_summary": lkw.get("rip_summary", {}),
    }


async def _run_shipping_hallucinated_carrier() -> dict:
    ship_fi.FAULT_MODE = ship_fi.FM_2_2
    orch = ShippingOrchestrator()
    orch._run_agent_loop = lambda task: json.dumps({
        "tracking_id": "TRACK-001",
        "carrier": "SpeedyShip",
        "service_level": "ultra-express",
        "cost_usd": 12.34,
    })
    result = await orch.ship_order(
        {"street_address": "1 Main St", "city": "Montreal", "state": "QC", "country": "CA", "zip_code": 12345},
        [{"product_id": "PROD-001", "quantity": 1}],
        capture_partial_trace=True,
    )
    lkw = result["_lkw"]
    return {
        "scenario": "shipping_fm_2_2",
        "failure_class": result.get("failure_class", "fault_induced"),
        "boundary_alerts": _count_boundary_alerts(lkw),
        "boundary_checks": _extract_boundary_checks(lkw),
        "rip_summary": lkw.get("rip_summary", {}),
    }


def _run_shipping_quote_ignored() -> dict:
    ship_fi.FAULT_MODE = ship_fi.FM_2_5
    orch = ShippingOrchestrator()
    orch.carrier_agent.select = lambda address, cost_usd, item_count: {
        "carrier": "FedEx",
        "service_level": "ground",
        "selected_cost_usd": cost_usd,
        "item_count": item_count,
    }
    payload = {
        "address": {"city": "Montreal", "country": "CA", "state": "QC", "zip_code": 12345},
        "cost_usd": 12.34,
        "item_count": 1,
    }
    result = json.loads(orch._dispatch_tool("select_carrier", payload))
    return {
        "scenario": "shipping_fm_2_5",
        "failure_class": "fault_induced",
        "boundary_alerts": 1 if result.get("boundary_check", {}).get("alert") else 0,
        "boundary_checks": [result.get("boundary_check", {})],
        "boundary_check": result.get("boundary_check", {}),
        "used_cost_usd": result.get("boundary_check", {}).get("observed", {}).get("used_cost_usd"),
        "quoted_cost_usd": result.get("boundary_check", {}).get("expected", {}).get("quoted_cost_usd"),
    }


async def _run_shipping_timeout() -> dict:
    ship_fi.FAULT_MODE = "NONE"
    orch = ShippingOrchestrator()

    def boom(_task):
        raise RuntimeError("Llama read timeout after 1 attempt(s): synthetic timeout")

    orch._run_agent_loop = boom
    result = await orch.ship_order(
        {"street_address": "1 Main St", "city": "Montreal", "state": "QC", "country": "CA", "zip_code": 12345},
        [{"product_id": "PROD-001", "quantity": 1}],
        capture_partial_trace=True,
    )
    lkw = result["_lkw"]
    return {
        "scenario": "shipping_infra_timeout",
        "failure_class": result.get("failure_class", "infra_timeout"),
        "boundary_alerts": _count_boundary_alerts(lkw),
        "boundary_checks": _extract_boundary_checks(lkw),
        "rip_summary": lkw.get("rip_summary", {}),
    }


async def main() -> None:
    if not CROSS_AGENT_RESULTS.exists():
        raise FileNotFoundError(f"Missing cross-agent results file: {CROSS_AGENT_RESULTS}")

    cross_agent = json.loads(CROSS_AGENT_RESULTS.read_text(encoding="utf-8"))
    shipping_clean = await _run_shipping_clean()
    shipping_fm22 = await _run_shipping_hallucinated_carrier()
    shipping_fm25 = _run_shipping_quote_ignored()
    shipping_timeout = await _run_shipping_timeout()

    scenarios = [shipping_clean, shipping_fm22, shipping_fm25, shipping_timeout]
    boundary_alerts = sum(item.get("boundary_alerts", 0) for item in scenarios) + cross_agent.get("summary", {}).get("boundary_alerts", 0)
    signal_escapes = cross_agent.get("summary", {}).get("signal_escapes", 0) + sum(
        1 for item in scenarios if item.get("failure_class") == "fault_induced" and item.get("boundary_alerts", 0) > 0
    )
    infra_failures = sum(1 for item in scenarios if item.get("failure_class") == "infra_timeout")
    fault_induced = sum(1 for item in scenarios if item.get("failure_class") == "fault_induced")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "cross_agent": str(CROSS_AGENT_RESULTS),
            "shipping": "monkeypatched orchestrator scenarios",
        },
        "cross_agent": cross_agent,
        "shipping": scenarios,
        "totals": {
            "boundary_alerts": boundary_alerts,
            "signal_escapes": signal_escapes,
            "fault_induced": fault_induced,
            "infra_failures": infra_failures,
            "manual_review_candidates": fault_induced,
        },
    }

    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {SUMMARY_OUT}")


if __name__ == "__main__":
    asyncio.run(main())
