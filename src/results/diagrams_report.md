# LLM-MAS Research Diagrams Report

**Project:** Failure Injection and Propagation Analysis in Agentic Microservice Workflows  
**Author:** Deepak Sunil Chavan, Concordia University  
**Branch:** `deepak/fault-injection`  
**Date:** 2026-06-28  
**Data sources:** `src/shippingservice/lkw_rip_results.json`, `src/results/cross_agent_propagation.json`, `src/results/hitl_classification_report.json`

> All numeric annotations in this report are sourced directly from the JSON result files.
> All Mermaid diagrams render natively on GitHub. For Overleaf, see `paper_updated.tex` for embedded TikZ versions.

---

## Table of Contents

| # | Diagram | Paper Section |
|---|---|---|
| 1 | [Master System Architecture](#1-master-system-architecture) | Section II — System and Fault Model |
| 2 | [LKW/RIP Methodology Pipeline](#2-lkwrip-methodology-pipeline) | Section III — Failure Injection Workflow |
| 3 | [ShippingService FM-3.1 Failure Trace](#3-shippingservice-fm-31-failure-trace) | Section V — Retail Bench Results |
| 4 | [ShippingService FM-1.2 Failure Trace](#4-shippingservice-fm-12-failure-trace) | Section V — Retail Bench Results |
| 5 | [BL_COMPLIANCE_AMBIGUITY — INCONCLUSIVE Timeline](#5-bl_compliance_ambiguity--inconclusive-timeline) | Section V — Retail Bench Results |
| 6 | [Cross-Agent Chain A — Currency → Payment](#6-cross-agent-chain-a--currency--payment) | Section VII — Cross-Agent Propagation |
| 7 | [Cross-Agent Chain B — ProductCatalog → Recommendation](#7-cross-agent-chain-b--productcatalog--recommendation) | Section VII — Cross-Agent Propagation |
| 8 | [HITL Tier Classification Decision Tree](#8-hitl-tier-classification-decision-tree) | Section VIII — HITL Framework |

---

## 1. Master System Architecture

**Purpose:** Shows the full LLM-MAS topology — gRPC service connections, agent wrapper layers, and the shared Ollama LLM backend.

**Key facts:**
- 7 microservices connected to `CheckoutService` via gRPC
- 7 agent wrappers (LangGraph/ReAct) each orchestrating one service
- Single shared Ollama backend (qwen2.5-coder:14b, Concordia SPEED HPC A100 MIG)
- Frontend communicates with CheckoutService over HTTP

```mermaid
graph TD
  subgraph UserLayer ["User Layer"]
    UI["Frontend<br/>(HTTP / React)"]
  end

  subgraph OrchLayer ["Orchestration"]
    CS["CheckoutService<br/>(gRPC hub)"]
  end

  subgraph SvcLayer ["Microservice Layer — gRPC"]
    CurrS["CurrencyService"]
    PayS["PaymentService"]
    ShipS["ShippingService"]
    ProdS["ProductCatalogService"]
    RecS["RecommendationService"]
    AdS["AdService"]
    EmailS["EmailService"]
  end

  subgraph AgtLayer ["Agentic Layer — LangGraph / ReAct"]
    CurrA["CurrencyAgent"]
    PayA["PaymentAgent"]
    ShipA["ShippingOrchestrator<br/>(ReAct + LKW)"]
    ProdA["ProductCatalogAgent"]
    RecA["RecommendationAgent"]
    AdA["AdAgent"]
    EmailA["EmailAgent"]
  end

  subgraph LLMLayer ["LLM Backend"]
    LLM["Ollama: qwen2.5-coder:14b<br/>Concordia SPEED HPC — A100 MIG 1g.20gb"]
  end

  UI -->|HTTP| CS

  CS -->|gRPC| CurrS
  CS -->|gRPC| PayS
  CS -->|gRPC| ShipS
  CS -->|gRPC| ProdS
  CS -->|gRPC| RecS
  CS -->|gRPC| AdS
  CS -->|gRPC| EmailS

  CurrA -.->|orchestrates| CurrS
  PayA -.->|orchestrates| PayS
  ShipA -.->|orchestrates| ShipS
  ProdA -.->|orchestrates| ProdS
  RecA -.->|orchestrates| RecS
  AdA -.->|orchestrates| AdS
  EmailA -.->|orchestrates| EmailS

  CurrA -->|LLM calls| LLM
  PayA -->|LLM calls| LLM
  ShipA -->|LLM calls| LLM
  ProdA -->|LLM calls| LLM
  RecA -->|LLM calls| LLM
  AdA -->|LLM calls| LLM
  EmailA -->|LLM calls| LLM

  style UserLayer fill:#f0f4f8,stroke:#90a4ae
  style OrchLayer fill:#fff8e1,stroke:#ffb300
  style SvcLayer fill:#e3f2fd,stroke:#1976d2
  style AgtLayer fill:#e8f5e9,stroke:#388e3c
  style LLMLayer fill:#fbe9e7,stroke:#e64a19
```

> **Data source:** `src/protos/demo.proto` (gRPC definitions), `src/shippingservice/orchestrator.py` (ReAct), `src/*agent*/` (LangGraph agents)

---

## 2. LKW/RIP Methodology Pipeline

**Purpose:** Shows the complete testing pipeline from fault injection through RIP analysis to HITL tier classification. This is the core methodological contribution.

```mermaid
flowchart TD
  A(["Select Fault Mode<br/>NONE / FM-1.2 / FM-2.2 / FM-2.5 / FM-3.1 / BL-*"])
  A --> B["Inject Fault into Agent<br/>input, internal state, or tool output"]
  B --> C["Agent Executes<br/>LangGraph StateGraph / ReAct Loop"]
  C --> D["LKW Checkpoints Logged per Step<br/>TASK_START → domain steps → FINAL_ANSWER"]
  D --> E{{"RIP Triad Analysis"}}

  E --> R["R — Reachability<br/>Did fault reach the agent boundary?"]
  E --> I["I — Infection Point<br/>Which checkpoint first carries deviant state?"]
  E --> P["P — Propagation Depth<br/>How many downstream steps were affected?<br/>depth = |Baseline steps| − |Fault steps|"]

  R & I & P --> F["Compute Metrics<br/>propagation_depth / missing_steps / elapsed_ms"]

  F --> G{{"Classify Result"}}

  G -->|"Steps missing from LKW trace"| TP["TRUE POSITIVE<br/>Fault Detected — structural deviation"]
  G -->|"All steps reached, data semantically corrupted"| PTP["PARTIAL TRUE POSITIVE<br/>Silent fault — semantic deviation only"]
  G -->|"All steps reached, data correct"| TN["TRUE NEGATIVE<br/>Fault Contained — no propagation"]
  G -->|"No FINAL_ANSWER logged"| INC["INCONCLUSIVE<br/>Timeout or infra failure"]

  TP --> HITL
  PTP --> HITL

  subgraph HITL ["HITL Tier Assignment"]
    T1["TIER 1 — Structural<br/>Auto-detectable via step-count diff<br/>HITL for severity assessment"]
    T2["TIER 2 — Flag-Detectable<br/>LKW flag monitor triggers HITL alert"]
    T3["TIER 3 — Silent<br/>Full semantic human review required"]
  end

  HITL --> OUT["Record in *_fault_results.json<br/>or lkw_rip_results.json"]

  style TP fill:#c8e6c9,stroke:#388e3c
  style PTP fill:#fff9c4,stroke:#f9a825
  style TN fill:#e3f2fd,stroke:#1976d2
  style INC fill:#ffcdd2,stroke:#d32f2f
  style T1 fill:#ffcdd2,stroke:#d32f2f
  style T2 fill:#ffe0b2,stroke:#e65100
  style T3 fill:#ef9a9a,stroke:#b71c1c
```

> **Data source:** `src/shippingservice/lkw_rip_runner.py`, `src/hitl_detector.py`, `src/stability_analysis.py`

---

## 3. ShippingService FM-3.1 Failure Trace

**Fault:** FM-3.1 — Premature Termination  
**Result:** TRUE POSITIVE — fault structurally detected  
**Key metrics** (from `lkw_rip_results.json`):

| Field | Value |
|---|---|
| `infection_point` | `QUOTE_DONE` |
| `propagation_depth` | 1 |
| `missing_steps` | `[CARRIER_DONE]` |
| `elapsed_ms` | 44,799 ms |
| `tracking_id` | `PREMATURE-0000` |
| `cost_usd` | 0.0 |

```mermaid
sequenceDiagram
  participant FI as Fault Injector
  participant Orch as ShippingOrchestrator (ReAct)
  participant LKW as LKW Logger
  participant Down as Downstream

  FI->>Orch: FM_3_1 injected<br/>tracking_id=PREMATURE-0000, cost_usd=0.0<br/>reason=premature_termination

  activate Orch
  Orch->>LKW: TASK_START (t=0 ms)
  Orch->>Orch: Generate shipping quote
  Orch->>LKW: QUOTE_DONE (t≈45 ms)

  Note over Orch,LKW: INFECTION POINT = QUOTE_DONE<br/>fault state enters checkpoint log here

  Orch--xLKW: CARRIER_DONE — NOT LOGGED<br/>expected carrier selection step is skipped<br/>propagation_depth = 1 starts here

  Note over Orch,LKW: Instrumentation gap (Limitation L3):<br/>ESCALATION_CHECK also absent from<br/>expected_steps definition

  Orch->>LKW: TRACKING_DONE
  Orch->>LKW: SAVE_DONE
  Orch->>LKW: FINAL_ANSWER (t=44,799 ms)
  deactivate Orch

  Note over FI,Down: Classification: TRUE POSITIVE<br/>propagation_depth=1, missing=[CARRIER_DONE]<br/>HITL Tier 1 — Structural (auto-detectable)
```

---

## 4. ShippingService FM-1.2 Failure Trace

**Fault:** FM-1.2 — Incorrect Task Decomposition (malformed/schema-invalid input)  
**Result:** PARTIAL TRUE POSITIVE — all steps reached but fault detectable at CARRIER_DONE  
**Key metrics** (from `lkw_rip_results.json`):

| Field | Value |
|---|---|
| `infection_point` | `CARRIER_DONE` |
| `propagation_depth` | 0 |
| `missing_steps` | `[]` |
| `elapsed_ms` | 9,678 ms |

```mermaid
sequenceDiagram
  participant FI as Fault Injector
  participant Orch as ShippingOrchestrator (ReAct)
  participant LKW as LKW Logger

  FI->>Orch: FM_1_2 injected<br/>malformed or schema-invalid input

  activate Orch
  Orch->>LKW: TASK_START (t=0 ms)
  Orch->>LKW: QUOTE_DONE
  Orch->>LKW: CARRIER_DONE (t=9,678 ms)

  Note over Orch,LKW: INFECTION POINT = CARRIER_DONE<br/>All steps still reach the LKW log (depth=0)<br/>but checkpoint data carries fault signature

  Orch->>LKW: TRACKING_DONE
  Orch->>LKW: SAVE_DONE
  Orch->>LKW: FINAL_ANSWER
  deactivate Orch

  Note over FI,LKW: Classification: PARTIAL TRUE POSITIVE<br/>propagation_depth=0, all steps reached<br/>Fault visible only via checkpoint data inspection<br/>HITL Tier 2 — Flag-Detectable
```

---

## 5. BL_COMPLIANCE_AMBIGUITY — INCONCLUSIVE Timeline

**Fault:** BL_COMPLIANCE_AMBIGUITY — complex regulatory compliance scenario  
**Result:** INCONCLUSIVE — HTTP read timeout, agent never returned FINAL_ANSWER  
**Key metrics** (from `lkw_rip_results.json`):

| Field | Value |
|---|---|
| `elapsed_ms` | 577,682 ms (≈ 9 min 37 sec) |
| `error` | `requests.exceptions.ReadTimeout` (Ollama timeout) |
| `FINAL_ANSWER` | Never logged |

```mermaid
sequenceDiagram
  participant FI as Fault Injector
  participant Orch as ShippingOrchestrator (ReAct)
  participant LLM as Ollama qwen2.5-coder:14b
  participant LKW as LKW Logger

  FI->>Orch: BL_COMPLIANCE_AMBIGUITY injected<br/>complex regulatory compliance scenario

  activate Orch
  Orch->>LKW: TASK_START (t=0 ms)

  Orch->>LLM: LLM call — reasoning over compliance scenario
  activate LLM

  Note over LLM: Very long inference chain<br/>Multiple ReAct loop iterations<br/>No token limit hit — model keeps reasoning

  Orch->>LLM: (ReAct iteration 2...)
  Orch->>LLM: (ReAct iteration 3...)

  Note over Orch,LLM: t = 577,682 ms ≈ 9 minutes 37 seconds

  LLM--xOrch: HTTP Read Timeout<br/>requests.exceptions.ReadTimeout<br/>Ollama did not return before timeout

  deactivate LLM
  deactivate Orch

  Note over LKW: FINAL_ANSWER — NEVER LOGGED<br/>No LKW checkpoint after TASK_START

  Note over FI,LKW: Classification: INCONCLUSIVE<br/>Cause: infrastructure timeout, not fault behavior<br/>See Limitation L2 (HPC environment constraints)
```

---

## 6. Cross-Agent Chain A — Currency → Payment

**Experiment:** CurrencyAgent injected with FM-2.2 (hallucinated output); PaymentAgent runs baseline (NONE).  
**Finding:** Hallucinated exchange rate propagates silently across the agent boundary with no LKW structural signal at hop 2.  
**Key metrics** (from `cross_agent_propagation.json`):

| Field | Value |
|---|---|
| `hop1_infection` | `CONVERT_DONE` |
| `baseline_units` | 9 EUR |
| `propagated_units` | 1,337 EUR |
| `overcharge_eur` | 1,328 EUR |
| `overcharge_pct` | **14,755.6%** |
| `hop2_infection` | `null` (no signal at PaymentAgent) |
| `hop2_steps_lost` | 0 of 5 |

```mermaid
flowchart LR
  subgraph Hop1 ["HOP 1 — CurrencyAgent  FM-2.2 injected"]
    direction TB
    CA_in(["Input:<br/>convert 9 USD to EUR"])
    CA_1["TASK_START"]
    CA_2["CONVERT_DONE<br/>INFECTION POINT<br/>hallucinated rate x148.6<br/>output: 1,337 EUR<br/>baseline: 9 EUR"]
    CA_3["FINAL_ANSWER<br/>returns 1,337 EUR"]
    CA_in --> CA_1 --> CA_2 --> CA_3
  end

  PROP["SILENT PROPAGATION<br/>1,337 EUR passed as-is<br/>no LKW flag at boundary"]

  subgraph Hop2 ["HOP 2 — PaymentAgent  NONE fault-free"]
    direction TB
    PA_1["TASK_START"]
    PA_2["CARD_VALIDATED"]
    PA_3["CHARGE_DONE<br/>charges 1,337 EUR<br/>structurally correct<br/>no awareness of hallucination"]
    PA_4["SAVE_DONE"]
    PA_5["FINAL_ANSWER<br/>5 of 5 steps reached"]
    PA_1 --> PA_2 --> PA_3 --> PA_4 --> PA_5
  end

  RESULT(["RESULT<br/>Baseline: 9 EUR charged<br/>Fault run: 1,337 EUR charged<br/>Overcharge: +14,755.6%<br/>hop2_infection = null<br/>Tier 3 — Silent"])

  Hop1 --> PROP --> Hop2 --> RESULT

  style CA_2 fill:#ffcdd2,stroke:#c62828
  style PROP fill:#ffcdd2,stroke:#c62828
  style PA_3 fill:#fff9c4,stroke:#f57f17
  style RESULT fill:#fff3e0,stroke:#e65100
```

---

## 7. Cross-Agent Chain B — ProductCatalog → Recommendation

**Experiment:** ProductCatalogAgent injected with FM-2.2 (phantom product ID); RecommendationAgent runs baseline (NONE).  
**Finding:** Phantom product propagates silently — recommendation steps structurally identical to baseline but semantically corrupted (garbage-in, garbage-out).  
**Key metrics** (from `cross_agent_propagation.json`):

| Field | Value |
|---|---|
| `hop1_infection` | `CATALOG_DONE` |
| `baseline_product_ids` | `[PROD-001]` |
| `propagated_product_ids` | `[HALLUCINATED-001]` |
| `baseline_recs` | `[PROD-042, PROD-017, PROD-009]` |
| `propagated_recs` | `[PROD-042, PROD-017, PROD-009]` (structurally identical) |
| `hop2_infection` | `null` (no structural signal) |
| `hop2_steps_lost` | 0 of 3 |

```mermaid
flowchart LR
  subgraph Hop1 ["HOP 1 — ProductCatalogAgent  FM-2.2 injected"]
    direction TB
    PC_in(["Input:<br/>list catalog products"])
    PC_1["TASK_START"]
    PC_2["CATALOG_DONE<br/>INFECTION POINT<br/>hallucinated product: HALLUCINATED-001<br/>baseline: PROD-001"]
    PC_3["FINAL_ANSWER<br/>returns HALLUCINATED-001"]
    PC_in --> PC_1 --> PC_2 --> PC_3
  end

  PROP["SILENT PROPAGATION<br/>HALLUCINATED-001 passed as-is<br/>no LKW flag at boundary"]

  subgraph Hop2 ["HOP 2 — RecommendationAgent  NONE fault-free"]
    direction TB
    RA_1["TASK_START"]
    RA_2["RECOMMEND_DONE<br/>computes recs based on HALLUCINATED-001<br/>structurally correct — same steps as baseline"]
    RA_3["FINAL_ANSWER<br/>3 of 3 steps reached<br/>rec IDs: PROD-042, PROD-017, PROD-009"]
    RA_1 --> RA_2 --> RA_3
  end

  RESULT(["RESULT: Garbage-In Garbage-Out<br/>Baseline product: PROD-001<br/>Fault product: HALLUCINATED-001<br/>Rec step count identical to baseline<br/>hop2_infection = null<br/>Tier 2 — semantically corrupted"])

  Hop1 --> PROP --> Hop2 --> RESULT

  style PC_2 fill:#ffcdd2,stroke:#c62828
  style PROP fill:#ffcdd2,stroke:#c62828
  style RA_2 fill:#fff9c4,stroke:#f57f17
  style RESULT fill:#fff3e0,stroke:#e65100
```

---

## 8. HITL Tier Classification Decision Tree

**Purpose:** Shows how LKW checkpoint evidence maps to HITL tier assignments for automated intervention routing.  
**Data source:** `src/results/hitl_classification_report.json`

```mermaid
flowchart TD
  A(["LKW Trace + Result<br/>for one fault-mode run"])
  A --> B{{"Steps missing<br/>from LKW trace?"}}

  B -->|"Yes — expected checkpoints absent"| T1
  B -->|"No — all checkpoints logged"| C

  C{{"New operational flags<br/>raised in checkpoint data?"}}
  C -->|"Yes — e.g. amount_tampered<br/>validation_bypassed"| T2
  C -->|"No flags"| D

  D{{"Data semantics corrupted?<br/>e.g. hallucinated=True<br/>phantom ID returned"}}
  D -->|"Yes — silent value corruption"| T3
  D -->|"No — baseline-identical"| T0

  T1["TIER 1 — Structural<br/>Auto-detectable via step-count diff<br/>HITL required for severity assessment<br/>---<br/>PaymentAgent FM-3.1:<br/>steps lost: CARD_VALIDATED, CHARGE_DONE, SAVE_DONE<br/>ShippingAgent FM-3.1:<br/>step lost: CARRIER_DONE"]

  T2["TIER 2 — Flag-Detectable<br/>LKW flag monitor triggers HITL alert<br/>Semantic check confirms severity<br/>---<br/>PaymentAgent FM-1.2: flag=validation_bypassed<br/>PaymentAgent FM-2.5: flag=amount_tampered<br/>Chain B hop2: phantom product accepted"]

  T3["TIER 3 — Silent<br/>No structural or flag signal<br/>Full semantic human review required<br/>Hardest class to catch automatically<br/>---<br/>CurrencyAgent FM-2.2: hallucinated rate<br/>14,755.6% overcharge in Chain A<br/>ProductCatalogAgent FM-2.2: HALLUCINATED-001"]

  T0["TIER 0 — Baseline<br/>No fault injected — healthy run<br/>All steps reached, values correct"]

  style T1 fill:#ffcdd2,stroke:#c62828
  style T2 fill:#ffe0b2,stroke:#e65100
  style T3 fill:#ef9a9a,stroke:#b71c1c
  style T0 fill:#c8e6c9,stroke:#2e7d32
```

**Tier assignment summary** (PaymentAgent sample from `hitl_classification_report.json`):

| Fault Mode | Tier | Label | Auto-Detect | HITL Required | Infection Point |
|---|---|---|---|---|---|
| NONE | 0 | BASELINE | yes | no | — |
| FM_3_1 | 1 | Structural | yes | yes | `FINAL_ANSWER` |
| FM_1_2 | 2 | Flag-Detectable | no | yes | `CARD_VALIDATED` |
| FM_2_5 | 2 | Flag-Detectable | no | yes | `CARD_VALIDATED` |
| FM_2_2 | 3 | Silent | no | yes | `CHARGE_DONE` |

---

## Summary Findings Table

| Diagram | Key Finding | Numeric Evidence | Data Source |
|---|---|---|---|
| 1. System Architecture | 7 agentic microservices, single shared LLM, gRPC backbone | 7 agents, 7 services | `src/protos/demo.proto` |
| 2. LKW/RIP Methodology | RIP triad → 4 result classes → 3 HITL tiers | 11 ShippingService runs, 6×9 deterministic runs | `src/hitl_detector.py` |
| 3. FM-3.1 Trace | TRUE POSITIVE: early catch, infection at QUOTE_DONE | propagation_depth=1, 44,799 ms | `lkw_rip_results.json` |
| 4. FM-1.2 Trace | PARTIAL TP: all steps logged, infection at CARRIER_DONE | propagation_depth=0, 9,678 ms | `lkw_rip_results.json` |
| 5. BL_COMPLIANCE Timeout | INCONCLUSIVE: LLM never returned FINAL_ANSWER | 577,682 ms timeout | `lkw_rip_results.json` |
| 6. Chain A (Currency→Payment) | Silent 14,755.6% financial overcharge across agent boundary | 9 EUR → 1,337 EUR overcharge | `cross_agent_propagation.json` |
| 7. Chain B (Product→Rec) | Silent phantom product propagation, garbage-in/garbage-out | HALLUCINATED-001 passed undetected | `cross_agent_propagation.json` |
| 8. HITL Tier Decision Tree | Tier 1 (structural/auto) → Tier 2 (flag) → Tier 3 (silent/semantic) | 5 tiers mapped per agent | `hitl_classification_report.json` |

---

## How to Use These Diagrams

### Share via GitHub permalink
This file renders natively on GitHub with all Mermaid diagrams.  
**Share this link with your professor:**
```
https://github.com/<org>/LLM-MAS/blob/main/src/results/diagrams_report.md
```
(Replace `<org>` with the actual GitHub org/username for the public remote.)

### Overleaf / LaTeX
TikZ versions of Diagrams 1 and 6+7 are embedded directly in `paper_updated.tex`:
- `fig:architecture` — System Architecture (Section II)
- `fig:cross-agent` — Cross-Agent Chain A + B (Section VII)

Compile `paper_updated.tex` in Overleaf to get publication-ready PDF figures.

### draw.io / diagrams.net
1. Open [app.diagrams.net](https://app.diagrams.net)
2. **Extras → Edit Diagram** → paste any Mermaid block above
3. Export as PNG or SVG for slides and reports

### Mermaid Live Editor
1. Open [mermaid.live](https://mermaid.live)
2. Paste any Mermaid block → export as SVG
3. Upload SVG to Overleaf → `\includegraphics[width=\columnwidth]{filename.svg}`
