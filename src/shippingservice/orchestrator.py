"""
ShippingOrchestrator (Llama 3 variant)
=======================================
Replaces the Anthropic SDK with calls to a self-hosted Llama 3 instance
running as an OpenAI-compatible endpoint inside the Kubernetes cluster
(e.g. via vLLM, Ollama, or llama.cpp server).

Key difference from the Claude version:
  Llama 3 does not natively support tool-use in the same structured way.
  This orchestrator implements a **ReAct loop** (Reason → Act → Observe)
  using a strict prompt format that Llama 3 Instruct can reliably follow.

ReAct format used:
  Thought: <reasoning>
  Action: <tool_name>
  Action Input: <json args>
  ---
  Observation: <tool result injected by orchestrator>
  ... (repeat until)
  Final Answer: <json result>

Environment variables:
  LLAMA_BASE_URL   — OpenAI-compatible base URL, e.g. http://llama-service:8000/v1
  LLAMA_MODEL      — model name to pass in the request, e.g. "meta-llama/Meta-Llama-3-8B-Instruct"
  PORT             — gRPC port (default 50051)
  MONGO_URI        — MongoDB connection string
  MONGO_DB_NAME    — MongoDB database name (default: shipping_service)
"""

import json
import logging
import os
import re
import requests
from datetime import datetime, timezone

try:
    from langsmith import traceable
    from langsmith.wrappers import wrap_openai  # noqa: F401 — available but optional
    LANGSMITH_ENABLED = bool(os.getenv("LANGSMITH_API_KEY"))
except ImportError:
    LANGSMITH_ENABLED = False
    def traceable(*args, **kwargs):
        """No-op fallback when langsmith is not installed."""
        def decorator(fn):
            return fn
        return decorator if args and callable(args[0]) else decorator

from agents.quote_agent import QuoteAgent
from agents.carrier_agent import CarrierSelectionAgent
from agents.tracking_agent import TrackingAgent
from repository import save_quote, save_shipment
from config import LLAMA_BASE_URL, LLAMA_MODEL
import fault_injection as fi


# ── LKW (Last Known Well) Checkpoint Logger ───────────────────────────────────

class LKWCheckpoint:
    """
    Records the state at each well-defined step of the shipping workflow.
    Used by the RIP (Reachability → Infection → Propagation) test harness
    to detect where quality deviation first occurs and how far it spreads.

    Checkpoints:
      TASK_START      — inputs received, fault mode recorded
      QUOTE_DONE      — cost_usd returned by get_shipping_quote
      CARRIER_DONE    — carrier + service_level returned by select_carrier
      TRACKING_DONE   — tracking_id generated
      SAVE_DONE       — shipment persisted to MongoDB
      FINAL_ANSWER    — raw Final Answer string from LLM
    """

    EXPECTED_STEPS = [
        "TASK_START",
        "QUOTE_DONE",
        "CARRIER_DONE",
        "TRACKING_DONE",
        "SAVE_DONE",
        "FINAL_ANSWER",
    ]

    def __init__(self):
        self.checkpoints: list[dict] = []
        self.fault_mode = fi.active_fault()

    def record(self, step: str, data: dict):
        entry = {
            "step":       step,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "fault_mode": self.fault_mode,
            "data":       data,
        }
        self.checkpoints.append(entry)
        log.info("[LKW] %s | fault=%s | data=%s", step, self.fault_mode, data)

    def missing_steps(self) -> list[str]:
        """Return steps that were not reached — indicates propagation depth."""
        reached = {c["step"] for c in self.checkpoints}
        return [s for s in self.EXPECTED_STEPS if s not in reached]

    def to_dict(self) -> dict:
        return {
            "fault_mode":     self.fault_mode,
            "checkpoints":    self.checkpoints,
            "missing_steps":  self.missing_steps(),
            "rip_summary":    self._rip_summary(),
        }

    def _rip_summary(self) -> dict:
        """
        RIP analysis:
          Reachability  — did the fault-injected path reach the same steps as baseline?
          Infection     — which checkpoint first shows deviated data?
          Propagation   — how many downstream steps were affected?
        """
        reached   = [c["step"] for c in self.checkpoints]
        missing   = self.missing_steps()
        infected  = None

        for c in self.checkpoints:
            d = c.get("data", {})
            # Detect infection signals
            if c["step"] == "QUOTE_DONE" and d.get("cost_usd", 1) <= 0:
                infected = c["step"]
                break
            if c["step"] == "CARRIER_DONE" and d.get("carrier") in (None, "SpeedyShip", "Unknown"):
                infected = c["step"]
                break
            if c["step"] == "TRACKING_DONE" and "PREMATURE" in str(d.get("tracking_id", "")):
                infected = c["step"]
                break
            if c["step"] == "SAVE_DONE" and not d.get("saved", True):
                infected = c["step"]
                break

        propagation = len(missing)  # each missing step = one level of propagation

        return {
            "reachability": reached,
            "infection_point": infected,
            "propagation_depth": propagation,
            "missing_steps": missing,
        }


