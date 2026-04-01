"""
Unit Tests for Llama 3 Agent-Based Shipping Service
=====================================================
Tests:
  - Sub-agents (QuoteAgent, CarrierSelectionAgent, TrackingAgent) — no mocking needed
  - ShippingOrchestrator._parse_react_output       — pure logic, no HTTP
  - ShippingOrchestrator._run_agent_loop           — mocked HTTP calls to Llama
  - ShippingOrchestrator.get_quote / ship_order    — end-to-end with mocked Llama
"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.quote_agent import QuoteAgent
from agents.carrier_agent import CarrierSelectionAgent
from agents.tracking_agent import TrackingAgent
from orchestrator import ShippingOrchestrator


# ── Helpers ───────────────────────────────────────────────────────────────────

def mock_llama_response(content: str):
    """Build a fake requests.Response-like return for _call_llama."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ── Sub-agent tests (identical to Claude version — agents are shared) ─────────

class TestQuoteAgent(unittest.TestCase):
    def setUp(self):
        self.agent = QuoteAgent()

    def test_us_domestic(self):
        r = self.agent.estimate({"country": "US"}, [{"product_id": "A", "quantity": 2}])
        self.assertGreater(r["cost_usd"], 0)

    def test_international_higher_than_domestic(self):
        us = self.agent.estimate({"country": "US"}, [{"product_id": "X", "quantity": 3}])
        jp = self.agent.estimate({"country": "JP"}, [{"product_id": "X", "quantity": 3}])
        self.assertGreater(jp["cost_usd"], us["cost_usd"])

    def test_more_items_costs_more(self):
        small = self.agent.estimate({"country": "US"}, [{"product_id": "A", "quantity": 1}])
        large = self.agent.estimate({"country": "US"}, [{"product_id": "A", "quantity": 20}])
        self.assertGreater(large["cost_usd"], small["cost_usd"])


class TestCarrierAgent(unittest.TestCase):
    def setUp(self):
        self.agent = CarrierSelectionAgent()

    def test_domestic_carrier(self):
        r = self.agent.select({"country": "US"}, 8.0, 3)
        self.assertIn(r["carrier"], ["FedEx", "USPS", "UPS", "DHL"])

    def test_express_on_high_cost(self):
        r = self.agent.select({"country": "US"}, 25.0, 5)
        self.assertEqual(r["service_level"], "express")

    def test_international_carrier(self):
        r = self.agent.select({"country": "DE"}, 15.0, 4)
        self.assertIn(r["carrier"], ["DHL", "UPS"])


class TestTrackingAgent(unittest.TestCase):
    def setUp(self):
        self.agent = TrackingAgent()

    def test_fedex(self):
        r = self.agent.generate("FedEx", {"city": "NY", "country": "US"}, 2)
        self.assertTrue(r["tracking_id"].startswith("7489"))

    def test_ups(self):
        r = self.agent.generate("UPS", {"city": "LA", "country": "US"}, 1)
        self.assertTrue(r["tracking_id"].startswith("1Z"))

    def test_unique_ids(self):
        ids = {self.agent.generate("FedEx", {"country": "US"}, 1)["tracking_id"] for _ in range(20)}
        self.assertGreater(len(ids), 15)


# ── ReAct parser tests ────────────────────────────────────────────────────────

class TestParseReactOutput(unittest.TestCase):
    def setUp(self):
        self.orch = ShippingOrchestrator.__new__(ShippingOrchestrator)

    def test_parse_final_answer(self):
        text = 'Thought: Done.\nFinal Answer: {"cost_usd": 12.5}'
        kind, value, _ = self.orch._parse_react_output(text)
        self.assertEqual(kind, "final")
        self.assertIn("12.5", value)

    def test_parse_action(self):
        text = (
            'Thought: I should get a quote.\n'
            'Action: get_shipping_quote\n'
            'Action Input: {"address": {"country": "US"}, "items": []}'
        )
        kind, tool_name, tool_input = self.orch._parse_react_output(text)
        self.assertEqual(kind, "action")
        self.assertEqual(tool_name, "get_shipping_quote")
        self.assertIn("address", tool_input)

    def test_parse_unknown(self):
        kind, _, _ = self.orch._parse_react_output("Hello, I am a language model.")
        self.assertEqual(kind, "unknown")

    def test_parse_malformed_json_action_input(self):
        text = (
            'Action: select_carrier\n'
            'Action Input: {this is not valid json}'
        )
        kind, tool_name, tool_input = self.orch._parse_react_output(text)
        self.assertEqual(kind, "action")
        self.assertEqual(tool_input, {})  # graceful fallback


# ── Full orchestrator tests (mocked HTTP) ─────────────────────────────────────

