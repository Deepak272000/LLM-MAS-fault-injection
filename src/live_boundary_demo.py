"""Run the live boundary validation demo.

This clears results/boundary_events.jsonl, enables boundary event emission,
then runs the evidence scripts that produce the professor-facing examples.
Open boundary_dashboard.py in another terminal to watch events appear live.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
EVENTS = RESULTS / "boundary_events.jsonl"
SCRIPTS = [
    "cross_agent_propagation.py",
    "boundary_detection_runner.py",
    "repo_hitl_audit.py",
]


def load_events() -> list[dict]:
    if not EVENTS.exists():
        return []
    events = []
    with EVENTS.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    EVENTS.write_text("", encoding="utf-8")

    env = os.environ.copy()
    env["BOUNDARY_EVENTS_ENABLED"] = "1"
    env["BOUNDARY_EVENTS_FILE"] = str(EVENTS)

    print("Live boundary demo")
    print(f"Events file: {EVENTS}")
    print("Dashboard command: python boundary_dashboard.py")
    print()

    for script in SCRIPTS:
        print("=" * 78)
        print(f"Running {script}")
        print("=" * 78)
        completed = subprocess.run([sys.executable, script], cwd=ROOT, env=env)
        if completed.returncode != 0:
            return completed.returncode

    events = load_events()
    alerts = [event for event in events if event.get("alert")]
    print("=" * 78)
    print("LIVE BOUNDARY EVENT SUMMARY")
    print("=" * 78)
    print(f"Total events : {len(events)}")
    print(f"Alerts       : {len(alerts)}")
    print(f"Clean checks : {len(events) - len(alerts)}")
    for event in alerts:
        print(
            f"- {event.get('boundary')} | status={event.get('status')} | "
            f"difference={event.get('difference')}"
        )
    print(f"\nOpen http://127.0.0.1:8765 to inspect the event table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())