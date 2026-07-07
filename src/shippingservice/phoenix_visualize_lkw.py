"""
Phoenix Visualizer for Shippingservice LKW+RIP Results
=====================================================
Converts local fault-campaign output (lkw_rip_results.json) into a Phoenix
TraceDataset so you can inspect runs in a visual run-tree UI similar to
LangSmith screenshots.

Usage:
  python phoenix_visualize_lkw.py

Then open the printed Phoenix URL (default http://127.0.0.1:6006).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pandas as pd
import phoenix as px
from phoenix.trace import TraceDataset


RESULTS_FILE = "lkw_rip_results.json"


def _span_id() -> str:
    # Phoenix sample uses 16-char span IDs.
    return uuid4().hex[:16]


def _trace_id() -> str:
    # Phoenix sample uses 32-char trace IDs.
    return uuid4().hex[:32]


def _safe_iso_to_dt(value: str) -> datetime:
    try:
        # Handle trailing Z if present
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def build_trace_rows(results: dict) -> list[dict]:
    rows: list[dict] = []
    generated_at = _safe_iso_to_dt(results.get("generated_at", ""))

    for idx, run in enumerate(results.get("raw_results", [])):
        fault_mode = run.get("fault_mode", "UNKNOWN")
        lkw = run.get("lkw", {})
        ckpts = lkw.get("checkpoints", [])
        error = run.get("error")
        elapsed_ms = float(run.get("elapsed_ms", 0.0))

        trace_id = _trace_id()
        root_id = _span_id()
        start = generated_at + timedelta(seconds=idx)
        end = start + timedelta(milliseconds=max(elapsed_ms, 1))

        root_output = {
            "fault_mode": fault_mode,
            "elapsed_ms": elapsed_ms,
            "error": error,
            "rip_summary": lkw.get("rip_summary", {}),
            "missing_steps": lkw.get("missing_steps", []),
        }

        rows.append(
            {
                "name": "shipping_fault_run",
                "span_kind": "CHAIN",
                "parent_id": None,
                "start_time": start,
                "end_time": end,
                "status_code": "ERROR" if error else "OK",
                "status_message": error or "",
                "events": [],
                "context.span_id": root_id,
                "context.trace_id": trace_id,
                "attributes.input.mime_type": "application/json",
                "attributes.input.value": json.dumps(
                    {
                        "fault_mode": fault_mode,
                        "test_address": results.get("test_address", {}),
                        "test_items": results.get("test_items", []),
                    }
                ),
                "attributes.output.mime_type": "application/json",
                "attributes.output.value": json.dumps(root_output),
                "attributes.openinference.span.kind": "CHAIN",
                "attributes.metadata": json.dumps(
                    {"source": "lkw_rip_runner", "service": "shippingservice"}
                ),
                "attributes.tool.name": None,
                "attributes.tool.description": None,
            }
        )

        # Add child spans for each LKW checkpoint for visual step-by-step tree.
        for step_i, ckpt in enumerate(ckpts):
            c_start = start + timedelta(milliseconds=step_i * 30)
            c_end = c_start + timedelta(milliseconds=20)
            rows.append(
                {
                    "name": str(ckpt.get("step", "UNKNOWN_STEP")),
                    "span_kind": "TOOL",
                    "parent_id": root_id,
                    "start_time": c_start,
                    "end_time": c_end,
                    "status_code": "OK",
                    "status_message": "",
                    "events": [],
                    "context.span_id": _span_id(),
                    "context.trace_id": trace_id,
                    "attributes.input.mime_type": "application/json",
                    "attributes.input.value": json.dumps({"fault_mode": fault_mode}),
                    "attributes.output.mime_type": "application/json",
                    "attributes.output.value": json.dumps(ckpt.get("data", {})),
                    "attributes.openinference.span.kind": "TOOL",
                    "attributes.metadata": json.dumps(
                        {
                            "checkpoint_time": ckpt.get("timestamp"),
                            "fault_mode": ckpt.get("fault_mode"),
                        }
                    ),
                    "attributes.tool.name": str(ckpt.get("step", "UNKNOWN_STEP")),
                    "attributes.tool.description": "LKW checkpoint",
                }
            )

    return rows


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, RESULTS_FILE)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Cannot find {RESULTS_FILE}. Run lkw_rip_runner.py first."
        )

    with open(path, "r", encoding="utf-8") as f:
        results = json.load(f)

    rows = build_trace_rows(results)
    if not rows:
        raise RuntimeError("No trace rows generated from lkw_rip_results.json")

    df = pd.DataFrame(rows)
    dataset = TraceDataset(df, name="shippingservice-lkw-rip")

    # Persist data locally and run Phoenix in a background thread.
    session = px.launch_app(trace=dataset, use_temp_dir=False, run_in_thread=True)

    url = "http://127.0.0.1:6006"
    if session is not None and hasattr(session, "url"):
        url = session.url

    print("Phoenix UI ready")
    print(f"Open: {url}")
    print("Press Ctrl+C to stop this process.")

    try:
        # Keep process alive for local viewing.
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping Phoenix visualizer...")


if __name__ == "__main__":
    main()
