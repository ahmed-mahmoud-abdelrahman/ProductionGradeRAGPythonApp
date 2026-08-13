"""Coordinator: orchestrates requests using the LangChain RAG Agent."""
from agent import run_rag_agent


def handle_request(user_input: str, langsmith_api_key: str = None):
    """Handle a user request using the LangChain RAG AI Agent."""
    return run_rag_agent(user_input, langsmith_api_key=langsmith_api_key)

