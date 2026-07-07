# Failure Injection and Analysis Workflow (ShippingService)

Current workflow:

Shipping Agent -> Fault Injection at Orchestrator/Tool-Response Layer -> Phoenix Trace Collection -> Trace Export (LKW/RIP) -> MAST Annotation -> GPT-4o Evaluation -> RCA and Stability Matrix

```mermaid
flowchart LR
    A[Shipping Agent Request] --> B[Fault Injection Layer\nOrchestrator + Tool Response]
    B --> C[Run Baseline and Fault Modes\n3x Stability Repeats]
    C --> D[Phoenix Trace Collection]
    D --> E[Export LKW/RIP Evidence\nJSON + Matrices + Proof Packages]
    E --> F[MAST FM Mapping\nPrimary + Conditional Labels]
    F --> G[GPT-4o RCA Synthesis]
    G --> H[Final Scenario Summary\nDone/Pending + Benchmark Status]
```

Notes:
- Injection is aligned to structured JSON orchestration, not user-text adversarial prompting.
- Primary FM label is set by dominant reproducible behavior; secondary labels are conditional on explicit trace evidence.
