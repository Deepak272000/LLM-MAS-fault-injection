from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

from app.agent import generate_email_content
from app.grpc_client import EmailServiceClient


class EmailGraphState(TypedDict):
    request: Dict[str, Any]
    email_type: str
    subject: str
    body: str
    llm_used: bool
    microservice_status: str


def run_agent_node(state: EmailGraphState) -> EmailGraphState:
    result = generate_email_content(state["request"])
    state["email_type"] = result["email_type"]
    state["subject"] = result["subject"]
    state["body"] = result["body"]
    state["llm_used"] = result["llm_used"]
    return state


def send_via_microservice_node(state: EmailGraphState) -> EmailGraphState:
    client = EmailServiceClient()
    result = client.send_confirmation_email(state["request"])
    state["microservice_status"] = result["status"]
    return state


def build_graph():
    graph = StateGraph(EmailGraphState)
    graph.add_node("run_agent", run_agent_node)
    graph.add_node("send_via_microservice", send_via_microservice_node)

    graph.set_entry_point("run_agent")
    graph.add_edge("run_agent", "send_via_microservice")
    graph.add_edge("send_via_microservice", END)

    return graph.compile()