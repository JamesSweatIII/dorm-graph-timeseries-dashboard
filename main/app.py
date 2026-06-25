import os
from dotenv import load_dotenv
import streamlit as st
from dorm_service import DormSearchService
from query_router import route_query, FALLBACK
from agent import Agent
from animate_component import animated_chart

load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

st.set_page_config(page_title="Dormitory Agent", layout="wide", initial_sidebar_state="expanded")

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
[data-testid="stSidebar"] { display: block; }
.stApp > .main > .block-container { z-index: 1; position: relative; }

.landing-wrap {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-height: calc(100vh - 200px); padding: 40px 0;
    opacity: 0; animation: wIn 0.5s ease-out 0.1s forwards;
}
@keyframes wIn { to { opacity: 1; } }
.landing-icon {
    font-size: 52px; margin-bottom: 16px; display: block; text-align: center;
}
.landing-title {
    font-size: 32px; font-weight: 700; color: #2d2a3e; text-align: center;
    margin: 0 0 8px; letter-spacing: -0.3px;
}
.landing-title span { color: #c77d4a; }
.landing-sub {
    font-size: 15px; color: #6b6578; text-align: center;
    margin: 0 0 28px; max-width: 440px; line-height: 1.5;
}
.landing-suggestions {
    display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
    max-width: 520px;
}
.landing-chip {
    background: rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.08);
    border-radius: 24px; padding: 10px 20px; color: #4a4560; font-size: 14px;
    cursor: pointer; transition: all 0.2s ease; font-family: inherit;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.landing-chip:hover {
    background: rgba(255,255,255,0.95); border-color: rgba(245,158,111,0.25);
    box-shadow: 0 2px 12px rgba(0,0,0,0.06); color: #c77d4a;
}

.landing-metrics {
    display: flex; gap: 24px; justify-content: center; margin-top: 36px;
    flex-wrap: wrap;
}
.landing-metric {
    text-align: center; padding: 8px 16px;
}
.landing-metric .lmv {
    font-size: 24px; font-weight: 700; color: #2d2a3e; font-variant-numeric:tabular-nums;
}
.landing-metric .lml {
    font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    color: rgba(0,0,0,0.35); margin-top: 2px;
}

.chat-area { margin-top: 8px; }

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

WEAK_MODEL = "qwen/qwen-2.5-72b-instruct"
STRONG_MODEL = "openai/gpt-4o-2024-11-20"

with st.sidebar:
    st.markdown("### Model")
    model_choice = st.selectbox(
        "Select model", ["Weak (Qwen 2.5)", "Strong (GPT-4o)"],
        label_visibility="collapsed"
    )
    selected_model = STRONG_MODEL if model_choice == "Strong (GPT-4o)" else WEAK_MODEL

    if "model" not in st.session_state or st.session_state.model != selected_model:
        st.session_state.model = selected_model
        st.session_state.agent = Agent(
            service,
            model=selected_model,
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("LLM_API_KEY", "ollama"),
        )
        st.session_state.agent.reset()
        st.session_state.messages = []

    st.caption(f"Using `{selected_model.split('/')[-1]}`")
    st.divider()
    st.caption("**Dormitory Q&A** — ask about rooms, AC units, sensors, and relationships in the knowledge graph.")

agent = st.session_state.agent
llm_available = agent.is_available()

with service.driver.session() as s:
    rc = s.run("MATCH (r:Room) RETURN count(r) AS c").single()["c"]
    ac = s.run("MATCH (a:ACUnit) RETURN count(a) AS c").single()["c"]
    sc = s.run("MATCH (s:Sensor) RETURN count(s) AS c").single()["c"]
    ec = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]


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
    st.markdown(f"""
    <div class="landing-wrap">
        <span class="landing-icon">🏠</span>
        <div class="landing-title">Dormitory <span>Q&A</span></div>
        <div class="landing-sub">Ask anything about your smart dormitory — rooms, AC units, sensors, and more.</div>
        <div class="landing-suggestions">
            <span class="landing-chip">🏠 Show all rooms</span>
            <span class="landing-chip">❄️ Which rooms have AC?</span>
            <span class="landing-chip">🌡️ Temperature for Room01</span>
            <span class="landing-chip">📊 How many sensors?</span>
            <span class="landing-chip">➕ Add a room called Room09</span>
        </div>
        <div class="landing-metrics">
            <div class="landing-metric"><div class="lmv">{rc}</div><div class="lml">Rooms</div></div>
            <div class="landing-metric"><div class="lmv">{ac}</div><div class="lml">AC Units</div></div>
            <div class="landing-metric"><div class="lmv">{sc}</div><div class="lml">Sensors</div></div>
            <div class="landing-metric"><div class="lmv">{ec}</div><div class="lml">Relationships</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        if isinstance(msg["content"], list):
            for item in msg["content"]:
                if isinstance(item, dict) and "chart" in item:
                    render_chart(item)
                else:
                    write_message("assistant", str(item))
        else:
            write_message(msg["role"], msg["content"])

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
