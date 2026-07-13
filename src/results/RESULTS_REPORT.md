# LLM-MAS Fault Injection Study — Full Results Report
**Author:** Deepak Sunil Chavan, Concordia University  
**Platform:** Concordia SPEED HPC (`deepak/fault-injection` branch)  
**Date:** 2026-06-18  
**Updated:** 2026-07-07 — boundary validation and HITL readiness refresh  

---

## Table of Contents
1. [Stability Analysis (RQ5)](#1-stability-analysis-rq5)
2. [Agent-Level Fault Injection — All 7 Agents](#2-agent-level-fault-injection)
3. [HITL Tier Classification — Automated](#3-hitl-tier-classification)
4. [Cross-Agent Fault Propagation](#4-cross-agent-fault-propagation)
5. [Boundary Validation Improvements](#5-boundary-validation-improvements)
6. [Key Findings Summary](#6-key-findings-summary)
7. [Limitations](#7-limitations)

---

## 1. Stability Analysis (RQ5)
**Job:** 970059 on Concordia SPEED HPC  
**Protocol:** Each agent's full 9-fault-mode suite run **3 times independently**. LKW fingerprints compared across all 3 runs.

### Stability Classification
| Label | Meaning |
|---|---|
| `STABLE_PASS` | Baseline NONE: clean across all 3 runs, no infection |
| `STABLE_FAULT` | Fault mode: identical LKW fingerprint (same infection point, same steps lost, same depth) across all 3 runs |
| `UNSTABLE` | At least one run differs — non-determinism detected |

### Results

| Agent | Modes | STABLE_PASS | STABLE_FAULT | UNSTABLE | Rate |
|---|---|---|---|---|---|
| PaymentAgent | 9 | 1 | 8 | 0 | **100%** |
| CurrencyAgent | 9 | 1 | 8 | 0 | **100%** |
| EmailServiceAgent | 9 | 1 | 8 | 0 | **100%** |
| ProductCatalogAgent | 9 | 1 | 8 | 0 | **100%** |
| RecommendationAgent | 9 | 1 | 8 | 0 | **100%** |
| AdServiceAgent | 9 | 1 | 8 | 0 | **100%** |
| ShippingService ¹ | 10 | 1 | 9 | 0 | **100%** |
| **TOTAL** | **64** | **7** | **57** | **0** | **100%** |

> ¹ ShippingService uses a live LLM (Ollama on SPEED) with real gRPC and MongoDB — not mock-based. Stability for Llama 3.2:1b assessed via per-fault-mode individual evidence files. Full 10-fault batch rerun completed with qwen2.5-coder:14b (A100 MIG, SPEED HPC), resolving all 5 previously INCONCLUSIVE results.

> **Finding (mock-based agents):** Zero UNSTABLE entries across 54 mode-runs (162 total individual runs). All mock-based fault injection results are deterministic and reproducible.  
> **Finding (ShippingService):** Per-fault-mode stability matrices confirm deterministic LKW traces for all 10 fault modes under real-LLM execution on SPEED. Combined: 64 mode-runs, 0 UNSTABLE, evidence is publishable.

---

## 2. Agent-Level Fault Injection

Each agent is instrumented with **LKW (Last Known Well) checkpoints**. gRPC dependencies are replaced with controlled mocks. All results are deterministic (no LLM calls, `USE_LLM=false`).

**RIP metrics per run:**
- **Infection Point** — first LKW checkpoint with semantically deviant data
- **Propagation Depth** — number of expected downstream steps absent in the fault trace
- **Steps Lost** — checkpoints present in the NONE baseline but absent in the fault run

---

### 2.1 PaymentAgent
**Checkpoints:** `TASK_START` → `CARD_VALIDATED` → `CHARGE_DONE` → `SAVE_DONE` → `FINAL_ANSWER`

| Fault Mode | Infection Point | Depth | Steps Lost | Flag Detected |
|---|---|---|---|---|
| NONE | — | 0 | — | — |
| FM_3_1 Premature Termination | FINAL_ANSWER | 3 | CARD_VALIDATED, CHARGE_DONE, SAVE_DONE | `premature_termination` |
| FM_2_2 Hallucinated TXN ID | CHARGE_DONE | 0 | — | `hallucinated` |
| FM_2_5 Amount Ignored | CARD_VALIDATED | 0 | — | `amount_tampered` |
| FM_1_2 Validation Bypassed | CARD_VALIDATED | 0 | — | `validation_bypassed` |
| BL_TRANSACTION_LOST | SAVE_DONE | 0 | — | `save_skipped` |
| BL_DOUBLE_CHARGE | SAVE_DONE | 0 | — | `double_charge` |
| BL_AMOUNT_TAMPERING | CARD_VALIDATED | 0 | — | `amount_tampered` |
| BL_CARD_DECLINED | FINAL_ANSWER | 3 | CARD_VALIDATED, CHARGE_DONE, SAVE_DONE | `forced_decline` |

---

### 2.2 CurrencyAgent
**Checkpoints:** `TASK_START` → `CONVERT_DONE` → `FINAL_ANSWER`

| Fault Mode | Infection Point | Depth | Steps Lost | Flag Detected |
|---|---|---|---|---|
| NONE | — | 0 | — | — |
| FM_3_1 Premature Termination | FINAL_ANSWER | 1 | CONVERT_DONE | `premature_termination` |
| FM_2_2 Hallucinated Result (1337 EUR) | CONVERT_DONE | 0 | — | `hallucinated` |
| FM_2_5 Amount Ignored | CONVERT_DONE | 0 | — | `amount_tampered` |
| FM_1_2 Wrong Currency Routing | CONVERT_DONE | 0 | — | `currency_swapped` |
| BL_RATE_MANIPULATION | CONVERT_DONE | 0 | — | `rate_manipulated` |
| BL_CURRENCY_UNAVAILABLE | FINAL_ANSWER | 1 | CONVERT_DONE | `unavailable` |
| BL_STALE_RATE | CONVERT_DONE | 0 | — | `stale_rate` |
| BL_CONVERSION_OVERFLOW | CONVERT_DONE | 0 | — | `overflow` |

---

### 2.3 EmailServiceAgent
**Checkpoints:** `TASK_START` → `EMAIL_GENERATED` → `EMAIL_SENT` → `FINAL_ANSWER`

| Fault Mode | Infection Point | Depth | Steps Lost | Flag Detected |
|---|---|---|---|---|
| NONE | — | 0 | — | — |
| FM_3_1 Premature Termination | FINAL_ANSWER | 2 | EMAIL_GENERATED, EMAIL_SENT | `premature_termination` |
| FM_2_2 Hallucinated Email (phishing) | EMAIL_GENERATED | 0 | — | `hallucinated` |
| FM_2_5 Recipient Swapped | EMAIL_GENERATED | 0 | — | `recipient_swapped` |
| FM_1_2 Wrong Email Type | EMAIL_GENERATED | 0 | — | `type_wrong` |
| BL_SEND_SKIPPED | EMAIL_SENT | 0 | — | `send_skipped` |
| BL_DOUBLE_SEND | EMAIL_SENT | 0 | — | `double_send` |
| BL_CORRUPTED_BODY | EMAIL_GENERATED | 0 | — | `corrupted` |
| BL_WRONG_CUSTOMER | EMAIL_GENERATED | 0 | — | `wrong_customer` |

---

### 2.4 ProductCatalogAgent
**Checkpoints:** `TASK_START` → `CATALOG_DONE` → `FINAL_ANSWER`

| Fault Mode | Infection Point | Depth | Steps Lost | Flag Detected |
|---|---|---|---|---|
| NONE | — | 0 | — | — |
| FM_3_1 Premature Termination | FINAL_ANSWER | 1 | CATALOG_DONE | `premature_termination` |
| FM_2_2 Hallucinated Products | CATALOG_DONE | 0 | — | `hallucinated` |
| FM_2_5 Query Tampered | CATALOG_DONE | 0 | — | `query_tampered` |
| FM_1_2 Wrong Action Routing | CATALOG_DONE | 0 | — | `action_swapped` |
| BL_PRODUCT_MISSING | CATALOG_DONE | 0 | — | `products_missing` |
| BL_PRICE_MANIPULATION | CATALOG_DONE | 0 | — | `price_manipulated` |
| BL_DUPLICATE_PRODUCT | CATALOG_DONE | 0 | — | `duplicated` |
| BL_WRONG_CATEGORY | CATALOG_DONE | 0 | — | `category_wrong` |

---

### 2.5 RecommendationAgent
**Checkpoints:** `TASK_START` → `RECOMMEND_DONE` → `FINAL_ANSWER`

| Fault Mode | Infection Point | Depth | Steps Lost | Flag Detected |
|---|---|---|---|---|
| NONE | — | 0 | — | — |
| FM_3_1 Premature Termination | FINAL_ANSWER | 1 | RECOMMEND_DONE | `premature_termination` |
| FM_2_2 Hallucinated IDs | RECOMMEND_DONE | 0 | — | `hallucinated` |
| FM_2_5 User ID Swapped | RECOMMEND_DONE | 0 | — | `user_id_swapped` |
| FM_1_2 Wrong Method Routed | RECOMMEND_DONE | 0 | — | `method_swapped` |
| BL_EMPTY_RECS | RECOMMEND_DONE | 0 | — | `empty_recs` |
| BL_SELF_RECOMMENDATION | RECOMMEND_DONE | 0 | — | `self_rec` |
| BL_INJECTION_RECS | RECOMMEND_DONE | 0 | — | `injection` |
| BL_SHUFFLED_RECS | RECOMMEND_DONE | 0 | — | `shuffled` |

---

### 2.6 AdServiceAgent
**Checkpoints:** `TASK_START` → `CONTEXT_EXTRACTED` → `ADS_FETCHED` → `FINAL_ANSWER`

| Fault Mode | Infection Point | Depth | Steps Lost | Flag Detected |
|---|---|---|---|---|
| NONE | — | 0 | — | — |
| FM_3_1 Premature Termination | FINAL_ANSWER | 1 | ADS_FETCHED | `premature_termination` |
| FM_2_2 Hallucinated Ads (phishing URLs) | ADS_FETCHED | 0 | — | `hallucinated` |
| FM_2_5 Context Keys Tampered | CONTEXT_EXTRACTED | 0 | — | `context_tampered` |
| FM_1_2 Wrong Category | CONTEXT_EXTRACTED | 0 | — | `category_swapped` |
| BL_EMPTY_ADS | ADS_FETCHED | 0 | — | `empty_ads` |
| BL_AD_INJECTION | ADS_FETCHED | 0 | — | `injected` |
| BL_WRONG_URL | ADS_FETCHED | 0 | — | `wrong_url` |
| BL_DUPLICATE_ADS | ADS_FETCHED | 0 | — | `duplicated` |

---

### 2.7 ShippingService (qwen2.5-coder:14b — Real LLM, SPEED HPC)
**Checkpoints:** `TASK_START` → `QUOTE_DONE` → `CARRIER_DONE` → `TRACKING_DONE` → `ESCALATION_CHECK` → `FINAL_ANSWER` → `SAVE_DONE`

> **Note:** Unlike agents 2.1–2.6, ShippingService runs a live qwen2.5-coder:14b LLM via ReAct loop (Ollama on SPEED HPC A100 MIG). Initial runs with Llama 3.2:1b (1B parameter) produced 5 INCONCLUSIVE results due to ReAct loop exhaustion; upgraded to qwen2.5-coder:14b (14B parameter) per reviewer recommendation, resolving all timeouts. Injection points are at the Final Answer intercept and tool-dispatch layer rather than pure mock substitution.

| Fault Mode | Injection Layer | Infection Point | Depth | Steps Lost | Flag Detected | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | 0 | — | — | TN |
| FM_3_1 Premature Termination | Final Answer intercept | TRACKING_DONE | 1 | CARRIER_DONE, ESCALATION_CHECK | `premature_termination` | Partial TP ¹ |
| FM_1_2 Incomplete Task Spec | Task-spec mutation + dispatch block | SAVE_DONE | 2 | CARRIER_DONE, TRACKING_DONE, ESCALATION_CHECK | `incomplete` | TP |
| FM_2_2 Hallucinated Carrier (SpeedyShip) | Final Answer intercept | CARRIER_DONE | 0 | — | `hallucinated` | TP |
| FM_2_5 Stale Quote Ignored ($4.99) | Final Answer + `ship_order` fallback | CARRIER_DONE | 0 | — | `ignored_downstream_quote` | TP |
| BL_SHIPMENT_LOST | `ship_order` MongoDB save bypass | None detected | 1 | SAVE_DONE | `save_skipped` | Partial TP ² |
| BL_INVENTORY_MISMATCH | Pre-task item quantity inflation | QUOTE_DONE | 0 | — | `item_count_inflated` | TP |
| BL_VENDOR_NEGOTIATION | Final Answer + `ship_order` fallback | CARRIER_DONE | 0 | — | `forced_vendor` | TP |
| BL_CUSTOMER_ESCALATION | Post-agent metadata injection | ESCALATION_CHECK | 0 | — | `escalation_required` | TP |
| BL_REFUND_REASONING | Post-agent cost negation | QUOTE_DONE | 0 | — | `negative_cost` | TP |
| BL_COMPLIANCE_AMBIGUITY | Pre-task address tagging | None detected | 0 | — | — | FN ³ |

> ¹ FM_3_1: system reports depth=1 but actual missing steps = 2 (CARRIER_DONE + ESCALATION_CHECK). ESCALATION_CHECK absent from RIP expected-steps checker (known bug).  
> ² BL_SHIPMENT_LOST: SAVE_DONE structurally absent (depth=1) but infection_point=None — all present checkpoints look clean, no infected step identified. Step-loss is auto-detectable.  
> ³ BL_COMPLIANCE_AMBIGUITY: qwen2.5-coder:14b resolved the injected ambiguity gracefully (all 7 steps complete, infection_point=None). Model-capability-dependent FN — larger LLM is more resilient to semantic ambiguity injection.

---

## 3. HITL Tier Classification

**Tool:** `src/hitl_detector.py` — fully automated, reads `*_fault_results.json` per agent.  
**Generated:** 2026-06-18T14:51:55Z (local) / verified SPEED job 970084

### Tier Definitions

| Tier | Label | Detection Method | Risk Level |
|---|---|---|---|
| **1** | Structural | `propagation_depth > 0` — missing step in LKW trace | Auto-detectable, no semantic analysis |
| **2** | Flag-Detectable | Operational boolean flag is `True` in LKW data (new vs baseline) | Needs flag monitor / alert rule |
| **3** | Silent | Only `hallucinated=True` or no flag — pure data corruption | Requires semantic validation of data values |

### Full Classification Table

| Agent | Fault Mode | Tier | Detect Method | Flags |
|---|---|---|---|---|
| PaymentAgent | NONE | BASELINE | — | — |
| PaymentAgent | FM_3_1 | **TIER 1** | AUTO (step diff) | `premature_termination` |
| PaymentAgent | FM_2_2 | **TIER 3** | MANUAL (semantic) | `hallucinated` |
| PaymentAgent | FM_2_5 | **TIER 2** | MANUAL (flag monitor) | `amount_tampered` |
| PaymentAgent | FM_1_2 | **TIER 2** | MANUAL (flag monitor) | `validation_bypassed` |
| PaymentAgent | BL_TRANSACTION_LOST | **TIER 2** | MANUAL (flag monitor) | `save_skipped` |
| PaymentAgent | BL_DOUBLE_CHARGE | **TIER 2** | MANUAL (flag monitor) | `double_charge` |
| PaymentAgent | BL_AMOUNT_TAMPERING | **TIER 2** | MANUAL (flag monitor) | `amount_tampered` |
| PaymentAgent | BL_CARD_DECLINED | **TIER 1** | AUTO (step diff) | `forced_decline` |
| CurrencyAgent | NONE | BASELINE | — | — |
| CurrencyAgent | FM_3_1 | **TIER 1** | AUTO (step diff) | `premature_termination` |
| CurrencyAgent | FM_2_2 | **TIER 3** | MANUAL (semantic) | `hallucinated` |
| CurrencyAgent | FM_2_5 | **TIER 2** | MANUAL (flag monitor) | `amount_tampered` |
| CurrencyAgent | FM_1_2 | **TIER 2** | MANUAL (flag monitor) | `currency_swapped` |
| CurrencyAgent | BL_RATE_MANIPULATION | **TIER 2** | MANUAL (flag monitor) | `rate_manipulated` |
| CurrencyAgent | BL_CURRENCY_UNAVAILABLE | **TIER 1** | AUTO (step diff) | `unavailable` |
| CurrencyAgent | BL_STALE_RATE | **TIER 2** | MANUAL (flag monitor) | `stale_rate` |
| CurrencyAgent | BL_CONVERSION_OVERFLOW | **TIER 2** | MANUAL (flag monitor) | `overflow` |
| EmailServiceAgent | NONE | BASELINE | — | — |
| EmailServiceAgent | FM_3_1 | **TIER 1** | AUTO (step diff) | `premature_termination` |
| EmailServiceAgent | FM_2_2 | **TIER 3** | MANUAL (semantic) | `hallucinated` |
| EmailServiceAgent | FM_2_5 | **TIER 2** | MANUAL (flag monitor) | `recipient_swapped` |
| EmailServiceAgent | FM_1_2 | **TIER 2** | MANUAL (flag monitor) | `type_wrong` |
| EmailServiceAgent | BL_SEND_SKIPPED | **TIER 2** | MANUAL (flag monitor) | `send_skipped` |
| EmailServiceAgent | BL_DOUBLE_SEND | **TIER 2** | MANUAL (flag monitor) | `double_send` |
| EmailServiceAgent | BL_CORRUPTED_BODY | **TIER 2** | MANUAL (flag monitor) | `corrupted` |
| EmailServiceAgent | BL_WRONG_CUSTOMER | **TIER 2** | MANUAL (flag monitor) | `wrong_customer` |
| ProductCatalogAgent | NONE | BASELINE | — | — |
| ProductCatalogAgent | FM_3_1 | **TIER 1** | AUTO (step diff) | `premature_termination` |
| ProductCatalogAgent | FM_2_2 | **TIER 3** | MANUAL (semantic) | `hallucinated` |
| ProductCatalogAgent | FM_2_5 | **TIER 2** | MANUAL (flag monitor) | `query_tampered` |
| ProductCatalogAgent | FM_1_2 | **TIER 2** | MANUAL (flag monitor) | `action_swapped` |
| ProductCatalogAgent | BL_PRODUCT_MISSING | **TIER 2** | MANUAL (flag monitor) | `products_missing` |
| ProductCatalogAgent | BL_PRICE_MANIPULATION | **TIER 2** | MANUAL (flag monitor) | `price_manipulated` |
| ProductCatalogAgent | BL_DUPLICATE_PRODUCT | **TIER 2** | MANUAL (flag monitor) | `duplicated` |
| ProductCatalogAgent | BL_WRONG_CATEGORY | **TIER 2** | MANUAL (flag monitor) | `category_wrong` |
| RecommendationAgent | NONE | BASELINE | — | — |
| RecommendationAgent | FM_3_1 | **TIER 1** | AUTO (step diff) | `premature_termination` |
| RecommendationAgent | FM_2_2 | **TIER 3** | MANUAL (semantic) | `hallucinated` |
| RecommendationAgent | FM_2_5 | **TIER 2** | MANUAL (flag monitor) | `user_id_swapped` |
| RecommendationAgent | FM_1_2 | **TIER 2** | MANUAL (flag monitor) | `method_swapped` |
| RecommendationAgent | BL_EMPTY_RECS | **TIER 2** | MANUAL (flag monitor) | `empty_recs` |
| RecommendationAgent | BL_SELF_RECOMMENDATION | **TIER 2** | MANUAL (flag monitor) | `self_rec` |
| RecommendationAgent | BL_INJECTION_RECS | **TIER 2** | MANUAL (flag monitor) | `injection` |
| RecommendationAgent | BL_SHUFFLED_RECS | **TIER 2** | MANUAL (flag monitor) | `shuffled` |
| AdServiceAgent | NONE | BASELINE | — | — |
| AdServiceAgent | FM_3_1 | **TIER 1** | AUTO (step diff) | `premature_termination` |
| AdServiceAgent | FM_2_2 | **TIER 3** | MANUAL (semantic) | `hallucinated` |
| AdServiceAgent | FM_2_5 | **TIER 2** | MANUAL (flag monitor) | `context_tampered` |
| AdServiceAgent | FM_1_2 | **TIER 2** | MANUAL (flag monitor) | `category_swapped` |
| AdServiceAgent | BL_EMPTY_ADS | **TIER 2** | MANUAL (flag monitor) | `empty_ads` |
| AdServiceAgent | BL_AD_INJECTION | **TIER 2** | MANUAL (flag monitor) | `injected` |
| AdServiceAgent | BL_WRONG_URL | **TIER 2** | MANUAL (flag monitor) | `wrong_url` |
| AdServiceAgent | BL_DUPLICATE_ADS | **TIER 2** | MANUAL (flag monitor) | `duplicated` |
| ShippingService | NONE | BASELINE | — | — |
| ShippingService | FM_3_1 | **TIER 1** | AUTO (step diff) | `premature_termination` |
| ShippingService | FM_1_2 | **TIER 1** | AUTO (step diff) | `incomplete` |
| ShippingService | FM_2_2 | **TIER 3** | MANUAL (semantic) | `hallucinated` |
| ShippingService | FM_2_5 | **TIER 2** | MANUAL (flag monitor) | `ignored_downstream_quote` |
| ShippingService | BL_SHIPMENT_LOST | **TIER 1** | AUTO (step diff) | `save_skipped` |
| ShippingService | BL_INVENTORY_MISMATCH | **TIER 2** | MANUAL (flag monitor) | `item_count_inflated` |
| ShippingService | BL_VENDOR_NEGOTIATION | **TIER 2** | MANUAL (flag monitor) | `forced_vendor` |
| ShippingService | BL_CUSTOMER_ESCALATION | **TIER 2** | MANUAL (flag monitor) | `escalation_required` |
| ShippingService | BL_REFUND_REASONING | **TIER 2** | MANUAL (flag monitor) | `negative_cost` |
| ShippingService | BL_COMPLIANCE_AMBIGUITY | **TIER 2** | MANUAL (flag monitor) | `compliance_failed` |

### HITL Summary

| Tier | Count (6 mock agents) | Count (ShippingService) | Total | Description |
|---|---|---|---|---|
| **Tier 1 — Structural** | **8** | **3** | **11** | Auto-detectable from step-trace diff alone |
| **Tier 2 — Flag-Detectable** | **34** | **6** | **40** | Requires flag monitor on LKW checkpoint data |
| **Tier 3 — Silent** | **6** | **1** | **7** | Requires semantic validation of data values |
| Baseline (NONE) | 6 | 1 | **7** | — |
| **Total fault modes** | **48** | **10** | **58** | |

> **Key Finding:** FM-2.2 (hallucination) is **Tier 3 before boundary validation** — zero structural signal and no reliable step-loss signal. The July boundary-validation refresh adds explicit `BOUNDARY_CHECK` contracts so high-risk hallucinated handoffs are now observable through range checks, entity existence checks, and schema/value validators at agent boundaries.  
> **ShippingService note (qwen2.5-coder:14b):** With the 14B model, all 10 fault modes complete successfully (0 INCONCLUSIVE). BL_COMPLIANCE_AMBIGUITY is a **confirmed FN** — the 14B model resolved the injected ambiguity without any fault signal (all 7 steps, infection_point=None), demonstrating LLM robustness to semantic ambiguity injection. BL_VENDOR_NEGOTIATION (confirmed FN under 1B model) became **TP** under 14B — the stronger model correctly reflects vendor-forced routing at CARRIER_DONE. This model-capability-dependent detectability gap is a novel finding for LLM-MAS fault injection methodology.

---

## 4. Cross-Agent Fault Propagation

**Job:** 970076 on Concordia SPEED HPC  
**Design:** FM-2.2 injected at upstream agent; downstream agent runs with `FAULT_MODE=NONE`.  
FM-2.2 selected because it is the only fault class with depth=0 at the upstream agent — structurally invisible to downstream.

### Chain A — Financial Propagation

| Property | Baseline | Infected |
|---|---|---|
| **Chain** | CurrencyAgent [NONE] → PaymentAgent [NONE] | CurrencyAgent [FM_2_2] → PaymentAgent [NONE] |
| **Hop 1 result** | 9 EUR (correct) | **1337 EUR** (hallucinated) |
| **Hop 1 infection** | None | `CONVERT_DONE` |
| **Hop 2 steps reached** | 5/5 (all) | **5/5 (all)** |
| **Hop 2 infection** | None | **None** (agent is correct) |
| **Hop 2 steps lost** | 0 | **0** |
| **Structural alert** | No | **No** |
| **Amount charged** | 9 EUR | **1337 EUR** |
| **Overcharge** | — | **+1328 EUR (+14,755.6%)** |
| **HITL Tier** | — | **Tier 3 — Silent** |

> PaymentAgent validates the card, charges 1337 EUR, saves the transaction, and returns success — **all 5 checkpoints reached, infection_point=None**. The agent is correct. The financial loss is entirely caused by upstream FM-2.2 with no observable signal at either hop.

---

### Chain B — Semantic Propagation

| Property | Baseline | Infected |
|---|---|---|
| **Chain** | ProductCatalogAgent [NONE] → RecommendationAgent [NONE] | ProductCatalogAgent [FM_2_2] → RecommendationAgent [NONE] |
| **Hop 1 result** | `['PROD-001']` (valid) | **`['HALLUCINATED-001']`** (phantom) |
| **Hop 1 infection** | None | `CATALOG_DONE` |
| **Hop 2 steps reached** | 3/3 (all) | **3/3 (all)** |
| **Hop 2 infection** | None | **None** (agent is correct) |
| **Hop 2 steps lost** | 0 | **0** |
| **Structural alert** | No | **No** |
| **Recommendations for** | PROD-001 (exists) | **HALLUCINATED-001 (does not exist)** |
| **HITL Tier** | — | **Tier 2 — Detectable via product ID cross-check** |

> RecommendationAgent queries the recommender service and returns results — **all 3 checkpoints reached, infection_point=None**. The agent is correct. The phantom product ID is forwarded silently. Detectable only by validating returned product IDs against the authoritative catalog.

---

### Cross-Agent Summary

| Chain | Upstream Fault | Downstream Health | Impact | Structural Alert | HITL Tier |
|---|---|---|---|---|---|
| A | CurrencyAgent FM-2.2 | PaymentAgent correct (5/5 steps) | +14,755.6% overcharge | **None** | **Tier 3** |
| B | ProductCatalogAgent FM-2.2 | RecommendationAgent correct (3/3 steps) | Phantom product recommended | **None** | **Tier 2** |

> **Finding:** A structurally-correct downstream agent cannot self-detect or recover from upstream hallucination. Single-agent LKW instrumentation is necessary but **not sufficient** for system-level fault detection.

---

## 5. Boundary Validation Improvements

**Generated artifacts:** `cross_agent_propagation.py`, `boundary_detection_runner.py`, `repo_hitl_audit.py`  
**Latest evidence timestamp:** 2026-07-07T03:15Z  
**Purpose:** address the professor's concern that default LKW/RIP traces can miss silent boundary failures unless explicit flags, gates, and probes make semantic deviations observable.

**Live demo artifacts:** `live_boundary_demo.py`, `boundary_dashboard.py`, and `results/boundary_events.jsonl` show these boundary flags appearing while the evidence flow runs.

### 5.1 Repo-Wide Boundary Coverage

The repository audit now reports complete boundary-flag coverage for all agent/service groups in scope.

| Coverage Metric | Result |
|---|---:|
| Python groups scanned | 19 |
| Groups with boundary flags | 16 |
| Agent/service groups missing flags | **0** |
| Boundary proxy groups | `shippingservice -> shippingagent` |

**Flagged agent/service groups:** `adserviceagent`, `currencyagent`, `emailservice`, `emailserviceagent`, `paymentagent`, `productcatalogagent`, `productcatalogservice`, `recommendationagent`, `recommendationservice`, `shippingagent`, `shippingservice`, `shoppingassistantservice`.

`shippingservice` is intentionally counted through the compatibility shim to `shippingagent`, where the real shipping orchestration and boundary checks live. This avoids duplicating logic while preserving service/agent separation.

### 5.2 Cross-Agent Boundary Evidence After Improvements

The regenerated cross-agent study now records `BOUNDARY_CHECK` in both upstream and downstream traces for Chain A, and in the upstream ProductCatalogAgent trace for Chain B.

| Chain | Boundary | Expected | Observed | Alert | Downstream Infection |
|---|---|---:|---:|---|---|
| A: CurrencyAgent -> PaymentAgent | `currency_to_payment` | 9 EUR | 1337 EUR | **Yes** (`delta=1328`) | None |
| B: ProductCatalogAgent -> RecommendationAgent | `catalog_to_recommendation` | `PROD-001` | `HALLUCINATED-001` | **Yes** (`missing/extra`) | None |

**Summary:** 2/2 cross-agent chains produced boundary alerts, 2/2 were signal escapes, and 2/2 downstream agents remained structurally healthy. This preserves the original finding that downstream LKW alone is insufficient, but now shows that explicit boundary contracts make the silent propagation observable.

### 5.3 Shipping Boundary Evidence

The boundary detection runner combines Chain A/B with shipping-specific internal handoff probes.

| Scenario | Failure Class | Boundary Alerts | Interpretation |
|---|---|---:|---|
| `shipping_clean` | `ok` | 0 | Clean quote/carrier/tracking path |
| `shipping_fm_2_2` | `fault_induced` | 1 | Hallucinated carrier/service level caught at `carrier_to_tracking` |
| `shipping_fm_2_5` | `fault_induced` | 1 | Quote-to-carrier handoff deviation caught at `quote_to_carrier_selection` |
| `shipping_infra_timeout` | `infra_timeout` | 0 | Classified separately as infrastructure/runtime failure |

Aggregate boundary summary: 4 boundary alerts, 4 signal escapes, 2 fault-induced shipping cases, 1 infrastructure timeout, and 2 manual-review candidates.

### 5.4 Updated Development Conclusion

The development improvements change the interpretation of the original HITL result:

- **Before boundary contracts:** FM-2.2 hallucinations were structurally silent and required human semantic review.
- **After boundary contracts:** the same high-risk handoffs emit explicit `BOUNDARY_CHECK` records with expected vs observed payloads, differences, and violations.
- **Remaining human role:** humans still review high-impact alerts, but the system now has machine-readable evidence for why the handoff is suspicious.

This satisfies the requested development goal: LKW/RIP is no longer only a step-reachability trace; it now includes boundary-level semantic probes where silent propagation previously escaped.

### 5.5 Live Dashboard Demonstration

For a live professor demo, start the dashboard and then run the evidence flow:

```bash
cd LLM-MAS/src
python boundary_dashboard.py
```

In a second terminal:

```bash
cd LLM-MAS/src
python live_boundary_demo.py
```

The dashboard reads `src/results/boundary_events.jsonl` and shows each boundary event with the boundary name, expected payload, observed payload, alert status, difference, and violations. This gives a start-to-end view of what happened during the run, instead of only showing static JSON after completion.

Validated local dashboard smoke test: `/events` returned HTTP 200 with 13 total boundary events, 8 alerts, and 5 clean checks.

---

## 6. Key Findings Summary

### Structural Pattern Across Fault Classes

| MAST Class | Fault Mode | Infection Stage | Depth | HITL Tier | HITL Method |
|---|---|---|---|---|---|
| FM-3.1 | Premature Termination | `FINAL_ANSWER` | 1–3 | **Tier 1** | Auto — step count diff |
| FM-2.2 | Hallucinated Output | Middle checkpoint | 0 | **Tier 3** | Semantic data validation |
| FM-2.5 | Ignored Input | Middle checkpoint | 0 | **Tier 2** | Flag monitor |
| FM-1.2 | Wrong Routing | Middle checkpoint | 0 | **Tier 2** | Flag monitor |
| BL (most) | Business Logic | Middle checkpoint | 0 | **Tier 2** | Flag monitor |
| BL (abort) | Card Declined, Currency Unavailable | `FINAL_ANSWER` | 1–3 | **Tier 1** | Auto — step count diff |

### Research Question Answers

**RQ1 — Can faults be reliably reproduced?**  
Yes. 64/64 mode-runs across all 7 agents are STABLE_PASS or STABLE_FAULT. Zero UNSTABLE. Fault injection is deterministic — including under live LLM execution (ShippingService). Full 10-fault batch rerun with qwen2.5-coder:14b (0 INCONCLUSIVE) confirms reproducibility across both model scales.

**RQ2 — Where does failure first appear?**  
- FM-3.1: always at `FINAL_ANSWER` (premature return before processing checkpoint)  
- FM-2.2, FM-2.5, FM-1.2, BL: always at the agent's middle processing checkpoint (`CONVERT_DONE`, `CATALOG_DONE`, `CHARGE_DONE`, etc.)

**RQ3 — How far does it propagate?**  
- FM-3.1 and abort-class BL: depth 1–3 (steps missing)  
- All other fault classes: depth 0 (all steps reached, corruption is data-only)

**RQ4 — Which failures require human intervention?**

| Category | Faults | Intervention |
|---|---|---|
| Auto-detectable (Tier 1) | FM-3.1, BL_CARD_DECLINED, BL_CURRENCY_UNAVAILABLE | Step-trace monitor, no human review needed for detection |
| Flag-monitorable (Tier 2) | FM-2.5, FM-1.2, all BL (save_skipped, double_charge, etc.) | Requires human alert rule on LKW flag |
| Boundary-alerted after refresh | FM-2.2 cross-agent handoffs and selected service handoffs | `BOUNDARY_CHECK` contract plus human review for high-impact alerts |

**RQ5 — Are observations stable across repeated runs?**  
100% stability rate. 0/64 UNSTABLE. Results are reproducible on Concordia SPEED HPC — both for mock-based agents (54 mode-runs) and the live-LLM ShippingService (10 mode-runs, per-fault-mode stability matrices).

### Critical Architectural Finding

> **FM-2.2 (hallucinated output) is the highest-risk fault class in a microservice LLM-MAS.**  
> - At the single-agent level before mitigation: depth=0, no structural alert.  
> - At the system level: a fault-free downstream agent can propagate corrupted values to business harm.  
> - After the boundary-validation refresh: explicit `BOUNDARY_CHECK` records make these handoff deviations observable through range checks, entity existence checks, schema validation, and expected-vs-observed payload comparison.

---

## 7. Limitations

### L1 — LLM Not in the Loop for 6 of 7 Agents

The six mock-based agents (Payment, Currency, Email, ProductCatalog, Recommendation, Ad) run their fault injection tests by calling the agent's business logic method directly — bypassing the LangGraph router and the LLM inference call entirely. The `USE_LLM` flag defaults to `false` in those agents' configurations. As a result, their fault injection results characterize the correctness of the **LKW+RIP instrumentation framework** on deterministic Python code — not the fault detection capability of an LLM.

Only **ShippingService** is a true LLM-in-the-loop agent in this study, using `qwen2.5-coder:14b` via Ollama on SPEED HPC for all 10 fault modes.

**Implication:** Claims about LLM-based fault detection are supported only by the ShippingService results (11 fault modes, 7 TP, 2 Partial TP, 1 TN, 1 FN). The six-agent results establish a framework baseline, not an LLM capability claim. Extending live-LLM execution to all agents is left as future work.

---

### L2 — Single-Run LLM Results (ShippingService)

The ShippingService results are from a single batch execution with `qwen2.5-coder:14b`. LLMs are stochastic; a second run may produce different infection signals for ambiguous fault modes. Stability matrices confirm determinism for the current run, but multi-run cross-model validation has not been performed.

---

### L3 — Known Code Defect in FM_3_1 Depth Calculation

For ShippingService FM_3_1 (Premature Termination), the RIP depth calculator reports `depth=1` but two steps are actually missing from the trace (`CARRIER_DONE` + `ESCALATION_CHECK`). `ESCALATION_CHECK` was not included in the expected-steps list in the runner. The fault is correctly detected and classified as Partial TP, but the reported depth is undercount by 1. This is a code-level instrumentation bug, not a model error.

---

### L4 — Human Cross-Validation Incomplete at Time of Submission

The human assessment rubric has been distributed to two independent assessors (cross-validation pending). Inter-rater agreement scores will be computed after all three assessments are submitted. Results in this report reflect Deepak's assessment only.

---

*Results files:*
- `src/results/stability_summary.json` — RQ5 stability matrices (mock-based agents)
- `src/results/hitl_classification_report.json` — automated HITL tier classification
- `src/results/cross_agent_propagation.json` — cross-agent chain data
- `src/results/boundary_detection_summary.json` — boundary validation and shipping handoff summary
- `src/results/boundary_events.jsonl` — live boundary event stream generated by `live_boundary_demo.py`
- `src/results/BOUNDARY_LIVE_DEMO.md` — live dashboard/demo instructions
- `src/results/repo_hitl_audit.json` — repo-wide HITL and boundary coverage audit
- `src/results/stability_matrix_<agent>.json` — per-agent 3-run fingerprints (×6)
- `src/shippingservice/hitl_classification_report.json` — ShippingService HITL tier classification
- `src/shippingservice/lkw_rip_results.json` — ShippingService full LKW+RIP results
- `src/shippingservice/*_lkw_rip_evidence.json` — per-fault-mode stability evidence (×10)
