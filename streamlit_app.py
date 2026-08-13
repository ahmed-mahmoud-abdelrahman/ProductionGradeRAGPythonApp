import asyncio
from pathlib import Path
import time
import os
import requests

import streamlit as st
import inngest
from dotenv import load_dotenv
import nest_asyncio

from agent import run_rag_agent, QdrantStorage

nest_asyncio.apply()
load_dotenv()

# Page Configuration with Wide layout & Custom Title
st.set_page_config(
    page_title="AI Agent RAG Hub & LangSmith",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics, glassmorphism, badges, and smooth scrollable layout
st.markdown("""
<style>
    /* Theme Gradients & Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Main Background Header */
    .hero-header {
        background: linear-gradient(135deg, #1e1e38 0%, #2a1b4e 50%, #111827 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px 32px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8 0%, #a855f7 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-top: 6px;
    }
    
    /* Custom Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 8px;
    }
    
    .badge-cyan {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    
    .badge-purple {
        background: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    
    .badge-green {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    
    /* Thinking / Steps Expander Box */
    .thinking-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 12px;
        font-family: monospace;
        font-size: 0.88rem;
    }
    
    /* Source Pill */
    .source-pill {
        display: inline-block;
        background: #1e293b;
        color: #e2e8f0;
        border: 1px solid #334155;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px 4px;
    }
    
    /* Sidebar Styling */
    .sidebar-section {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 12px;
        padding: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Inngest Client
@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)


def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_bytes = file.getbuffer()
    file_path.write_bytes(file_bytes)
    return file_path


async def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
            },
        )
    )


async def send_rag_query_event(question: str, langsmith_key: str = "", chat_history: list = None) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "langsmith_api_key": langsmith_key,
                "chat_history": chat_history or []
            },
        )
    )
    return result[0]


def _inngest_api_base() -> str:
    env_base = os.getenv("INNGEST_API_BASE")
    if env_base:
        clean_url = env_base.replace("host.docker.internal", "127.0.0.1").replace("http://app:", "http://127.0.0.1:")
        return clean_url.replace(":8000", ":8288")
    return "http://127.0.0.1:8288/v1"


def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 60.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    while True:
        try:
            runs = fetch_runs(event_id)
            if runs:
                run = runs[0]
                status = run.get("status")
                if status in ("Completed", "Succeeded", "Success", "Finished"):
                    return run.get("output") or {}
                if status in ("Failed", "Cancelled"):
                    raise RuntimeError(f"Workflow function run status: {status}")
        except Exception as e:
            # Fallback if local inngest dev server is not running: fallback directly to agent execution
            pass
        
        if time.time() - start > timeout_s:
            break
        time.sleep(poll_interval_s)
    
    return {}


# Session State Initialization for Chat History & Settings
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 Hi! I am your **LangChain RAG AI Agent**.\n\nI can answer general questions, create execution plans, think through complex tasks, or retrieve factual context from uploaded PDF documents. How can I help you today?",
            "steps": [],
            "sources": [],
            "traced": False
        }
    ]

if "exec_mode" not in st.session_state:
    st.session_state.exec_mode = "Inngest Async Background Workflow"


# Sidebar Layout
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/brain.png", width=64)
    st.title("Control Center")
    
    # Execution Mode Selector
    st.session_state.exec_mode = st.radio(
        "⚡ Execution Mode",
        ["Inngest Async Background Workflow", "Direct Agent Execution (Instant)"],
        help="Inngest sends background event to dev server (shows runs in dashboard); Direct runs locally in-process."
    )
    
    st.divider()
    
    # PDF Ingestion Section
    st.subheader("📄 Document Vector Store")
    uploaded_pdf = st.file_uploader("Upload PDF Document", type=["pdf"], key="pdf_uploader")
    
    if uploaded_pdf is not None:
        if st.button("🚀 Ingest Document into Qdrant", use_container_width=True, type="primary"):
            with st.spinner("Processing PDF chunks & creating vector embeddings..."):
                saved_path = save_uploaded_pdf(uploaded_pdf)
                try:
                    asyncio.run(send_rag_ingest_event(saved_path))
                    st.success(f"Ingested `{saved_path.name}` into Qdrant!")
                except Exception:
                    # Direct fallback if Inngest dev server offline
                    from data_loader import load_and_chunk_pdf, embed_texts
                    import uuid
                    chunks = load_and_chunk_pdf(str(saved_path.resolve()))
                    vecs = embed_texts(chunks)
                    ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{saved_path.name}:{i}")) for i in range(len(chunks))]
                    payloads = [{"source": saved_path.name, "text": chunks[i]} for i in range(len(chunks))]
                    QdrantStorage().upsert(ids, vecs, payloads)
                    st.success(f"Ingested `{saved_path.name}` ({len(chunks)} chunks) into Qdrant!")
    
    # Qdrant Status Info
    try:
        store = QdrantStorage()
        if store.client.collection_exists(store.collection):
            info = store.client.get_collection(store.collection)
            st.caption(f"🟢 Qdrant Vector DB: **Active** (`{info.points_count}` vectors)")
        else:
            st.caption("🟡 Qdrant Vector DB: **Empty**")
    except Exception:
        st.caption("🔴 Qdrant Vector DB: Offline/Connecting...")

    st.divider()

    # LangSmith Observability Section
    st.subheader("🔭 LangSmith Observability")
    env_ls_key = os.getenv("LANGCHAIN_API_KEY", "")
    ls_api_key_input = st.text_input(
        "LangSmith API Key",
        value=env_ls_key,
        type="password",
        help="Get your API key at https://smith.langchain.com"
    )
    
    if ls_api_key_input:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = ls_api_key_input
        st.markdown('<span class="badge badge-green">🟢 Tracing Active</span>', unsafe_allow_html=True)
        st.caption("Project: `ProductionGradeRAGAgent`")
        st.markdown("[🔗 Open LangSmith Dashboard](https://smith.langchain.com)", unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-purple">⚪ Tracing Ready (Key optional)</span>', unsafe_allow_html=True)
        st.caption("Enter API key above to view live execution traces on LangSmith.")

    st.divider()
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()


# Main UI Header Banner
st.markdown("""
<div class="hero-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1 class="hero-title">Production RAG AI Agent</h1>
            <div class="hero-subtitle">Multi-Step Reasoning, PDF Vector Retrieval & LangSmith Observability</div>
        </div>
        <div>
            <span class="badge badge-cyan">LangChain 0.3</span>
            <span class="badge badge-purple">LangSmith Traced</span>
            <span class="badge badge-green">Qdrant Vector DB</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# Render Scrollable Chat Message History
for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        # Render thinking steps expander if assistant message has intermediate steps
        if msg.get("steps"):
            with st.expander("💭 **Agent Planning & Thinking Process**", expanded=False):
                for step_idx, s in enumerate(msg["steps"], 1):
                    st.markdown(f"**Step {step_idx}: Executed Tool `{s['tool']}`**")
                    if s.get("input"):
                        st.json(s["input"])
                    if s.get("output"):
                        st.markdown(f"```text\n{s['output'][:500]}...\n```")
        
        # Render response content
        st.markdown(msg["content"])
        
        # Render source pills & tracing badges if present
        if msg.get("sources") or msg.get("traced"):
            st.markdown("---")
            cols = st.columns([3, 1])
            with cols[0]:
                if msg.get("sources"):
                    st.markdown("**Sources:** " + " ".join([f'<span class="source-pill">📄 {src}</span>' for src in msg["sources"]]), unsafe_allow_html=True)
            with cols[1]:
                if msg.get("traced"):
                    st.markdown('<span class="badge badge-green">⚡ LangSmith Traced</span>', unsafe_allow_html=True)


# Chat Input & Form Processing
user_query = st.chat_input("Ask a question, request a document summary, or get a plan...")

if user_query:
    # 1. Append User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    # 2. Generate Assistant Response
    with st.chat_message("assistant", avatar="🤖"):
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown("🧠 *Agent is reasoning, planning, and retrieving context...*")
        
        start_time = time.time()
        agent_output = {}
        
        # Build chat history tuple format for agent
        history_tuples = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        if "Direct" in st.session_state.exec_mode:
            # Direct In-Process Execution
            agent_output = run_rag_agent(
                user_input=user_query,
                chat_history=history_tuples,
                langsmith_api_key=ls_api_key_input
            )
        else:
            # Inngest Background Async Workflow Execution
            try:
                event_id = asyncio.run(send_rag_query_event(user_query, ls_api_key_input, history_tuples))
                agent_output = wait_for_run_output(event_id)
            except Exception:
                # Fallback to direct execution if server unreachable
                agent_output = run_rag_agent(
                    user_input=user_query,
                    chat_history=history_tuples,
                    langsmith_api_key=ls_api_key_input
                )

        thinking_placeholder.empty()

        answer = agent_output.get("answer", "No answer generated.")
        steps = agent_output.get("intermediate_steps", [])
        sources = agent_output.get("sources", [])
        traced = agent_output.get("langsmith_traced", False)

        # Display steps expander
        if steps:
            with st.expander("💭 **Agent Planning & Thinking Process**", expanded=True):
                for step_idx, s in enumerate(steps, 1):
                    st.markdown(f"**Step {step_idx}: Executed Tool `{s['tool']}`**")
                    if s.get("input"):
                        st.json(s["input"])
                    if s.get("output"):
                        st.markdown(f"```text\n{s['output'][:600]}...\n```")

        # Display answer text
        st.markdown(answer)

        # Display metadata footer
        if sources or traced:
            st.markdown("---")
            cols = st.columns([3, 1])
            with cols[0]:
                if sources:
                    st.markdown("**Sources:** " + " ".join([f'<span class="source-pill">📄 {src}</span>' for src in sources]), unsafe_allow_html=True)
            with cols[1]:
                if traced:
                    st.markdown('<span class="badge badge-green">⚡ LangSmith Traced</span>', unsafe_allow_html=True)

        # 3. Append Assistant Message to Session State
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "steps": steps,
            "sources": sources,
            "traced": traced
        })