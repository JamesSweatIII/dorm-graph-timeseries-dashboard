import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from dorm_service import DormSearchService
from query_router import route_query, FALLBACK
from agent import Agent
from animate_component import animated_metrics, animated_chart, page_header, info_banner

load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

st.set_page_config(page_title="Dormitory Agent", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f7f3ef 0%, #fdf6f3 30%, #f5f0eb 60%, #f7f3ef 100%);
}
section[data-testid="stMain"] { max-width: 100% !important; }
.main > .block-container {
    max-width: 820px !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    margin: 0 auto !important;
}
[data-testid="stVerticalBlock"] { width: 100% !important; }
[data-testid="stChatInput"] { width: 100% !important; max-width: 100% !important; }
[data-testid="stChatInput"] > div { width: 100% !important; max-width: 100% !important; }
.stApp::before {
    content: ''; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(ellipse at 30% 20%, rgba(245,158,111,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 70% 80%, rgba(180,140,190,0.06) 0%, transparent 50%);
    pointer-events: none; z-index: 0;
}
.stApp > header {
    background: rgba(247,243,239,0.9) !important;
    backdrop-filter: blur(16px) !important;
    border-bottom: 1px solid rgba(0,0,0,0.06) !important;
}
[data-testid="stSidebar"] { display: none; }
.stApp > .main > .block-container { z-index: 1; position: relative; }

.welcome-card {
    background: rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.06);
    border-radius: 16px; padding: 24px; text-align: center; margin: 16px 0;
    opacity: 0; animation: wIn 0.6s cubic-bezier(0.34,1.56,0.64,1) 0.2s forwards;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
@keyframes wIn { to { opacity: 1; } }
.welcome-card .emoji { font-size: 40px; display: block; margin-bottom: 8px; }
.welcome-card h2 { color: #2d2a3e; font-size: 18px; font-weight: 600; margin: 0 0 4px; }
.welcome-card p { color: #6b6578; font-size: 13px; margin: 0 0 16px; }
.welcome-suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.welcome-chip {
    background: rgba(245,158,111,0.08); border: 1px solid rgba(245,158,111,0.15);
    border-radius: 20px; padding: 6px 14px; color: #c77d4a; font-size: 12px;
    cursor: pointer; transition: all 0.2s ease;
    font-family: inherit;
}
.welcome-chip:hover { background: rgba(245,158,111,0.15); border-color: rgba(245,158,111,0.3); }

.msg-row {
    display: flex; margin-bottom: 14px; gap: 10px;
    opacity: 0; animation: mIn 0.4s cubic-bezier(0.22,1,0.36,1) forwards;
}
@keyframes mIn { to { opacity: 1; } }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }
.msg-avatar {
    width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; margin-top: 4px; user-select: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.msg-avatar.u { background: linear-gradient(135deg,#f59e6f,#f7b384); color: #fff; }
.msg-avatar.a { background: linear-gradient(135deg,#b89abe,#c9aecf); color: #fff; }
.msg-body { max-width: 78%; }
.msg-bubble {
    padding: 10px 16px; border-radius: 18px; font-size: 14px; line-height: 1.55;
    color: #2d2a3e; word-wrap: break-word; position: relative;
}
.msg-bubble.user {
    background: linear-gradient(135deg,rgba(245,158,111,0.12),rgba(245,158,111,0.06));
    border: 1px solid rgba(245,158,111,0.15);
    border-bottom-right-radius: 6px;
}
.msg-bubble.assistant {
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(0,0,0,0.06);
    border-bottom-left-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.msg-bubble strong { color: #c77d4a; }
.msg-bubble code {
    background: rgba(0,0,0,0.05); padding: 1px 6px; border-radius: 4px;
    font-size: 13px; color: #b87a44;
}
.msg-time { font-size: 10px; color: rgba(0,0,0,0.25); margin-top: 4px; }

.streamlit-expanderHeader { color: #64748b !important; font-size: 12px !important; }
div[data-testid="stChatInput"] {
    width: 100% !important; max-width: 100% !important;
}
div[data-testid="stChatInput"] > div {
    width: 100% !important; max-width: 100% !important;
}
.stChatInput {
    background: rgba(255,255,255,0.8) !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    border-radius: 16px !important;
    padding: 8px !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
}
.stChatInput [contenteditable] {
    background: rgba(255,255,255,0.5) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    min-height: 24px !important;
    outline: none !important;
    caret-color: #f59e6f !important;
    color: #2d2a3e !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.04) !important;
}
.stChatInput [contenteditable]:empty:before {
    content: attr(data-placeholder);
    color: #9c94a8 !important;
    pointer-events: none;
    font-style: normal !important;
}
.stChatInput textarea:focus {
    border-color: transparent !important;
    box-shadow: none !important;
}
.stChatInput textarea::placeholder { color: #9c94a8 !important; }
.stChatInput button {
    background: linear-gradient(135deg,#f59e6f,#f7b384) !important;
    border-radius: 14px !important;
    width: auto !important; height: 38px !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(245,158,111,0.25) !important;
    transition: all 0.2s ease !important;
    margin-left: 8px !important;
    padding: 0 18px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    border: none !important;
    letter-spacing: 0.3px !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
}
.stChatInput button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(245,158,111,0.4) !important;
}
.stChatInput button:active {
    transform: translateY(0);
}
.stChatInput button::after { content: "Send →"; font-size: 13px; }

.typing-wrap {
    display: flex; align-items: center; gap: 10px; padding: 4px 0; margin-bottom: 14px;
    opacity: 0; animation: mIn 0.25s ease-out forwards;
}
.typing-dots {
    display: flex; gap: 5px; padding: 14px 20px;
    background: rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.06);
    border-radius: 18px; border-bottom-left-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.typing-dots span {
    width: 9px; height: 9px; background: #f59e6f; border-radius: 50%;
    animation: tB 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes tB { 0%,60%,100% { transform: translateY(0); opacity: 0.15; } 30% { transform: translateY(-10px); opacity: 0.9; } }

.chart-msg { opacity: 0; animation: mIn 0.5s ease-out 0.1s forwards; }
</style>
""", unsafe_allow_html=True)

if not NEO4J_PASSWORD:
    st.warning("Configure your Neo4j credentials in the .env file.")
    st.stop()

service = DormSearchService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
agent = Agent(service)
llm_available = agent.is_available()

page_header("Dormitory Q&A Agent")

if llm_available:
    provider = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("LLM_MODEL", "qwen2.5:7b")
    info_banner(f"LLM: <strong>{model}</strong> via {provider}")
else:
    info_banner("No LLM connected. I'll use keyword matching to answer your questions.")

with service.driver.session() as s:
    rc = s.run("MATCH (r:Room) RETURN count(r) AS c").single()["c"]
    ac = s.run("MATCH (a:ACUnit) RETURN count(a) AS c").single()["c"]
    sc = s.run("MATCH (s:Sensor) RETURN count(s) AS c").single()["c"]
    ec = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

animated_metrics([
    {"label": "Rooms", "value": rc, "color": "f59e6f"},
    {"label": "AC Units", "value": ac, "color": "d4a56a"},
    {"label": "Sensors", "value": sc, "color": "7bab7a"},
    {"label": "Relationships", "value": ec, "color": "b89abe"},
])


def render_chart(content):
    ts = content["chart"]
    label = ts.get("label", "Time Series")
    st.markdown('<div class="chart-msg">', unsafe_allow_html=True)
    animated_chart(ts, title=label)
    st.markdown('</div>', unsafe_allow_html=True)


def write_message(role, text):
    a = "u" if role == "user" else "a"
    avatar_content = "🙋" if role == "user" else "🤖"
    avatar = f'<div class="msg-avatar {a}">{avatar_content}</div>'
    bubble_class = "user" if role == "user" else "assistant"
    st.markdown(
        f'<div class="msg-row {role}">'
        + (avatar if role == "assistant" else "")
        + f'<div class="msg-body"><div class="msg-bubble {bubble_class}">{text}</div></div>'
        + (avatar if role == "user" else "")
        + '</div>',
        unsafe_allow_html=True
    )


def show_typing():
    st.markdown(
        '<div class="typing-wrap">'
        '<div class="msg-avatar a">🤖</div>'
        '<div class="typing-dots"><span></span><span></span><span></span></div>'
        "</div>",
        unsafe_allow_html=True
    )


if "messages" not in st.session_state:
    st.session_state.messages = []

if "thinking" not in st.session_state:
    st.session_state.thinking = False

if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-card">
        <span class="emoji">👋</span>
        <h2>Hey there! How can I help you?</h2>
        <p>Ask me anything about the dormitory — rooms, AC units, sensors, and more.</p>
        <div class="welcome-suggestions">
            <span class="welcome-chip">🏠 Show all rooms</span>
            <span class="welcome-chip">❄️ Which rooms have AC?</span>
            <span class="welcome-chip">🌡️ Temperature data for Room01</span>
            <span class="welcome-chip">📊 How many sensors?</span>
            <span class="welcome-chip">➕ Add a room called Room09</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

for msg in st.session_state.messages:
    if isinstance(msg["content"], list):
        for item in msg["content"]:
            if isinstance(item, dict) and "chart" in item:
                render_chart(item)
            else:
                write_message("assistant", str(item))
    else:
        write_message(msg["role"], msg["content"])

with st.expander("Try these questions", expanded=False):
    st.markdown("""
    **Time series:**
    - "Show temperature data for Room01"
    - "Show power readings for AC1"
    - "Chart humidity for Room02"

    **Graph queries:**
    - "How many rooms, AC units, and sensors are there?"
    - "Tell me about Room01"
    - "What serves Room01?"
    - "What AC is located in Room07?"

    **Add / Delete:**
    - "Add a room called Room09"
    - "Delete Room09"
    """)

st.markdown('<div id="chat-end"></div>', unsafe_allow_html=True)

st.markdown(
    "<script>var e=document.getElementById('chat-end'); if(e) e.scrollIntoView({behavior:'smooth'});</script>",
    unsafe_allow_html=True
)

prompt = st.chat_input("Ask about the dormitory...", disabled=st.session_state.thinking)

if prompt and not st.session_state.thinking:
    st.session_state.thinking = True
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.thinking:
    last_prompt = st.session_state.messages[-1]["content"] if st.session_state.messages else ""

    with st.chat_message("user"):
        write_message("user", last_prompt)

    show_typing()

    result = route_query(last_prompt, service)

    if result == [None]:
        reply_text = "Which node would you like details about? Please specify a room, AC unit, or sensor."
        st.session_state.messages.append({"role": "assistant", "content": reply_text})
    elif result[0] is FALLBACK:
        if llm_available:
            reply_text = agent.ask(last_prompt)
        else:
            reply_text = "I couldn't find anything matching your question. Try asking about rooms, AC units, or sensors."
        st.session_state.messages.append({"role": "assistant", "content": reply_text})
    else:
        st.session_state.messages.append({"role": "assistant", "content": result})

    st.session_state.thinking = False
    st.rerun()

service.close()
