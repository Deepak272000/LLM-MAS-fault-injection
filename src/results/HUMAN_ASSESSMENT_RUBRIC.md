# Human Assessment Rubric — LLM-MAS Fault Injection Root Cause Analysis
**Author:** Deepak Sunil Chavan, Concordia University  
**Purpose:** Independent human evaluation of agent-produced root cause analysis  
**Date:** 2026-06-18  

---

## 1. Background

Each agent in the LLM-MAS system is instrumented with **LKW (Last Known Well) checkpoints**. When a fault is injected, the agent executes and records a structured trace. The agent's "root cause analysis" is the structured output it produces — not a text explanation.

The goal of this assessment is to answer: **"Does the agent's structured output accurately describe the fault that was injected?"**

The ground truth is fully known because the fault was deliberately injected by the researcher. You will compare the agent's output against that known ground truth using the 4 criteria below.

---

## 2. What to Read

For each fault-mode run, open the corresponding `<agent>_fault_results.json` file and read the following fields:

| JSON Field | What it represents |
|---|---|
| `fault_mode` | Which fault was injected (this is the ground truth label) |
| `infection_point` | First checkpoint the agent flagged as infected |
| `propagation_depth` | Number of expected checkpoints missing from the trace |
| `steps_lost` | List of checkpoint names that did not execute |
| `lkw[].data` | Checkpoint-level data — boolean flags and values recorded at each step |

---

## 3. The 4 Scoring Criteria

Score each fault-mode run on the following 4 criteria. Each criterion is worth **1 point**. Maximum score per run = **4/4**.

| # | Criterion | Question | Score 1 | Score 0 |
|---|---|---|---|---|
| **C1** | Detection | Did the agent detect any infection at all? | `infection_point` is not null | `infection_point` is null when a fault was active |
| **C2** | Location | Is the reported `infection_point` the correct checkpoint? | Matches expected checkpoint in the table below | Wrong checkpoint or null |
| **C3** | Flag | Does the LKW data flag correctly describe the nature of the fault? | Correct flag is True in LKW data | Wrong flag, missing flag, or only test-only flag |
| **C4** | Depth | Is `propagation_depth` correct? | Matches expected depth in the table below | Wrong depth |

**NONE baseline runs** are scored separately — if `infection_point` is null and all steps reached, mark as **TN**. If infection is falsely reported on a clean run, mark as **FP**.

---

## 4. Confusion Matrix Classification

| Situation | Classification |
|---|---|
| Fault injected + agent scores **4/4** | **TP** — True Positive |
| Fault injected + agent scores **2–3/4** | **Partial TP** — detected but incomplete |
| Fault injected + agent scores **0–1/4** (detects nothing) | **FN** — False Negative |
| NONE mode + agent reports no infection | **TN** — True Negative |
| NONE mode + agent reports infection | **FP** — False Positive |
| LLM timeout / no checkpoints recorded | **INCONCLUSIVE** — cannot assess |

---

## 5. Expected Values Table (Ground Truth)

This table tells you what the correct answer should be for each fault mode. Compare this against the JSON output.

### 5.1 PaymentAgent
**JSON file:** `src/paymentagent/paymentagent_fault_results.json`  
**Checkpoint chain:** `TASK_START → CARD_VALIDATED → CHARGE_DONE → SAVE_DONE → FINAL_ANSWER`

| Fault Mode | Expected Infection Point | Expected Depth | Expected Flag | Evidence |
|---|---|---|---|---|
| NONE | — | 0 | — | All 5 steps clean |
| FM_3_1 | `FINAL_ANSWER` | 3 | `premature_termination: true` | transaction_id=PREMATURE-0000 |
| FM_2_2 | `CHARGE_DONE` | 0 | `hallucinated: true` | transaction_id starts with FAKE-TXN- |
| FM_2_5 | `CARD_VALIDATED` | 0 | `amount_tampered: true` | units_charged=30 (was 10) |
| FM_1_2 | `CARD_VALIDATED` | 0 | `validation_bypassed: true` | card accepted without real check |
| BL_TRANSACTION_LOST | `SAVE_DONE` | 0 | `save_skipped: true`, `saved: false` | charge executed, no DB record |
| BL_DOUBLE_CHARGE | `SAVE_DONE` | 0 | `double_charge: true` | saved=true but duplicate marker |
| BL_AMOUNT_TAMPERING | `CARD_VALIDATED` | 0 | `amount_tampered: true` | units_charged=30 (was 10) |
| BL_CARD_DECLINED | `FINAL_ANSWER` | 3 | `forced_decline: true` | transaction_id=null, success=false |

