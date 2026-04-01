# Agent-Based ShippingService — Llama 3 (Self-Hosted) Variant

Same agent design as the Claude variant, but the LLM backend is a **self-hosted Llama 3**
instance running inside your Kubernetes cluster via [vLLM](https://github.com/vllm-project/vllm).
No external API calls, no API keys — the model runs entirely within your infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  gRPC Client (checkoutservice / frontend)                               │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ proto: GetQuote / ShipOrder
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  main.py  —  ShippingServicer (gRPC adapter, identical to Claude ver.)  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  orchestrator.py  —  ShippingOrchestrator (Llama 3 / ReAct)             │
│                                                                         │
│  Uses a ReAct prompting loop instead of native tool-use API:            │
│    Thought → Action → Action Input → Observation → ... → Final Answer   │
│                                                                         │
│  HTTP POST → llama-service:8000/v1/chat/completions (OpenAI-compat.)    │
└──────┬──────────────────────┬──────────────────────┬────────────────────┘
       │                      │                      │
       ▼                      ▼                      ▼
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ QuoteAgent  │    │ CarrierSelection │    │  TrackingAgent   │
│  (shared)   │    │  Agent (shared)  │    │   (shared)       │
└─────────────┘    └──────────────────┘    └──────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  llama-service (vLLM)        │
              │  meta-llama/Llama-3-8B-      │
              │  Instruct  (GPU node)        │
              └─────────────────────────────┘
```

## Claude vs Llama 3 — Key Differences

| Aspect               | Claude variant                    | Llama 3 variant                          |
|----------------------|-----------------------------------|------------------------------------------|
| LLM API              | Anthropic SDK (`anthropic`)       | HTTP `requests` to local vLLM            |
| Tool-use mechanism   | Native structured tool-use blocks | ReAct prompting (Thought/Action/Obs.)    |
| API key              | `ANTHROPIC_API_KEY` (external)    | `HUGGINGFACE_HUB_TOKEN` (model download only) |
| Inference cost       | Per-token billing                 | GPU node cost (self-managed)             |
| Latency              | ~1–3s per tool call (API round trip) | ~0.5–2s (in-cluster, GPU-dependent)  |
| Data sovereignty     | Data leaves cluster               | Data stays entirely in-cluster           |
| Horizontal scaling   | Stateless, scale freely           | Stateless; vLLM handles GPU contention   |
| Sub-agents           | Identical Python code             | Identical Python code                    |

## ReAct Loop

Llama 3 does not have a native structured tool-use API (unlike Claude), so this variant
uses **ReAct** (Reason + Act) prompting:

```
[System]: You are a shipping agent. Tools available: get_shipping_quote, select_carrier, generate_tracking_id.
          Use format: Thought / Action / Action Input / ... / Final Answer

[User]: Ship an order to {"country": "US"}, items=[...]

[Llama]: Thought: I need to estimate cost first.
         Action: get_shipping_quote
         Action Input: {"address": {"country": "US"}, "items": [...]}

[Orchestrator appends]: Observation: {"cost_usd": 11.5, "breakdown": {...}}

[Llama]: Thought: Now select carrier.
         Action: select_carrier
         Action Input: {"address": {"country": "US"}, "cost_usd": 11.5, "item_count": 3}

[Orchestrator appends]: Observation: {"carrier": "FedEx", "service_level": "express", ...}

[Llama]: Thought: Generate tracking ID.
         Action: generate_tracking_id
         Action Input: {"carrier": "FedEx", "address": {...}, "item_count": 3}

[Orchestrator appends]: Observation: {"tracking_id": "7489173829001234", ...}

[Llama]: Final Answer: {"tracking_id": "7489173829001234"}
```

## Files

```
shippingservice-llama/
├── main.py                   # gRPC server (identical to Claude variant)
├── orchestrator.py           # Llama 3 ReAct loop + HTTP client
├── agents/
│   ├── __init__.py
│   ├── quote_agent.py        # Shared with Claude variant
│   ├── carrier_agent.py      # Shared with Claude variant
│   └── tracking_agent.py     # Shared with Claude variant
├── tests/
│   └── test_agents.py        # 18 tests — no GPU or API key required
├── requirements.txt          # No anthropic SDK — only grpcio + requests
├── Dockerfile
└── kubernetes-manifest.yaml  # Deploys vLLM (GPU) + shippingservice (CPU)
```

## Setup

### 1. Prerequisites
- Kubernetes cluster with at least one GPU node (NVIDIA L4, T4, or A100)
- Node labeled with `cloud.google.com/gke-accelerator` (GKE) or equivalent
- `kubectl` configured for your cluster

### 2. Set HuggingFace token (for model download)
```bash
kubectl create secret generic huggingface-token -n shipping \
  --from-literal=token=hf_...
```
> Note: You need to accept the Llama 3 license at huggingface.co/meta-llama first.

### 3. Deploy everything
```bash
kubectl apply -f kubernetes-manifest.yaml

# Watch llama-service come up (takes 2-5 min for model download)
kubectl get pods -n shipping -w
```

### 4. Build and deploy shippingservice
```bash
docker build -t your-registry/shippingservice-llama:latest .
docker push your-registry/shippingservice-llama:latest

# Update the image in kubernetes-manifest.yaml, then:
kubectl rollout restart deployment/shippingservice -n shipping
```

### 5. Run tests (no GPU needed)
```bash
python -m unittest tests/test_agents.py -v
```

## Model Options

| Model                              | VRAM  | Quality  | Speed    | Notes                      |
|------------------------------------|-------|----------|----------|----------------------------|
| Meta-Llama-3-8B-Instruct           | 16GB  | Good     | Fast     | Default, fits L4/T4        |
| Meta-Llama-3-70B-Instruct          | 140GB | Best     | Slower   | Needs A100 80GB x2         |
| Meta-Llama-3-8B-Instruct (4-bit)   | 8GB   | Good     | Fastest  | Add `--quantization awq`   |

Change the model via the `LLAMA_MODEL` env var and `--model` vLLM arg in the manifest.

## Tuning the ReAct Loop

Two constants in `orchestrator.py` control loop behavior:

```python
MAX_ITERATIONS = 8   # max Llama calls per request before raising RuntimeError
MAX_TOKENS     = 512 # max tokens per Llama response
```

For simpler requests (GetQuote), 2 iterations suffice.
For ShipOrder (3 tool calls), expect 4–5 iterations.
Increase `MAX_ITERATIONS` if you add more agents.
