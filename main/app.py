# --- IMPORTS ---
# Importing necessary libraries for UI, database connections, LLMs, and data processing.
import os
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
from pymongo import MongoClient
import openai
import google.generativeai as genai
from load_graph import load_dorm_graph, fetch_graph_data
from utils import chunk_text, cosine_similarity, validate_openai_api_key
from neo4j_utils import display_neo4j_graph
from time_series_generator import get_sensor_data
from data_storage import (
    has_valid_sensor_data,
    save_sensor_data_to_mongo,
    fetch_mongo_documents,
    combine_documents_by_room,
    prepare_sensor_data_for_mongo
)
from utils import get_embedding
from openai import OpenAI
import numpy as np

# --- SETTINGS FOR DATABASES AND STORAGE ---
# Loading environment variables for secure database and API configurations.

# Load environment variables from .env file
load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION")
VECTOR_INDEX_COLLECTION = os.environ.get("VECTOR_INDEX_COLLECTION")

# --- MONGODB CONNECTION SETUP ---
# Connecting to MongoDB and selecting collections for storing and retrieving data.
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTION]
index_collection = db[VECTOR_INDEX_COLLECTION]

# --- STREAMLIT PAGE CONFIGURATION ---
# Setting up the Streamlit app's title and page configuration.
st.set_page_config(page_title="Dorm Query Assistant")
st.title("Dorm Sensor Data Assistant")

# --- API KEY INPUT FOR OPENAI ---
# Prompting the user to input their OpenAI API key for LLM operations.
api_key = st.text_input("Enter your OPENAI API key", type="password")

# --- OPENAI API KEY SETUP ---
# Validating the OpenAI API key and initializing the OpenAI client.
if api_key:
    if validate_openai_api_key(api_key):
        os.environ["OPENAI_API_KEY"] = api_key
        openai.api_key = api_key
        client = OpenAI(api_key=api_key)
    else:
        st.stop()  # Stop execution if the key is invalid