---

### 5.2 CurrencyAgent
**JSON file:** `src/currencyagent/currencyagent_fault_results.json`  
**Checkpoint chain:** `TASK_START → CONVERT_DONE → FINAL_ANSWER`

| Fault Mode | Expected Infection Point | Expected Depth | Expected Flag | Evidence |
|---|---|---|---|---|
| NONE | — | 0 | — | units_out=9, all flags false |
| FM_3_1 | `FINAL_ANSWER` | 1 | `premature_termination: true` | currency_code=PREMATURE, units=0 |
| FM_2_2 | `CONVERT_DONE` | 0 | `hallucinated: true` | units_out=1337 (was 9), original_suppressed shows real value |
| FM_2_5 | `CONVERT_DONE` | 0 | `amount_tampered: true` | units_in=50 (was 10, input tampered) |
| FM_1_2 | `CONVERT_DONE` | 0 | `currency_swapped: true` | to_currency=JPY (was EUR) |
| BL_RATE_MANIPULATION | `CONVERT_DONE` | 0 | `rate_manipulated: true` | units_out=90 (was 9, 10× inflation) |
| BL_CURRENCY_UNAVAILABLE | `FINAL_ANSWER` | 1 | `unavailable: true` | CONVERT_DONE missing, error message |
| BL_STALE_RATE | `CONVERT_DONE` | 0 | `stale_rate: true` | units_out=0, cached_at=2026-01-01 |
| BL_CONVERSION_OVERFLOW | `CONVERT_DONE` | 0 | `overflow: true` | units_out=9007199254740992 (MAX_SAFE_INTEGER) |

---

### 5.3 EmailServiceAgent
**JSON file:** `src/emailserviceagent/emailserviceagent_fault_results.json`  
**Checkpoint chain:** `TASK_START → EMAIL_GENERATED → EMAIL_SENT → FINAL_ANSWER`

| Fault Mode | Expected Infection Point | Expected Depth | Expected Flag | Evidence |
|---|---|---|---|---|
| NONE | — | 0 | — | subject correct, body_len=68, status=sent |
| FM_3_1 | `FINAL_ANSWER` | 2 | `premature_termination: true` | email_type=PREMATURE_TERMINATION, body_len=0 |
| FM_2_2 | `EMAIL_GENERATED` | 0 | `hallucinated: true` | subject="CONGRATULATIONS! You've won a prize" (phishing) |
| FM_2_5 | `EMAIL_GENERATED` | 0 | `recipient_swapped: true` | email sent to wrong recipient |
| FM_1_2 | `EMAIL_GENERATED` | 0 | `type_wrong: true` | email_type=promotional (was order_confirmation) |
| BL_SEND_SKIPPED | `EMAIL_SENT` | 0 | `send_skipped: true` | status=skipped_fault (not "sent") |
| BL_DOUBLE_SEND | `EMAIL_SENT` | 0 | `double_send: true` | email sent twice |
| BL_CORRUPTED_BODY | `EMAIL_GENERATED` | 0 | `corrupted: true` | body_len=20 (was 68, garbled content) |
| BL_WRONG_CUSTOMER | `EMAIL_GENERATED` | 0 | `wrong_customer: true` | body_len=80 (different, personalized for wrong person) |

---

### 5.4 ProductCatalogAgent
**JSON file:** `src/productcatalogagent/productcatalogagent_fault_results.json`  
**Checkpoint chain:** `TASK_START → CATALOG_DONE → FINAL_ANSWER`

| Fault Mode | Expected Infection Point | Expected Depth | Expected Flag | Evidence |
|---|---|---|---|---|
| NONE | — | 0 | — | count=2, real products PROD-001/002 |
| FM_3_1 | `FINAL_ANSWER` | 1 | `premature_termination: true` | CATALOG_DONE missing, count=0 |
| FM_2_2 | `CATALOG_DONE` | 0 | `hallucinated: true` | product=HALLUCINATED-001 "Fabricated Product" @ $9999 |
| FM_2_5 | `CATALOG_DONE` | 0 | `query_tampered: true` | query was altered before execution |
| FM_1_2 | `CATALOG_DONE` | 0 | `action_swapped: true` | action=search_products (was list_products) |
| BL_PRODUCT_MISSING | `CATALOG_DONE` | 0 | `products_missing: true` | count=0 (was 2) |
| BL_PRICE_MANIPULATION | `CATALOG_DONE` | 0 | `price_manipulated: true` | price=$190 (was $19.99, 10× inflation) |
| BL_DUPLICATE_PRODUCT | `CATALOG_DONE` | 0 | `duplicated: true` | count=3 (was 2, one duplicate added) |
| BL_WRONG_CATEGORY | `CATALOG_DONE` | 0 | `category_wrong: true` | product assigned to wrong category |

