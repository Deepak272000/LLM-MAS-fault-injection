"""
Langfuse preparation for shippingservice LKW+RIP results.
==========================================================
Transforms the local fault-campaign output into a Langfuse-shaped JSONL export.

Usage:
  python langfuse_prepare_lkw.py

The script is offline-first. If Langfuse credentials are configured later,
the exported trace data can be adapted or ingested without changing the
shippingservice runtime.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4


RESULTS_FILE = "lkw_rip_results.json"
OUTPUT_FILE = "langfuse_lkw_traces.jsonl"


def _trace_id() -> str:
    return uuid4().hex


def _span_id() -> str:
    return uuid4().hex[:16]


def _safe_iso_to_dt(value: str) -> datetime:
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _load_results() -> dict:
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, RESULTS_FILE)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Cannot find {RESULTS_FILE}. Run lkw_rip_runner.py first."
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_trace_events(results: dict) -> list[dict]:
    events: list[dict] = []
    generated_at = _safe_iso_to_dt(results.get("generated_at", ""))

    for index, run in enumerate(results.get("raw_results", [])):
        fault_mode = run.get("fault_mode", "UNKNOWN")
        lkw = run.get("lkw", {})
        ckpts = lkw.get("checkpoints", [])
        elapsed_ms = float(run.get("elapsed_ms", 0.0))
        trace_id = _trace_id()
        root_span_id = _span_id()
        start_time = generated_at + timedelta(seconds=index)
        end_time = start_time + timedelta(milliseconds=max(elapsed_ms, 1.0))

        events.append(
            {
                "trace_id": trace_id,
                "span_id": root_span_id,
                "parent_span_id": None,
                "type": "span",
                "name": "shipping_fault_run",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "input": {
                    "fault_mode": fault_mode,
                    "test_address": results.get("test_address", {}),
                    "test_items": results.get("test_items", []),
                },
                "output": {
                    "error": run.get("error"),
                    "elapsed_ms": elapsed_ms,
                    "rip_summary": lkw.get("rip_summary", {}),
                },
                "metadata": {
                    "source": "shippingservice.lkw_rip_runner",
                    "service": "shippingservice",
                    "fault_mode": fault_mode,
                },
            }
        )

        for step_index, ckpt in enumerate(ckpts):
            step_start = start_time + timedelta(milliseconds=step_index * 30)
            step_end = step_start + timedelta(milliseconds=20)
            events.append(
                {
                    "trace_id": trace_id,
                    "span_id": _span_id(),
                    "parent_span_id": root_span_id,
                    "type": "span",
                    "name": str(ckpt.get("step", "UNKNOWN_STEP")),
                    "start_time": step_start.isoformat(),
                    "end_time": step_end.isoformat(),
                    "input": {"fault_mode": fault_mode},
                    "output": ckpt.get("data", {}),
                    "metadata": {
                        "checkpoint_time": ckpt.get("timestamp"),
                        "fault_mode": ckpt.get("fault_mode"),
                    },
                }
            )

    return events


def main() -> None:
    results = _load_results()
    events = build_trace_events(results)

    root = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(root, OUTPUT_FILE)

    with open(out_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    print("Langfuse trace export ready")
    print(f"Open: {out_path}")
    print("This JSONL file mirrors the root trace plus child checkpoint spans.")
    print("If you later configure Langfuse credentials, this is the shape to map into the SDK.")


if __name__ == "__main__":
    main()