# --- FORCE REINDEX BUTTON ---
# Allowing the user to reindex data by regenerating sensor data, embeddings, and graph data.
if st.button("Force Reindex Data"):
    if NEO4J_PASSWORD:
        with st.spinner("Reindexing all data sources. Please wait..."):
            # 1. Load and index Neo4j graph data (building structure)
            with st.spinner("Loading and indexing Neo4j graph data..."):
                load_dorm_graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
                graph_docs = fetch_graph_data(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            # 2. Clear old sensor data from MongoDB
            with st.spinner("Clearing old sensor data from MongoDB..."):
                collection.delete_many({})
            # 3. Generate and save new synthetic sensor data (6 days, 5-min intervals)
            with st.spinner("Generating new synthetic sensor data..."):
                sensor_data = get_sensor_data(start_date="2025-01-01", days=7, interval_minutes=5)
                st.session_state["sensor_data"] = sensor_data
                prepared = prepare_sensor_data_for_mongo(sensor_data)
            if prepared:
                try:
                    with st.spinner("Saving sensor data to MongoDB..."):
                        save_sensor_data_to_mongo(prepared, collection)
                except ValueError as e:
                    st.error(f"Error saving sensor data: {e}")
            else:
                st.warning("No sensor data to index.")
            # 4. Fetch and combine all documents for indexing (room-day and graph)
            with st.spinner("Processing and combining documents for indexing..."):
                mongo_raw = list(collection.find({}))  # Get raw dicts from MongoDB
                sensor_docs = combine_documents_by_room(mongo_raw)
                all_docs = sensor_docs + graph_docs
            st.success(f"Processed {len(mongo_raw)} MongoDB records into {len(sensor_docs)} room-level documents.")
            st.success(f"Integrated {len(graph_docs)} graph documents, resulting in {len(all_docs)} total documents for indexing.")
            # 5. Generate and store embeddings for similarity search (RAG)
            with st.spinner("Generating and storing embeddings for similarity search..."):
                doc_texts = [doc.text for doc in all_docs]
                doc_embeddings = []
                for text in doc_texts:
                    try:
                        embedding = get_embedding(text, client)
                        doc_embeddings.append(embedding)
                    except openai.BadRequestError as e:
                        if "maximum context length" in str(e):
                            st.warning(f"Document text too long ({len(text)} chars), chunking...")
                            chunks = chunk_text(text)
                            embedding = get_embedding(chunks[0], client)
                            doc_embeddings.append(embedding)
                        else:
                            raise e
                st.session_state["doc_texts"] = doc_texts
                st.session_state["doc_embeddings"] = doc_embeddings
            # Save index metadata in MongoDB for persistence
            with st.spinner("Saving index metadata..."):
                index_collection.delete_many({})
                index_collection.insert_one({
                    "index_created": True, 
                    "timestamp": datetime.now().isoformat(),
                    "doc_count": len(doc_texts)
                })
            st.success("Reindex complete! Embeddings stored in session state!")
    else:
        st.warning("Please configure your Neo4j password before reindexing.")

# --- MAIN TABS FOR THE APPLICATION ---
# Creating tabs for different functionalities: QA Assistant, Graph View, Time Series Data, Predictive Model, and Fine-Tuning.
tabs = st.tabs(["QA Assistant", "Graph View", "Time Series Data", "Predective Model",  "Fine-Tuning"])

# --- QA ASSISTANT TAB ---
# Enabling natural language Q&A over dorm sensor and graph data using embeddings and LLMs.
with tabs[0]:
    if api_key and NEO4J_PASSWORD:
        # Configure Google Generative AI (if used)
        os.environ["GOOGLE_API_KEY"] = api_key
        genai.configure(api_key=api_key)

        # Ensure sensor data is available before allowing Q&A
        if not has_valid_sensor_data(collection):
            st.error("No data available. Please reindex.")
            st.stop()

        # Ensure embeddings are available in session state
        if "doc_texts" not in st.session_state or "doc_embeddings" not in st.session_state:
            has_index = index_collection.find_one({"index_created": True})
            if not has_index:
                st.error("No saved index found; please reindex.")
                st.stop()
            else:
                st.error("Session state lost. Please reindex to restore embeddings.")
                st.stop()

        # Clear QA input if requested (for follow-up questions)
        if st.session_state.get("clear_qa_input", False):
            st.session_state["qa_input"] = ""
            st.session_state["clear_qa_input"] = False

        st.success("Data indexed. Ask your questions below:")

        # User input for natural language questions
        user_input = st.text_input(
            "Ask a question about the dorms (sensors or structure)",
            key="qa_input"
        )
        
        # Only process if user input is new
        if user_input and st.session_state.get("last_qa_input", "") != user_input:
            st.session_state["last_qa_input"] = user_input

            # 1. Embed the user query for semantic search
            embedded_query = get_embedding(user_input, client)
            
            # 2. Similarity search with document embeddings
            doc_texts = st.session_state.get("doc_texts", [])
            doc_embeddings = st.session_state.get("doc_embeddings", [])
            if doc_texts and doc_embeddings:
                similarities = [cosine_similarity(embedded_query, emb) for emb in doc_embeddings]
                top_k = 50  # Retrieve the top 50 most relevant documents
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                
                # 3. Truncate and extract relevant context for the LLM
                MAX_DOC_TOKENS = 2500  # Estimate for LLM context window
                truncated_docs = []
                for idx in top_indices:
                    doc = doc_texts[idx]
                    # Smart truncation: extract only the most relevant sections for the LLM
                    if "Room ID:" in doc and "TEMPERATURE DATA:" in doc:
                        sections = doc.split("\n\n")
                        room_info = next((s for s in sections if "Room ID:" in s), "")
                        temp_summary = next((s for s in sections if "TEMPERATURE DATA:" in s 
                                            and ("Average temperature:" in s or "Minimum temperature:" in s)), "")
                        profile_info = next((s for s in sections if "Room profile:" in s), "")
                        reading_section = next((s for s in sections if "Sample temperature readings:" in s), "")
                        sample_readings = "\n".join(reading_section.split("\n")[:15]) if reading_section else ""
                        smart_truncated = f"{room_info}\n\n{temp_summary}\n\n{profile_info}\n\n{sample_readings}"
                        truncated_docs.append(smart_truncated)
                    else:
                        # Fallback: truncate long docs to fit context window
                        if len(doc) > MAX_DOC_TOKENS * 4:
                            truncated_docs.append(doc[:MAX_DOC_TOKENS * 4] + "...[truncated]")
                        else:
                            truncated_docs.append(doc)
                context_str = "\n\n".join(truncated_docs)
            else:
                context_str = ""
                st.warning("No document embeddings found. Please reindex data.")

            # 4. Send the user query and context to the LLM for a generative answer
            with st.spinner("Thinking…"):
                if context_str:
                    prompt = f"""You are a helpful assistant for dorm sensor data. Answer the user's question based on the context below.
                                                
                            Context from dorm data:
                            {context_str}

                            User question: {user_input}

                            The data contains temperature readings from various rooms with attributes such as:
                            - temperature_celsius: The temperature reading
                            - room_id: The identifier for the room (e.g., Room6)
                            - room_profile: Usage pattern of the room (e.g., night_student)
                            - exposure: Whether the room is sunny or shaded
                            - ac_status: Whether the AC is ON or OFF
                            - temperature_status: Categorization of temperature (Comfortable, Hot, Cold)

                            Answer the user's question based only on the provided context. If the context doesn't contain the answer, say you don't have that information.
                            Make sure to provide specific values when available (e.g., exact temperatures, room IDs, times).
                            """
                else:
                    prompt = f"You are a helpful assistant for dorm sensor data. User question: {user_input}"
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant for dorm sensor data. Be concise and specific when answering questions."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=400,
                        temperature=0.3
                    )
                    st.write("### Answer:")
                    answer = response.choices[0].message.content
                    st.markdown(answer)

                    # Show the context used for the answer
                    with st.expander("Show context used for this answer"):
                        st.markdown("#### Context provided to the LLM:")
                        st.markdown(f"```text\n{context_str}\n```")

                    if st.button("Ask a follow-up question"):
                        st.session_state["clear_qa_input"] = True
                        st.rerun()
                except openai.RateLimitError as e:
                    st.error("Error: Token limit exceeded. Try asking a more specific question.")
                    st.info("Tip: For better results, focus your question on a specific room or time period.")

        # Reset QA input if needed
        if st.session_state.get("clear_qa_input", False):
            st.session_state["qa_input"] = ""
            st.session_state["clear_qa_input"] = False

    elif not api_key:
        st.warning("Please enter your OPENAI API key.")
    elif not NEO4J_PASSWORD:
        st.warning("Please configure your Neo4j password.")