---

### 5.5 RecommendationAgent
**JSON file:** `src/recommendationagent/recommendationagent_fault_results.json`  
**Checkpoint chain:** `TASK_START → RECOMMEND_DONE → FINAL_ANSWER`

| Fault Mode | Expected Infection Point | Expected Depth | Expected Flag | Evidence |
|---|---|---|---|---|
| NONE | — | 0 | — | recs=[PROD-042, PROD-017, PROD-009] |
| FM_3_1 | `FINAL_ANSWER` | 1 | `premature_termination: true` | RECOMMEND_DONE missing, recs=[] |
| FM_2_2 | `RECOMMEND_DONE` | 0 | `hallucinated: true` | recs=[HALLUCINATED-001, HALLUCINATED-002, HALLUCINATED-003] |
| FM_2_5 | `RECOMMEND_DONE` | 0 | `user_id_swapped: true` | recommendations for wrong user |
| FM_1_2 | `RECOMMEND_DONE` | 0 | `method_swapped: true` | action=explain_recommendations (was get_recommendations) |
| BL_EMPTY_RECS | `RECOMMEND_DONE` | 0 | `empty_recs: true` | count=0, recs=[] |
| BL_SELF_RECOMMENDATION | `RECOMMEND_DONE` | 0 | `self_rec: true` | recs=[PROD-001, PROD-002] (same as user's own products) |
| BL_INJECTION_RECS | `RECOMMEND_DONE` | 0 | `injection: true` | SPONSORED-001, SPONSORED-002 prepended |
| BL_SHUFFLED_RECS | `RECOMMEND_DONE` | 0 | `shuffled: true` | recs reversed vs baseline order |

---

### 5.6 AdServiceAgent
**JSON file:** `src/adserviceagent/adserviceagent_fault_results.json`  
**Checkpoint chain:** `TASK_START → CONTEXT_EXTRACTED → ADS_FETCHED → FINAL_ANSWER`

| Fault Mode | Expected Infection Point | Expected Depth | Expected Flag | Evidence |
|---|---|---|---|---|
| NONE | — | 0 | — | 2 real clothing ads |
| FM_3_1 | `FINAL_ANSWER` | 1 | `premature_termination: true` | CONTEXT_EXTRACTED fired but ADS_FETCHED missing |
| FM_2_2 | `ADS_FETCHED` | 0 | `hallucinated: true` | ad URL=fake.ad.example.com/scam (phishing URL) |
| FM_2_5 | `CONTEXT_EXTRACTED` | 0 | `context_tampered: true` | context_keys=["nonexistent_category_xyz"] |
| FM_1_2 | `CONTEXT_EXTRACTED` | 0 | `category_swapped: true` | context_keys=["electronics"] (was "clothing") |
| BL_EMPTY_ADS | `ADS_FETCHED` | 0 | `empty_ads: true` | count=0, ad_preview=null |
| BL_AD_INJECTION | `ADS_FETCHED` | 0 | `injected: true` | count=3, unauthorized ad URL present |
| BL_WRONG_URL | `ADS_FETCHED` | 0 | `wrong_url: true` | redirect_url=wrong.url.example.com |
| BL_DUPLICATE_ADS | `ADS_FETCHED` | 0 | `duplicated: true` | count=3 (was 2, one ad duplicated) |

---

### 5.7 ShippingService (qwen2.5-coder:14b — Real LLM)
**JSON file:** `src/shippingservice/lkw_rip_results.json` (qwen2.5-coder:14b batch run, SPEED HPC A100 MIG)  
**Checkpoint chain:** `TASK_START → QUOTE_DONE → CARRIER_DONE → TRACKING_DONE → ESCALATION_CHECK → FINAL_ANSWER → SAVE_DONE`

> **Note:** Rerun with qwen2.5-coder:14b resolved all 5 previously INCONCLUSIVE results from the Llama 3.2:1b run. All 10 fault modes are now assessable.

| Fault Mode | Expected Infection Point | Expected Depth | Expected Evidence | Notes |
|---|---|---|---|---|
| NONE | — | 0 | All 7 steps clean, no infection | TN |
| FM_3_1 | `TRACKING_DONE` | **1** (bug: actual=2) | CARRIER_DONE + ESCALATION_CHECK missing; depth reports 1 | Partial TP — RIP depth bug persists |
| FM_1_2 | `SAVE_DONE` | 2 | CARRIER_DONE, TRACKING_DONE, ESCALATION_CHECK missing | TP |
| FM_2_2 | `CARRIER_DONE` | 0 | All 7 steps, hallucinated carrier data at CARRIER_DONE | TP |
| FM_2_5 | `CARRIER_DONE` | 0 | All 7 steps, stale quote value at CARRIER_DONE | TP |
| BL_SHIPMENT_LOST | None detected | 1 | SAVE_DONE missing; no infected checkpoint identified (depth=1 auto-detectable) | Partial TP — structural only |
| BL_INVENTORY_MISMATCH | `QUOTE_DONE` | 0 | All 7 steps, inflated item count at QUOTE_DONE | TP |
| BL_VENDOR_NEGOTIATION | `CARRIER_DONE` | 0 | All 7 steps, forced vendor at CARRIER_DONE | TP (was FN under 1B) |
| BL_CUSTOMER_ESCALATION | `ESCALATION_CHECK` | 0 | All 7 steps, escalation_required=True at ESCALATION_CHECK | TP (was Partial TP under 1B) |
| BL_REFUND_REASONING | `QUOTE_DONE` | 0 | All 7 steps, cost_usd negative at QUOTE_DONE | TP |
| BL_COMPLIANCE_AMBIGUITY | None detected | 0 | All 7 steps complete, no infection — 14B model resolved ambiguity | FN — model-capability-dependent |

---

## 6. Scoring Sheet (Fill This In)

Make a copy of this sheet with your name. Score each run independently using the criteria above.

**Assessor name:** ___________________  
**Date completed:** ___________________

### PaymentAgent

| Fault Mode | C1 | C2 | C3 | C4 | Score | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | — | — | — | TN / FP |
| FM_3_1 | | | | | /4 | |
| FM_2_2 | | | | | /4 | |
| FM_2_5 | | | | | /4 | |
| FM_1_2 | | | | | /4 | |
| BL_TRANSACTION_LOST | | | | | /4 | |
| BL_DOUBLE_CHARGE | | | | | /4 | |
| BL_AMOUNT_TAMPERING | | | | | /4 | |
| BL_CARD_DECLINED | | | | | /4 | |

### CurrencyAgent

| Fault Mode | C1 | C2 | C3 | C4 | Score | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | — | — | — | TN / FP |
| FM_3_1 | | | | | /4 | |
| FM_2_2 | | | | | /4 | |
| FM_2_5 | | | | | /4 | |
| FM_1_2 | | | | | /4 | |
| BL_RATE_MANIPULATION | | | | | /4 | |
| BL_CURRENCY_UNAVAILABLE | | | | | /4 | |
| BL_STALE_RATE | | | | | /4 | |
| BL_CONVERSION_OVERFLOW | | | | | /4 | |

### EmailServiceAgent

| Fault Mode | C1 | C2 | C3 | C4 | Score | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | — | — | — | TN / FP |
| FM_3_1 | | | | | /4 | |
| FM_2_2 | | | | | /4 | |
| FM_2_5 | | | | | /4 | |
| FM_1_2 | | | | | /4 | |
| BL_SEND_SKIPPED | | | | | /4 | |
| BL_DOUBLE_SEND | | | | | /4 | |
| BL_CORRUPTED_BODY | | | | | /4 | |
| BL_WRONG_CUSTOMER | | | | | /4 | |

### ProductCatalogAgent

| Fault Mode | C1 | C2 | C3 | C4 | Score | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | — | — | — | TN / FP |
| FM_3_1 | | | | | /4 | |
| FM_2_2 | | | | | /4 | |
| FM_2_5 | | | | | /4 | |
| FM_1_2 | | | | | /4 | |
| BL_PRODUCT_MISSING | | | | | /4 | |
| BL_PRICE_MANIPULATION | | | | | /4 | |
| BL_DUPLICATE_PRODUCT | | | | | /4 | |
| BL_WRONG_CATEGORY | | | | | /4 | |

### RecommendationAgent

| Fault Mode | C1 | C2 | C3 | C4 | Score | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | — | — | — | TN / FP |
| FM_3_1 | | | | | /4 | |
| FM_2_2 | | | | | /4 | |
| FM_2_5 | | | | | /4 | |
| FM_1_2 | | | | | /4 | |
| BL_EMPTY_RECS | | | | | /4 | |
| BL_SELF_RECOMMENDATION | | | | | /4 | |
| BL_INJECTION_RECS | | | | | /4 | |
| BL_SHUFFLED_RECS | | | | | /4 | |

### AdServiceAgent

| Fault Mode | C1 | C2 | C3 | C4 | Score | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | — | — | — | TN / FP |
| FM_3_1 | | | | | /4 | |
| FM_2_2 | | | | | /4 | |
| FM_2_5 | | | | | /4 | |
| FM_1_2 | | | | | /4 | |
| BL_EMPTY_ADS | | | | | /4 | |
| BL_AD_INJECTION | | | | | /4 | |
| BL_WRONG_URL | | | | | /4 | |
| BL_DUPLICATE_ADS | | | | | /4 | |

### ShippingService

| Fault Mode | C1 | C2 | C3 | C4 | Score | Verdict |
|---|---|---|---|---|---|---|
| NONE | — | — | — | — | — | TN / FP |
| FM_3_1 | | | | | /4 | |
| FM_1_2 | | | | | /4 | |
| FM_2_2 | | | | | /4 | |
| FM_2_5 | | | | | /4 | |
| BL_SHIPMENT_LOST | | | | | /4 | |
| BL_INVENTORY_MISMATCH | | | | | /4 | |
| BL_VENDOR_NEGOTIATION | | | | | /4 | |
| BL_CUSTOMER_ESCALATION | | | | | /4 | |
| BL_REFUND_REASONING | | | | | /4 | |
| BL_COMPLIANCE_AMBIGUITY | | | | | /4 | |

---

## 7. Deepak's Completed Assessment (Reference)

| Agent | TP | Partial TP | TN | FP | FN | Inconclusive |
|---|---|---|---|---|---|---|
| PaymentAgent | 8 | 0 | 1 | 0 | 0 | 0 |
| CurrencyAgent | 8 | 0 | 1 | 0 | 0 | 0 |
| EmailServiceAgent | 8 | 0 | 1 | 0 | 0 | 0 |
| ProductCatalogAgent | 8 | 0 | 1 | 0 | 0 | 0 |
| RecommendationAgent | 8 | 0 | 1 | 0 | 0 | 0 |
| AdServiceAgent | 8 | 0 | 1 | 0 | 0 | 0 |
| ShippingService | 7 | 2 | 1 | 0 | 1 | 0 |
| **TOTAL** | **55** | **2** | **7** | **0** | **1** | **0** |

### Key Findings from Deepak's Assessment

1. **Mock-based agents (6 agents): 100% accurate** — 48/48 fault modes correctly identified with 4/4 score. Zero FP, zero FN.

2. **ShippingService rerun with qwen2.5-coder:14b: 0 INCONCLUSIVE** — All 5 previously INCONCLUSIVE fault modes (FM_2_2, FM_2_5, BL_SHIPMENT_LOST, BL_INVENTORY_MISMATCH, BL_COMPLIANCE_AMBIGUITY) now complete successfully. Final score: 7 TP, 2 Partial TP, 1 TN, 1 FN, 0 INCONCLUSIVE.

3. **System bug found in FM_3_1 for ShippingService:** The RIP depth calculator reports depth=1 but actual missing steps = 2 (CARRIER_DONE + ESCALATION_CHECK both absent). ESCALATION_CHECK was not included in the expected steps checker. Bug persists under 14B model — this is a code-level issue, not a model issue.

4. **BL_VENDOR_NEGOTIATION: FN under 1B → TP under 14B** — The 1B model ignored vendor injection and selected UPS naturally. The 14B model correctly reflects forced-vendor routing at CARRIER_DONE. This is a model-capability-dependent detectability finding.

5. **BL_CUSTOMER_ESCALATION: Partial TP under 1B → full TP under 14B** — Under 1B, automated RIP reported infection_point=null. Under 14B, infection correctly appears at ESCALATION_CHECK.

6. **BL_COMPLIANCE_AMBIGUITY is a confirmed FN** — qwen2.5-coder:14b resolved the injected compliance ambiguity gracefully (all 7 steps complete, no infection signal). The 1B model crashed; the 14B model passed through. Fault detectability can be model-capability-dependent: more capable models may absorb semantic ambiguity injections without observable signal.

---

## 8. Instructions for Assessors

1. Read this rubric fully before starting
2. Open the JSON files listed for each agent
3. Fill in the scoring sheet above **independently**
4. For ShippingService: all 10 fault modes are now assessable (rerun with qwen2.5-coder:14b resolved all previously INCONCLUSIVE results)
5. If you disagree with an expected value in Section 5, note it — disagreements are valid findings

---

*Data files location: `e:\Summer ai Agent Project\LLM-MAS\src\`*
