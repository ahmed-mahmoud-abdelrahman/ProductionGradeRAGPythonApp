import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tracers.langchain import LangChainTracer

from data_loader import embed_texts
from vector_db import QdrantStorage

load_dotenv()

SYSTEM_PROMPT = (
    "You are an expert AI RAG Agent with advanced reasoning, planning, and document search capabilities.\n\n"
    "Guidance:\n"
    "1. THINK & PLAN: When given a request, decide if you need to look up information from uploaded PDF documents.\n"
    "2. GENERAL INQUIRIES & PLANNING: If the request is a general question, task planning, coding, or math, you can directly reason and answer without retrieving documents.\n"
    "3. DOCUMENT RETRIEVAL: If the question requires specific context from stored PDFs or uploaded files, invoke the `search_qdrant_docs` tool to retrieve context passages.\n"
    "4. GROUNDING & CITATIONS: When context is retrieved from Qdrant, cite your sources clearly and base your answer on the retrieved facts.\n"
    "5. TRANSPARENCY: Explain your reasoning clearly and structure your output nicely with Markdown headers, bullet points, and code blocks if appropriate."
)


@tool
def search_qdrant_docs(query: str, top_k: int = 5) -> str:
    """Search uploaded PDF documents in the Qdrant vector database for relevant contexts.
    
    Args:
        query: The search query string.
        top_k: Number of relevant text chunks to retrieve (default 5).
        
    Returns:
        A formatted string containing retrieved context passages and source references.
    """
    try:
        query_vec = embed_texts([query])[0]
        store = QdrantStorage()
        res = store.search(query_vec, top_k=top_k)
        
        contexts = res.get("contexts", [])
        sources = res.get("sources", [])
        
        if not contexts:
            return "No matching contexts found in the Qdrant vector database."
        
        formatted_chunks = []
        for i, ctx_text in enumerate(contexts, 1):
            formatted_chunks.append(f"[Chunk {i}]: {ctx_text}")
            
        sources_str = ", ".join(sources) if sources else "Unknown"
        return f"Retrieved Contexts from sources ({sources_str}):\n\n" + "\n\n".join(formatted_chunks)
    except Exception as e:
        return f"Error querying Qdrant vector store: {str(e)}"


@tool
def inspect_indexed_documents() -> str:
    """Inspect the status and collection metadata of the Qdrant vector store.
    
    Returns:
        Overview of available indexed collections and document storage state.
    """
    try:
        store = QdrantStorage()
        exists = store.client.collection_exists(store.collection)
        if not exists:
            return "Collection 'docs' does not exist in Qdrant."
        
        info = store.client.get_collection(store.collection)
        points_count = getattr(info, "points_count", "N/A")
        return f"Qdrant collection '{store.collection}' is ACTIVE. Total indexed vector points: {points_count}."
    except Exception as e:
        return f"Could not inspect vector database: {str(e)}"


TOOLS = [search_qdrant_docs, inspect_indexed_documents]


def run_rag_agent(
    user_input: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    langsmith_api_key: Optional[str] = None,
    project_name: Optional[str] = None
) -> Dict[str, Any]:
    """Execute the LangChain / LangGraph AI Agent with optional LangSmith tracing.
    
    Args:
        user_input: User prompt or question.
        chat_history: Optional prior conversation memory.
        langsmith_api_key: Optional key to override environment for LangSmith tracing.
        project_name: Optional project name for LangSmith tracing.
        
    Returns:
        Dict containing output answer, intermediate reasoning steps, retrieved sources, and tracing status.
    """
    callbacks = []
    tracing_active = False
    
    ls_key = langsmith_api_key or os.getenv("LANGCHAIN_API_KEY")
    
    if ls_key and ls_key.strip():
        try:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = ls_key.strip()
            proj = project_name or os.getenv("LANGCHAIN_PROJECT", "ProductionGradeRAGAgent")
            os.environ["LANGCHAIN_PROJECT"] = proj
            tracer = LangChainTracer(project_name=proj)
            callbacks.append(tracer)
            tracing_active = True
        except Exception as tracer_err:
            print(f"Warning: Could not initialize LangChainTracer: {tracer_err}")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
            
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    agent = create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT
    )
    
    messages = []
    if chat_history:
        for m in chat_history:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant" and content:
                messages.append(AIMessage(content=content))
                
    messages.append(HumanMessage(content=user_input))
    
    config = {}
    if callbacks:
        config["callbacks"] = callbacks
        
    result = agent.invoke({"messages": messages}, config=config)
    
    output_messages = result.get("messages", [])
    
    answer = ""
    formatted_steps = []
    sources = set()
    
    for msg in output_messages:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get("name", "Tool")
                tool_args = tc.get("args", {})
                formatted_steps.append({
                    "tool": tool_name,
                    "input": tool_args,
                    "log": msg.content or f"Calling tool `{tool_name}`",
                    "output": "Executing..."
                })
        elif isinstance(msg, ToolMessage):
            if formatted_steps:
                formatted_steps[-1]["output"] = str(msg.content)
            obs_str = str(msg.content)
            if "Retrieved Contexts from sources (" in obs_str:
                try:
                    src_part = obs_str.split("Retrieved Contexts from sources (")[1].split("):")[0]
                    for s in src_part.split(", "):
                        if s.strip() and s.strip() != "Unknown":
                            sources.add(s.strip())
                except Exception:
                    pass
        elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            answer = msg.content
            
    if not answer and output_messages:
        last_msg = output_messages[-1]
        if hasattr(last_msg, "content"):
            answer = str(last_msg.content)

    return {
        "answer": answer or "Completed processing.",
        "intermediate_steps": formatted_steps,
        "sources": list(sources),
        "langsmith_traced": tracing_active,
        "project_name": os.getenv("LANGCHAIN_PROJECT", "ProductionGradeRAGAgent")
    }


if __name__ == "__main__":
    print("Testing LangChain RAG AI Agent...")
    res = run_rag_agent("Hello! Can you introduce yourself and outline a 3-step strategy for building a RAG application?")
    print("\n--- Answer ---")
    print(res["answer"])
    print("\n--- Intermediate Steps ---")
    print(res["intermediate_steps"])