# --- GRAPH VIEW TAB ---
# Displaying an interactive visualization of the dorm's graph structure using Neo4j.
with tabs[1]:
    if api_key and NEO4J_PASSWORD:
        # Display an interactive visualization of the building's graph structure
        display_neo4j_graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    else:
        st.warning("Enter your OPENAI API key and Neo4j password to view the graph.")

# --- TIME SERIES DATA TAB ---
# Allowing users to explore raw and processed sensor data for occupancy and temperature.
with tabs[2]:
    if not api_key:
        st.warning("Please enter your OPENAI API key to view time series data.")
    else:
        sensor_data = st.session_state.get("sensor_data", None)
        if sensor_data:
            st.write("Showing most recently generated sensor data:")
            room_ids = sorted(sensor_data.keys())
            selected_room = st.selectbox("Select a room", room_ids)
            room = sensor_data[selected_room]
            sub_tabs = st.tabs(["Occupancy", "Temperature"])
            with sub_tabs[0]:
                if "occupancy" in room:
                    occ_columns = list(room["occupancy"].columns)
                    selected_occ_columns = st.multiselect(
                        "Select occupancy columns to display",
                        occ_columns,
                        default=occ_columns,
                        key="occ_cols"
                    )
                    st.markdown(
                        """
                        <div style="background-color:#e3f2fd; border:2px solid #2196f3; border-radius:8px; padding:18px; margin-bottom:18px;">
                        <b>Occupancy:</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.dataframe(
                        room["occupancy"][selected_occ_columns] if selected_occ_columns else room["occupancy"],
                        height=500
                    )
                else:
                    st.info("No occupancy data for this room.")
            with sub_tabs[1]:
                if "temperature" in room:
                    temp_columns = list(room["temperature"].columns)
                    selected_temp_columns = st.multiselect(
                        "Select temperature columns to display",
                        temp_columns,
                        default=temp_columns,
                        key="temp_cols"
                    )
                    st.markdown(
                        """
                        <div style="background-color:#fff3e0; border:2px solid #ff9800; border-radius:8px; padding:18px; margin-bottom:18px;">
                        <b>Temperature:</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.dataframe(room["temperature"][selected_temp_columns] if selected_temp_columns else room["temperature"], height=500)
                else:
                    st.info("No temperature data for this room.")
        else:
            # If no new data, fall back to MongoDB-stored data for demo robustness
            st.write("No new sensor data generated in this session. Showing data from MongoDB:")
            mongo_data = fetch_mongo_documents(collection)
            if mongo_data:
                room_ids = sorted({
                    doc.get("room_id", "Unknown")
                    for doc in mongo_data
                    if isinstance(doc, dict)
                })
                selected_room = st.selectbox("Select a room", room_ids)
                room_docs = [
                    doc for doc in mongo_data
                    if isinstance(doc, dict) and doc.get("room_id", "Unknown") == selected_room
                ]
                sub_tabs = st.tabs(["Occupancy", "Temperature"])
                with sub_tabs[0]:
                    occ_docs = [doc for doc in room_docs if doc.get("type") == "occupancy"]
                    if occ_docs:
                        for doc in occ_docs:
                            data = doc.get("data", [])
                            if data and isinstance(data, list) and isinstance(data[0], dict):
                                columns = list(data[0].keys())
                                selected_columns = st.multiselect(
                                    "Select occupancy columns to display",
                                    columns,
                                    default=columns,
                                    key="mongo_occ_cols"
                                )
                                filtered_data = [
                                    {k: row.get(k) for k in selected_columns}
                                    for row in data
                                ]
                                st.markdown(
                                    """
                                    <div style="background-color:#e3f2fd; border:2px solid #2196f3; border-radius:8px; padding:12px; margin-bottom:16px;">
                                    <b>Occupancy:</b>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                                st.dataframe(filtered_data)
                            else:
                                st.json(doc)
                    else:
                        st.info("No occupancy data for this room.")
                with sub_tabs[1]:
                    temp_docs = [doc for doc in room_docs if doc.get("type") == "temperature"]
                    if temp_docs:
                        for doc in temp_docs:
                            data = doc.get("data", [])
                            if data and isinstance(data, list) and isinstance(data[0], dict):
                                columns = list(data[0].keys())
                                selected_columns = st.multiselect(
                                    "Select temperature columns to display",
                                    columns,
                                    default=columns,
                                    key="mongo_temp_cols"
                                )
                                filtered_data = [
                                    {k: row.get(k) for k in selected_columns}
                                    for row in data
                                ]
                                st.markdown(
                                    """
                                    <div style="background-color:#fff3e0; border:2px solid #ff9800; border-radius:8px; padding:12px; margin-bottom:16px;">
                                    <b>Temperature:</b>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                                st.dataframe(filtered_data)
                            else:
                                st.json(doc)
                    else:
                        st.info("No temperature data for this room.")
            else:
                st.info("No time series data found.")

# --- FINE-TUNING TAB ---
# Placeholder for future options to fine-tune predictive models or LLMs.
with tabs[3]:
    if api_key and NEO4J_PASSWORD:
        st.write("Predictive Model options will be available soon.")
    else:
        st.warning("Enter your OPENAI API key and Neo4j password to view fine-tuning options.")

with tabs[4]:
    if api_key and NEO4J_PASSWORD:
        st.write("Fine-tuning options will be available soon.")
    else:
        st.warning("Enter your OPENAI API key and Neo4j password to view fine-tuning options.")