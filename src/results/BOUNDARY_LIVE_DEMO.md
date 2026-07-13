# Boundary Live Demo

This demo shows the professor where the new boundary flags appear while the system runs.

## Terminal 1: start the live dashboard

```bash
cd LLM-MAS/src
python boundary_dashboard.py
```

Open:

```text
http://127.0.0.1:8765
```

## Terminal 2: run the live evidence flow

```bash
cd LLM-MAS/src
python live_boundary_demo.py
```

The demo clears and rewrites:

```text
src/results/boundary_events.jsonl
```

Validated local run: the dashboard `/events` endpoint returned 13 total events, 8 alerts, and 5 clean checks.

## What to point out

The dashboard table shows each boundary event with:

- boundary name
- expected payload
- observed payload
- alert status
- difference
- violations

Expected professor-facing examples:

| Boundary | Expected | Observed | Benefit |
|---|---|---|---|
| `currency_to_payment` | `9` | `1337` | overcharge becomes machine-detectable |
| `catalog_to_recommendation` | `PROD-001` | `HALLUCINATED-001` | phantom product propagation becomes visible |
| `carrier_to_tracking` | valid carrier/service level | hallucinated carrier/service level | internal shipping corruption is localized |

## Why this proves the development

Before the new flags, LKW/RIP only showed whether checkpoints were reached. After the boundary refresh, every important handoff can emit a `BOUNDARY_CHECK` record with expected vs observed values and `alert=true` when semantic data escapes the upstream agent.