class TestShippingOrchestratorGetQuote(unittest.TestCase):
    """Tests get_quote with simulated Llama ReAct sequence."""

    def setUp(self):
        self.orch = ShippingOrchestrator()

    @patch("orchestrator.requests.post")
    def test_get_quote_single_tool_call(self, mock_post):
        """Llama calls get_shipping_quote then returns Final Answer."""
        # First call: Llama emits Action
        action_response = (
            "Thought: I need to estimate the shipping cost.\n"
            "Action: get_shipping_quote\n"
            'Action Input: {"address": {"country": "US", "city": "NY"}, '
            '"items": [{"product_id": "ABC", "quantity": 2}]}'
        )
        # Second call: Llama sees Observation and emits Final Answer
        final_response = 'Final Answer: {"cost_usd": 9.75}'

        mock_post.side_effect = [
            mock_llama_response(action_response),
            mock_llama_response(final_response),
        ]

        import asyncio
        result = asyncio.run(self.orch.get_quote(
            {"country": "US", "city": "NY"},
            [{"product_id": "ABC", "quantity": 2}],
        ))

        self.assertIn("cost_usd", result)
        self.assertIsInstance(result["cost_usd"], float)

    @patch("orchestrator.requests.post")
    def test_get_quote_parses_llama_cost(self, mock_post):
        """Ensure cost from Final Answer is correctly extracted."""
        mock_post.side_effect = [
            mock_llama_response(
                "Action: get_shipping_quote\n"
                'Action Input: {"address": {"country": "CA"}, "items": []}'
            ),
            mock_llama_response('Final Answer: {"cost_usd": 14.25}'),
        ]
        import asyncio
        result = asyncio.run(self.orch.get_quote({"country": "CA"}, []))
        self.assertAlmostEqual(result["cost_usd"], 14.25)


class TestShippingOrchestratorShipOrder(unittest.TestCase):
    """Tests ship_order with a full 3-tool ReAct sequence."""

    def setUp(self):
        self.orch = ShippingOrchestrator()

    @patch("orchestrator.requests.post")
    def test_ship_order_full_sequence(self, mock_post):
        """Llama calls all 3 tools in sequence and returns tracking ID."""
        mock_post.side_effect = [
            # Turn 1: get_shipping_quote
            mock_llama_response(
                "Thought: First I need a cost estimate.\n"
                "Action: get_shipping_quote\n"
                'Action Input: {"address": {"country": "US", "city": "Austin"}, '
                '"items": [{"product_id": "X1", "quantity": 3}]}'
            ),
            # Turn 2: select_carrier
            mock_llama_response(
                "Thought: Now I select a carrier.\n"
                "Action: select_carrier\n"
                'Action Input: {"address": {"country": "US"}, "cost_usd": 11.5, "item_count": 3}'
            ),
            # Turn 3: generate_tracking_id
            mock_llama_response(
                "Thought: Now generate the tracking ID.\n"
                "Action: generate_tracking_id\n"
                'Action Input: {"carrier": "FedEx", "address": {"city": "Austin", "country": "US"}, "item_count": 3}'
            ),
            # Turn 4: Final Answer
            mock_llama_response('Final Answer: {"tracking_id": "7489173829001234"}'),
        ]

        import asyncio
        result = asyncio.run(self.orch.ship_order(
            {"country": "US", "city": "Austin"},
            [{"product_id": "X1", "quantity": 3}],
        ))

        self.assertIn("tracking_id", result)
        self.assertIsInstance(result["tracking_id"], str)
        self.assertGreater(len(result["tracking_id"]), 0)
        # Should have called Llama 4 times
        self.assertEqual(mock_post.call_count, 4)

    @patch("orchestrator.requests.post")
    def test_ship_order_fallback_on_bad_json(self, mock_post):
        """If Llama emits plain-text before Final Answer, the nudge loop recovers."""
        mock_post.side_effect = [
            mock_llama_response(
                "Action: get_shipping_quote\n"
                'Action Input: {"address": {"country": "US"}, "items": []}'
            ),
            mock_llama_response(
                "Action: select_carrier\n"
                'Action Input: {"address": {"country": "US"}, "cost_usd": 8.0, "item_count": 1}'
            ),
            mock_llama_response(
                "Action: generate_tracking_id\n"
                'Action Input: {"carrier": "UPS", "address": {"country": "US"}, "item_count": 1}'
            ),
            # Unknown output triggers nudge + one more Llama call
            mock_llama_response("The tracking ID is 1ZABC123XYZ"),
            mock_llama_response('Final Answer: {"tracking_id": "1ZABC123XYZ"}'),
        ]

        import asyncio
        result = asyncio.run(self.orch.ship_order({"country": "US"}, []))
        self.assertIn("tracking_id", result)
        self.assertGreater(len(result["tracking_id"]), 0)


class TestOrchestratorConnectionError(unittest.TestCase):
    """Tests that connection failures raise a clear RuntimeError."""

    def setUp(self):
        self.orch = ShippingOrchestrator()

    @patch("orchestrator.requests.post", side_effect=Exception("Connection refused"))
    def test_connection_error_raises(self, mock_post):
        import asyncio
        with self.assertRaises(Exception):
            asyncio.run(self.orch.get_quote({"country": "US"}, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
