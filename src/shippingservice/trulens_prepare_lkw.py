"""
TruLens preparation for shippingservice LKW+RIP results.
========================================================
Transforms the local fault-campaign output into a compact dataset export that
can be used for TruLens batch evaluation, comparison, or dashboard import.

Usage:
  python trulens_prepare_lkw.py

This script is intentionally offline-first. It writes a local JSON export even
when TruLens credentials or dashboard services are not configured.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


RESULTS_FILE = "lkw_rip_results.json"
OUTPUT_FILE = "trulens_lkw_dataset.json"


def _safe_iso(value: str) -> str:
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _load_results() -> dict:
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, RESULTS_FILE)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Cannot find {RESULTS_FILE}. Run lkw_rip_runner.py first."
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_records(results: dict) -> list[dict]:
    records: list[dict] = []

    for index, run in enumerate(results.get("raw_results", [])):
        lkw = run.get("lkw", {})
        rip = lkw.get("rip_summary", {})

        records.append(
            {
                "record_id": f"shippingservice-{index + 1}",
                "fault_mode": run.get("fault_mode", "UNKNOWN"),
                "input": {
                    "test_address": results.get("test_address", {}),
                    "test_items": results.get("test_items", []),
                },
                "output": {
                    "error": run.get("error"),
                    "elapsed_ms": run.get("elapsed_ms", 0.0),
                    "rip_summary": rip,
                },
                "metadata": {
                    "source": "shippingservice.lkw_rip_runner",
                    "generated_at": results.get("generated_at"),
                    "recorded_at": _safe_iso(results.get("generated_at", "")),
                    "missing_steps": lkw.get("missing_steps", []),
                },
            }
        )

    return records


def main() -> None:
    results = _load_results()
    records = build_records(results)

    root = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(root, OUTPUT_FILE)

    payload = {
        "dataset_name": "shippingservice-lkw-rip",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_results_file": RESULTS_FILE,
        "records": records,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("TruLens dataset export ready")
    print(f"Open: {out_path}")
    print("This file can be used for offline comparison or imported into a TruLens workflow.")


if __name__ == "__main__":
    main()