log = logging.getLogger(__name__)


MAX_ITERATIONS = 8
MAX_TOKENS     = 512


TOOL_DESCRIPTIONS = """You have access to these tools:

1. get_shipping_quote
   Description: Estimates the USD shipping cost for a destination address and cart items.
   Input JSON schema:
     { "address": {"city": str, "country": str, "state": str, "zip_code": int},
       "items": [{"product_id": str, "quantity": int}] }
   Returns: {"cost_usd": float, "breakdown": {...}}

2. select_carrier
   Description: Selects the best shipping carrier given the destination, cost, and item count.
   Input JSON schema:
     { "address": {"country": str, "state": str, "zip_code": int},
       "cost_usd": float,
       "item_count": int }
   Returns: {"carrier": str, "service_level": str, "estimated_delivery_days": int, "reason": str}

3. generate_tracking_id
   Description: Generates a unique carrier-formatted tracking ID and registers the shipment.
   Input JSON schema:
     { "carrier": str, "address": {"city": str, "country": str}, "item_count": int }
   Returns: {"tracking_id": str, "carrier": str, "registered": bool}

Use the following format EXACTLY — no deviations:

Thought: <your reasoning about what to do next>
Action: <tool name, one of: get_shipping_quote | select_carrier | generate_tracking_id>
Action Input: <valid JSON matching the tool's input schema>

When you have the final answer, output:
Final Answer: <valid JSON with the result>
"""

REACT_SYSTEM_PROMPT = (
    "You are a shipping logistics agent. "
    "Solve tasks step-by-step. "
    "Always use Thought/Action/Action Input/Final Answer format exactly. "
    "Keep Thought sections under 2 sentences. Do not explain tool schemas."
)


