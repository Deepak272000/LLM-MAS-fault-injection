"""
Isolated TruLens dashboard launcher for LKW export data.

Safety properties:
- additive only (no modification of team runtime code)
- uses a dedicated local SQLite file for TruLens records
- does not delete any existing file or database

Usage:
  "e:/Summer ai Agent Project/.venv/Scripts/python.exe" trulens_dashboard_lkw.py
  "e:/Summer ai Agent Project/.venv/Scripts/python.exe" trulens_dashboard_lkw.py --port 8505
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# Must be set before importing TruLens so legacy recording APIs can be used.
os.environ.setdefault("TRULENS_OTEL_TRACING", "0")

# Ensure `streamlit` executable in the venv can be discovered by run_dashboard.
scripts_dir = os.path.dirname(sys.executable)
os.environ["PATH"] = scripts_dir + os.pathsep + os.environ.get("PATH", "")

import subprocess

from trulens.apps.basic import TruBasicApp
from trulens.core import TruSession
from trulens.core.schema.feedback import FeedbackResultStatus


DATASET_FILE = "trulens_lkw_dataset.json"
DB_FILE = "trulens_lkw_local_only.db"
SUMMARY_FILE = "trulens_leaderboard_summary.json"


def _load_dataset(dataset_path: Path) -> list[dict]:
    with dataset_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("records", [])


def _existing_source_record_ids(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT record_json FROM trulens_records")
        existing_ids: set[str] = set()
        for (record_json,) in cur.fetchall():
            try:
                row = json.loads(record_json)
                source_id = (row.get("meta") or {}).get("source_record_id")
                if source_id:
                    existing_ids.add(str(source_id))
            except Exception:
                # Skip malformed rows rather than failing dashboard startup.
                continue
        return existing_ids
    except sqlite3.OperationalError:
        # Table may not exist on first run.
        return set()
    finally:
        con.close()


def _summarize_record(record_payload: str) -> str:
    record = json.loads(record_payload)
    fault_mode = record.get("fault_mode", "UNKNOWN")
    output = record.get("output", {})
    rip = output.get("rip_summary", {})
    summary = {
        "record_id": record.get("record_id"),
        "fault_mode": fault_mode,
        "elapsed_ms": output.get("elapsed_ms"),
        "error": output.get("error"),
        "reachability": rip.get("reachability", []),
        "infection_point": rip.get("infection_point"),
        "missing_steps": rip.get("missing_steps", []),
    }
    return json.dumps(summary, ensure_ascii=True)


def ingest_records(
    records: list[dict],
    session: TruSession,
    existing_source_ids: set[str],
) -> tuple[int, int]:
    # Wrap a deterministic serializer function so each call is recorded by TruLens.
    app = TruBasicApp(
        text_to_text=_summarize_record,
        app_name="shippingservice-lkw-rip",
        app_version="local",
        app_id="shippingservice-lkw-rip-local",
        session=session,
    )

    ingested = 0
    skipped = 0
    for record in records:
        source_record_id = str(record.get("record_id", ""))
        if source_record_id in existing_source_ids:
            skipped += 1
            continue

        payload = json.dumps(record, ensure_ascii=True)
        result, tr_record = app.with_record(
            app.app._call,
            payload,
            record_metadata={
                "source_record_id": source_record_id,
                "fault_mode": record.get("fault_mode"),
            },
        )
        # Add a simple binary quality score so Leaderboard has at least one metric.
        # 1.0 means no error reported in the run output, 0.0 otherwise.
        has_error = bool(record.get("output", {}).get("error"))
        session.add_feedback(
            record_id=tr_record.record_id,
            name="run_success_score",
            result=0.0 if has_error else 1.0,
            status=FeedbackResultStatus.DONE,
        )
        _ = result
        _ = tr_record
        ingested += 1

    return ingested, skipped


def build_local_leaderboard_summary(records: list[dict]) -> dict:
    total = len(records)
    successes = 0
    total_latency = 0.0
    by_fault_mode: dict[str, dict] = {}

    for record in records:
        fault_mode = str(record.get("fault_mode", "UNKNOWN"))
        output = record.get("output", {}) or {}
        rip = output.get("rip_summary", {}) or {}

        elapsed_ms = float(output.get("elapsed_ms", 0.0) or 0.0)
        has_error = bool(output.get("error"))
        infection_point = rip.get("infection_point")

        total_latency += elapsed_ms
        if not has_error:
            successes += 1

        if fault_mode not in by_fault_mode:
            by_fault_mode[fault_mode] = {
                "count": 0,
                "success_count": 0,
                "avg_elapsed_ms": 0.0,
                "infection_detected_count": 0,
                "missing_steps_total": 0,
            }

        fm = by_fault_mode[fault_mode]
        fm["count"] += 1
        fm["success_count"] += 0 if has_error else 1
        fm["avg_elapsed_ms"] += elapsed_ms
        fm["infection_detected_count"] += 1 if infection_point else 0
        fm["missing_steps_total"] += len(rip.get("missing_steps", []) or [])

    for fm in by_fault_mode.values():
        count = max(int(fm["count"]), 1)
        fm["avg_elapsed_ms"] = round(float(fm["avg_elapsed_ms"]) / count, 3)
        fm["success_rate"] = round(float(fm["success_count"]) / count, 3)

    return {
        "records_total": total,
        "success_rate": round(float(successes) / max(total, 1), 3),
        "avg_elapsed_ms": round(total_latency / max(total, 1), 3),
        "by_fault_mode": by_fault_mode,
    }


def _launch_streamlit(db_path: Path, port: int) -> None:
    """Launch the TruLens Streamlit dashboard using the current Python executable."""
    # Find the TruLens dashboard Streamlit app file via the installed package.
    try:
        import trulens.dashboard as _td_pkg
        pkg_dir = Path(_td_pkg.__file__).resolve().parent
        # TruLens dashboard entry points across versions
        for candidate in ("main.py", "streamlit.py", "Home.py", "Leaderboard.py", "streamlit_app.py"):
            app_file = pkg_dir / "pages" / candidate
            if not app_file.exists():
                app_file = pkg_dir / candidate
            if app_file.exists():
                break
        else:
            raise FileNotFoundError(
                f"Could not find TruLens Streamlit app under {pkg_dir}"
            )
    except Exception as exc:
        print(f"[WARN] Could not locate TruLens Streamlit app: {exc}")
        print("Dashboard not started. Use the local leaderboard summary instead.")
        return

    db_url = f"sqlite:///{db_path.as_posix()}"
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_file),
        "--server.port", str(port),
        "--server.headless", "true",
        "--",
        "--database-url", db_url,
    ]
    print(f"Launching: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch isolated TruLens dashboard for LKW data."
    )
    parser.add_argument("--port", type=int, default=8505)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    dataset_path = root / DATASET_FILE
    db_path = root / DB_FILE
    summary_path = root / SUMMARY_FILE

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Cannot find {DATASET_FILE}. Run trulens_prepare_lkw.py first."
        )

    records = _load_dataset(dataset_path)
    if not records:
        raise RuntimeError("No records found in trulens dataset export.")

    existing_source_ids = _existing_source_record_ids(db_path)
    session = TruSession(database_url=f"sqlite:///{db_path.as_posix()}")
    ingested, skipped = ingest_records(records, session, existing_source_ids)
    summary = build_local_leaderboard_summary(records)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print("TruLens ingest complete")
    print(f"Dataset: {dataset_path}")
    print(f"Database: {db_path}")
    print(f"Ingested records: {ingested}")
    print(f"Skipped duplicates: {skipped}")
    print(f"Local leaderboard summary: {summary_path}")
    print(
        "Note: If TruLens Leaderboard shows an internal SQL error, use this local "
        "summary + /Records page for evaluation."
    )
    print(f"Starting dashboard on port {args.port} ...")
    print(f"Records view: http://localhost:{args.port}/Records")
    print(f"Leaderboard: http://localhost:{args.port}/")

    _launch_streamlit(db_path, port=args.port)


if __name__ == "__main__":
    main()
