# LLM-MAS Fault Injection Study — Full Results Report
**Author:** Deepak Sunil Chavan, Concordia University  
**Platform:** Concordia SPEED HPC (`deepak/fault-injection` branch)  
**Date:** 2026-06-18  

---

## Table of Contents
1. [Stability Analysis (RQ5)](#1-stability-analysis-rq5)
2. [Agent-Level Fault Injection — All 6 Agents](#2-agent-level-fault-injection)
3. [HITL Tier Classification — Automated](#3-hitl-tier-classification)
4. [Cross-Agent Fault Propagation](#4-cross-agent-fault-propagation)
5. [Key Findings Summary](#5-key-findings-summary)

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
| **TOTAL** | **54** | **6** | **48** | **0** | **100%** |

> **Finding:** Zero UNSTABLE entries across 54 mode-runs (162 total individual runs). All fault injection results are deterministic and reproducible — evidence is publishable.

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

### HITL Summary

| Tier | Count | Description |
|---|---|---|
| **Tier 1 — Structural** | **8** | Auto-detectable from step-trace diff alone |
| **Tier 2 — Flag-Detectable** | **34** | Requires flag monitor on LKW checkpoint data |
| **Tier 3 — Silent** | **6** | Requires semantic validation of data values |
| Baseline (NONE) | 6 | — |
| **Total fault modes** | **48** | |

> **Key Finding:** FM-2.2 (hallucination) is **Tier 3 across all 6 agents** — zero structural signal, zero operational flag. Detection requires inter-agent output validation contracts (e.g. range checks, entity existence validation) at every agent boundary.

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

## 5. Key Findings Summary

### Structural Pattern Across All 6 Agents

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
Yes. 54/54 mode-runs are STABLE_PASS or STABLE_FAULT. Zero UNSTABLE. Fault injection is deterministic.

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
| Silently absorbed (Tier 3) | FM-2.2 in all 6 agents | **Requires inter-agent output validation contracts** |

**RQ5 — Are observations stable across repeated runs?**  
100% stability rate. 0/54 UNSTABLE. Results are reproducible on Concordia SPEED HPC.

### Critical Architectural Finding

> **FM-2.2 (hallucinated output) is the highest-risk fault class in a microservice LLM-MAS.**  
> - At the single-agent level: depth=0, no operational flag, no structural alert.  
> - At the system level: a fault-free downstream agent propagates the corrupted value to business harm with no LKW signal at either hop.  
> - Mitigation requires **inter-agent output validation contracts** at every agent boundary — range checks, entity existence checks, schema validation — not just per-agent LKW instrumentation.

---

*Results files:*
- `src/results/stability_summary.json` — RQ5 stability matrices
- `src/results/hitl_classification_report.json` — automated HITL tier classification
- `src/results/cross_agent_propagation.json` — cross-agent chain data
- `src/results/stability_matrix_<agent>.json` — per-agent 3-run fingerprints (×6)