class ShippingOrchestrator:
    """
    Orchestrates shipping operations using Llama 3 (self-hosted) as the
    reasoning engine, via a ReAct prompting loop.
    Sub-agents are identical to the Claude version — fully reusable.
    """

    def __init__(self):
        self.base_url        = LLAMA_BASE_URL.rstrip("/")
        self.model           = LLAMA_MODEL
        self.quote_agent     = QuoteAgent()
        self.carrier_agent   = CarrierSelectionAgent()
        self.tracking_agent  = TrackingAgent()
        log.info(f"ShippingOrchestrator (Llama) ready — endpoint={self.base_url}, model={self.model}")

    # ── Llama inference call ──────────────────────────────────────────────────

    def _call_llama(self, messages: list, stop: list = None) -> str:
        payload = {
            "model":       self.model,
            "messages":    messages,
            "max_tokens":  MAX_TOKENS,
            "temperature": 0.0,
        }
        if stop:
            payload["stop"] = stop

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=(60, 120),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data    = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            usage         = data.get("usage", {})
            input_tokens  = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens  = usage.get("total_tokens", input_tokens + output_tokens)

            print(f"TOKEN_METRICS input={input_tokens} output={output_tokens} total={total_tokens}")

            with open("token_log.txt", "a") as f:
                f.write(f"{total_tokens}\n")

            return content
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Cannot reach Llama endpoint at {self.base_url}. "
                f"Ensure the llama-service pod is running. Error: {e}"
            )
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Llama API HTTP error: {e} — {resp.text[:200]}")

    # ── ReAct parser ──────────────────────────────────────────────────────────

    def _parse_react_output(self, text: str):
        fa_match = re.search(r"Final Answer:\s*(\{.*\})", text, re.DOTALL)
        if fa_match:
            return ("final", fa_match.group(1).strip(), None)

        action_match = re.search(r"Action:\s*(\w+)", text)
        ai_start     = re.search(r"Action Input:\s*(\{)", text)

        if action_match and ai_start:
            tool_name = action_match.group(1).strip()
            start = ai_start.start(1)
            depth, end = 0, start
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            raw_json = text[start:end]
            try:
                tool_input = json.loads(raw_json)
            except json.JSONDecodeError as e:
                log.warning(f"Failed to parse Action Input JSON: {e}\nRaw: {raw_json}")
                tool_input = {}
            return ("action", tool_name, tool_input)

        return ("unknown", text, None)

    # ── Tool dispatcher ───────────────────────────────────────────────────────

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        log.debug(f"Dispatching tool: {tool_name}, input={tool_input}")

        if tool_name == "get_shipping_quote":
            result = self.quote_agent.estimate(
                tool_input.get("address", {}), tool_input.get("items", [])
            )
        elif tool_name == "select_carrier":
            quoted_cost = float(tool_input.get("cost_usd", 0))
            selection_cost = fi.maybe_ignore_quote_for_carrier(quoted_cost)
            result = self.carrier_agent.select(
                tool_input.get("address", {}),
                selection_cost,
                int(tool_input.get("item_count", 1)),
            )
            if fi.active_fault() == "FM_2_5" and isinstance(result, dict):
                result["ignored_downstream_quote"] = True
                result["quoted_cost_usd"] = quoted_cost
                result["used_cost_usd"] = selection_cost
            # FM-2.2: replace real result with hallucinated carrier data
            result = fi.maybe_hallucinate_carrier(result)
            # BL-VENDOR_NEGOTIATION: force expensive fallback carrier
            result = fi.maybe_force_vendor(result)
        elif tool_name == "generate_tracking_id":
            result = self.tracking_agent.generate(
                tool_input.get("carrier", "FedEx"),
                tool_input.get("address", {}),
                int(tool_input.get("item_count", 1)),
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        log.debug(f"Tool result: {result}")
        return json.dumps(result)

    # ── ReAct agentic loop ────────────────────────────────────────────────────

    def _run_agent_loop(self, task_prompt: str) -> str:
        messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user",   "content": TOOL_DESCRIPTIONS + "\n\n" + task_prompt},
        ]
        scratchpad = ""

        for iteration in range(MAX_ITERATIONS):
            log.debug(f"ReAct iteration {iteration + 1}/{MAX_ITERATIONS}")

            current_messages = messages.copy()
            if scratchpad:
                current_messages.append({"role": "assistant", "content": scratchpad})
                current_messages.append({"role": "user",      "content": "Continue."})

            llama_output = self._call_llama(current_messages, stop=["Observation:"])
            log.debug(f"Llama output:\n{llama_output}")
            scratchpad += "\n" + llama_output

            kind, value, tool_input = self._parse_react_output(llama_output)

            # FM-3.1: inject premature Final Answer after first observation
            early = fi.maybe_inject_early_termination(iteration, scratchpad)
            if early is not None:
                llama_output = early
                kind, value, tool_input = self._parse_react_output(llama_output)

            if kind == "final":
                log.info(f"Agent reached Final Answer after {iteration + 1} iterations")
                return value
            elif kind == "action":
                tool_result  = self._dispatch_tool(value, tool_input)
                observation  = f"\nObservation: {tool_result}\n"
                scratchpad  += observation
                log.debug(f"Appended observation: {observation.strip()}")
            else:
                log.warning(f"Unexpected Llama output (iteration {iteration+1}): {value[:200]}")
                scratchpad += "\nThought: I need to use a tool or provide a Final Answer.\n"

        raise RuntimeError(
            f"ReAct loop exceeded {MAX_ITERATIONS} iterations without a Final Answer"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    @traceable(name="shipping.get_quote")
    async def get_quote(self, address: dict, items: list, capture_partial_trace: bool = False) -> dict:
        """
        Estimate shipping cost using Llama 3 + ReAct, then save to MongoDB.
        Returns: {"cost_usd": float}
        """
        ckpt = LKWCheckpoint()
        ckpt.record("TASK_START", {"address": address, "item_count": len(items)})

        task = (
            f"Task: Estimate the shipping cost.\n"
            f"Address: {json.dumps(address)}\n"
            f"Items: {json.dumps(items)}\n"
            f"Use the get_shipping_quote tool, then return: "
            f'Final Answer: {{"cost_usd": <number>}}'
        )

        try:
            raw = self._run_agent_loop(task)
            log.info(f"GetQuote agent response: {raw}")
        except Exception as exc:
            if not capture_partial_trace:
                raise
            log.exception("GetQuote failed during benchmark capture")
            ckpt.record("FINAL_ANSWER", {"raw": "", "error": str(exc)})
            log.info("[LKW] get_quote trace: %s", json.dumps(ckpt.to_dict()))
            return {"error": str(exc), "_lkw": ckpt.to_dict()}

        try:
            data     = json.loads(raw)
            cost_usd = float(data["cost_usd"])
        except Exception:
            match    = re.search(r"[\d]+\.?[\d]*", raw)
            cost_usd = float(match.group()) if match else 5.0

        ckpt.record("QUOTE_DONE", {"cost_usd": cost_usd})
        ckpt.record("FINAL_ANSWER", {"raw": raw})

        # ── Save quote to MongoDB ─────────────────────────────────────────────
        quote_result = self.quote_agent.estimate(address, items)
        if capture_partial_trace:
            ckpt.record("SAVE_DONE", {"saved": False, "reason": "benchmark_mode"})
        else:
            await save_quote(
                address   = address,
                items     = items,
                cost_usd  = cost_usd,
                breakdown = quote_result.get("breakdown", {}),
            )
            ckpt.record("SAVE_DONE", {"saved": True, "cost_usd": cost_usd})

        log.info("[LKW] get_quote trace: %s", json.dumps(ckpt.to_dict()))
        return {"cost_usd": cost_usd, "_lkw": ckpt.to_dict()}

    @traceable(name="shipping.ship_order")
    async def ship_order(self, address: dict, items: list, capture_partial_trace: bool = False) -> dict:
        """
        Orchestrate a full shipment using Llama 3 + ReAct:
        quote → carrier selection → tracking ID, then save to MongoDB.
        Returns: {"tracking_id": str}
        """
        ckpt = LKWCheckpoint()
        # BL-INVENTORY_MISMATCH: corrupt quantities before computing item_count
        items = fi.maybe_corrupt_items(items)
        item_count = sum(i.get("quantity", 1) for i in items)
        # BL-COMPLIANCE_AMBIGUITY: tag address with unknown jurisdiction
        address = fi.maybe_tag_compliance_unknown(address)
        ckpt.record("TASK_START", {"address": address, "item_count": item_count})

        base_task = (
            f"Task: Fulfill a shipping order step by step.\n"
            f"Address: {json.dumps(address)}\n"
            f"Items: {json.dumps(items)}\n"
            f"Total items: {item_count}\n\n"
            f"You MUST call these tools in order:\n"
            f"1. get_shipping_quote — to get the cost\n"
            f"2. select_carrier — using the cost and item count\n"
            f"3. generate_tracking_id — using the chosen carrier\n"
            f'Then return: Final Answer: {{"tracking_id": "<id>", "carrier": "<name>", '
            f'"service_level": "<level>", "cost_usd": <number>}}'
        )
        # FM-1.2: corrupt task spec before sending to LLM
        task = fi.corrupt_task_spec(base_task)

        try:
            raw = self._run_agent_loop(task)
            log.info(f"ShipOrder agent response: {raw}")
            ckpt.record("FINAL_ANSWER", {"raw": raw})
        except Exception as exc:
            if not capture_partial_trace:
                raise
            log.exception("ShipOrder failed during benchmark capture")
            ckpt.record("FINAL_ANSWER", {"raw": "", "error": str(exc)})
            ckpt.record("SAVE_DONE", {"saved": False, "reason": "benchmark_mode"})
            log.info("[LKW] ship_order trace: %s", json.dumps(ckpt.to_dict()))
            return {"error": str(exc), "_lkw": ckpt.to_dict()}

        try:
            data = json.loads(raw)
        except Exception:
            data = {}

        tracking_id   = str(data.get("tracking_id", raw.strip()[:64] or "UNKNOWN-TRACKING-ID"))
        carrier       = data.get("carrier", "Unknown")
        service_level = data.get("service_level", "standard")
        cost_usd      = float(data.get("cost_usd", 0.0))
        # BL-REFUND_REASONING: force negative cost to expose refund-check gap
        cost_usd = fi.maybe_corrupt_cost(cost_usd)

        # FM-3.1: if fault-injected early answer is observed, stop before
        # carrier/save workflow to surface a deterministic premature termination
        # signal in LKW/RIP output.
        if tracking_id.startswith("PREMATURE"):
            ckpt.record("QUOTE_DONE", {"cost_usd": cost_usd})
            ckpt.record("TRACKING_DONE", {"tracking_id": tracking_id})
            ckpt.record(
                "SAVE_DONE",
                {
                    "saved": False,
                    "tracking_id": tracking_id,
                    "reason": "premature_termination",
                },
            )
            log.warning(
                "[FM-3.1] Premature termination path returned early with tracking_id=%s",
                tracking_id,
            )
            log.info("[LKW] ship_order trace: %s", json.dumps(ckpt.to_dict()))
            return {"tracking_id": tracking_id, "_lkw": ckpt.to_dict()}

        ckpt.record("QUOTE_DONE",   {"cost_usd": cost_usd})
        carrier_data = {"carrier": carrier, "service_level": service_level}
        if fi.active_fault() == "FM_2_5":
            carrier_data["ignored_downstream_quote"] = True
            carrier_data["quoted_cost_usd"] = cost_usd
            carrier_data["used_cost_usd"] = 4.99
            carrier_data["silent_absorption"] = carrier == "UPS"
        if fi.active_fault() == "BL_VENDOR_NEGOTIATION":
            carrier_data["injected_carrier"] = "PremiumExpress"
            carrier_data["injected_service"] = "overnight"
            carrier_data["silent_absorption"] = carrier != "PremiumExpress"
        ckpt.record("CARRIER_DONE", carrier_data)
        ckpt.record("TRACKING_DONE", {"tracking_id": tracking_id})

        # BL-CUSTOMER_ESCALATION: flag high-risk orders before saving
        final_meta = fi.maybe_inject_escalation_flag({"tracking_id": tracking_id, "carrier": carrier})
        ckpt.record("ESCALATION_CHECK", {"escalation_required": final_meta.get("escalation_required", False)})

        # ── Save shipment to MongoDB ───────────────────────────────────────────
        # BL-SHIPMENT_LOST: fault may silently skip this save
        if capture_partial_trace:
            ckpt.record("SAVE_DONE", {"saved": False, "tracking_id": tracking_id, "reason": "benchmark_mode"})
        elif not fi.should_skip_shipment_save():
            await save_shipment(
                address       = address,
                items         = items,
                cost_usd      = cost_usd,
                carrier       = carrier,
                service_level = service_level,
                tracking_id   = tracking_id,
            )
            ckpt.record("SAVE_DONE", {"saved": True, "tracking_id": tracking_id})
        else:
            ckpt.record("SAVE_DONE", {"saved": False, "tracking_id": tracking_id})

        log.info("[LKW] ship_order trace: %s", json.dumps(ckpt.to_dict()))
        return {"tracking_id": tracking_id, "_lkw": ckpt.to_dict()}