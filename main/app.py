import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from load_graph import load_dorm_graph
from dorm_service import DormSearchService
from query_router import route_query, FALLBACK
from agent import Agent

load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

st.set_page_config(page_title="Dormitory Agent", layout="wide")

if not NEO4J_PASSWORD:
    st.warning("Configure your Neo4j credentials in the .env file.")
    st.stop()

service = DormSearchService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

agent = Agent(service)
llm_available = agent.is_available()

st.title("Dormitory Q&A Agent")

if llm_available:
    provider = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("LLM_MODEL", "qwen2.5:7b")
    st.caption(f"LLM: {model} via {provider}")
else:
    st.info("No LLM configured. Set `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in your .env, or run Ollama locally. Falling back to keyword matching.")

with service.driver.session() as s:
    rc = s.run("MATCH (r:Room) RETURN count(r) AS c").single()["c"]
    ac = s.run("MATCH (a:ACUnit) RETURN count(a) AS c").single()["c"]
    sc = s.run("MATCH (s:Sensor) RETURN count(s) AS c").single()["c"]
    ec = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Rooms", rc)
col2.metric("AC Units", ac)
col3.metric("Sensors", sc)
col4.metric("Relationships", ec)


def render_assistant_content(content):
    if isinstance(content, list):
        items = content
    else:
        items = [content]
    for item in items:
        if isinstance(item, dict) and "chart" in item:
            ts = item["chart"]
            df = pd.DataFrame(ts["data"])
            for col in ts["columns"]:
                if col in ("time", "timestamp"):
                    continue
                cdf = df[["time", col]].copy()
                cdf.columns = ["time", "value"]
                st.write(f"**{col}**")
                st.line_chart(cdf.set_index("time")["value"])
        elif isinstance(item, dict) and "table" in item:
            st.dataframe(item["table"], use_container_width=True, hide_index=True)
        else:
            st.markdown(str(item))


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_assistant_content(msg["content"])

with st.expander("Try these questions"):
    st.markdown("""
    **Time series:**
    - "Show temperature data for Room01"
    - "Show power readings for AC1"
    - "Chart humidity for Room02"

    **Graph queries:**
    - "Get me rooms with temperature sensors but without occupancy sensors"
    - "How many rooms, AC units, and sensors are there?"
    - "What's the average number of sensors per room?"
    - "Tell me about Room01"
    - "What serves Room01?"
    - "What is located in Room07?"

    **Add / Delete:**
    - "Add a room called Room09"
    - "Add AC unit AC3"
    - "Add a temperature sensor T07"
    - "Delete Room09"
    - "Remove AC3"
    """)

prompt = st.chat_input("Ask a question about the dormitory...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Fast path: try regex router first (instant)
    result = route_query(prompt, service)

    if result == [None]:
        reply = "Which node would you like details about? Please specify a room, AC unit, or sensor."
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
    elif result[0] is FALLBACK:
        # Complex query → use LLM
        if llm_available:
            reply = agent.ask(prompt)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)
        else:
            reply = "I couldn't find anything matching your question. Try asking about rooms, AC units, or sensors."
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)
    else:
        st.session_state.messages.append({"role": "assistant", "content": result})
        with st.chat_message("assistant"):
            render_assistant_content(result)

    st.rerun()

service.close()
