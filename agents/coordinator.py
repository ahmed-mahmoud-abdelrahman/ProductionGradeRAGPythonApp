"""Coordinator: simple orchestrator for agent stubs."""
from .retriever import Retriever
from .planner import Planner
from .synthesizer import Synthesizer


def handle_request(user_input: str):
    """Handle a user request by creating a plan, retrieving docs, and synthesizing.

    This is intentionally synchronous and minimal for an MVP.
    """
    planner = Planner()
    plan = planner.create_plan(user_input)

    retriever = Retriever()
    docs = retriever.search(plan.get("query", user_input))

    synthesizer = Synthesizer()
    return synthesizer.merge(docs, plan)
