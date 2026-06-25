# Dorm-Graph-Timeseries-Dashboard

Streamlit Q&A agent over a Neo4j dormitory knowledge graph (rooms, AC units, sensors) with hybrid regex/LLM chat, mock time series data, and a polished animated chatbot UI.

Built by **James Sweat III** — MIT License.

## Overview

This application lets users ask natural-language questions about a smart dormitory's infrastructure — rooms, AC units, and sensors — and their relationships stored in a Neo4j graph database. It uses a **hybrid query routing** strategy: simple intents are handled instantly via regex, while complex questions are delegated to an LLM agent backed by function-calling tools. Results are displayed through a polished dark-themed chat interface with animated metrics, charts, and network visualizations.

## Architecture

```
User Input
    │
    ▼
┌─────────────────┐
│  query_router   │  ← Regex fast-path for simple queries
│  (route_query)  │     (show / add / delete nodes, connect relationships)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 Fast-pass    FALLBACK sentinel
 (returns     │
  text)       ▼
         ┌─────────┐
         │  agent   │  ← LangChain LLM with tool binding
         │ .ask()   │     (query_knowledge_graph,
         │          │      fetch_time_series_metrics)
         └────┬────┘
              │
              ▼
         ┌──────────────┐
         │ dorm_service │  ← Neo4j CRUD layer (20+ methods)
         └──────┬───────┘
              │
              ├─────────────────────┐
              ▼                     ▼
         ┌──────────────┐  ┌─────────────────┐
         │ time_series  │  │ animate_component│
         │ (mock 24h)   │  │ + animate.js     │
         └──────────────┘  └─────────────────┘
```

### Key Components

| File | Role |
|---|---|
| **`main/app.py`** | Streamlit entry point, professional chatbot UI with animated components, sidebar model selector, landing page with suggestion chips and live metrics |
| **`main/agent.py`** | LangChain-based LLM agent with OpenAI-compatible client, system prompt, and function tool definitions for Cypher queries and time series retrieval |
| **`main/animate_component.py`** | Python bridge that generates animated HTML/JS components rendered inside Streamlit iframes |
| **`lib/animate.js`** | Animation engine — count-up cards, canvas line charts with gradient fill, bar charts, vis.js network graph, typing indicator, slide/fade effects |
| **`main/dorm_service.py`** | Neo4j data access layer — CRUD for nodes, relationships, and graph statistics (20+ methods) |
| **`main/query_router.py`** | Regex fast-path router with complexity heuristic and `FALLBACK` sentinel for LLM delegation |
| **`main/time_series.py`** | Pseudo-random seeded mock 24-hour time series data generator (temperature, humidity, power, load, occupancy) |
| **`main/load_graph.py`** | Seeds the Neo4j graph with 8 rooms, 2 AC units, 12 sensors, and 21+ relationships |
| **`main/neo4j_utils.py`** | Shared Neo4j utility functions (connection, helpers) |

## Data Model

### Nodes

| Label | Key Properties |
|---|---|
| **`Room`** | `room_id` (e.g. `Room01`), `room_type` (`dorm` / `mechanical_room`) |
| **`ACUnit`** | `ac_id` (e.g. `AC1`) |
| **`Sensor`** | `sensor_id` (e.g. `T01`), `type` (`temperature` / `occupancy`) |

### Relationships

```
(:ACUnit)-[:SERVICES]->(:Room)         — AC unit serves a room
(:ACUnit)-[:LOCATED_IN]->(:Room)       — AC unit physically located in a room
(:Room)-[:HAS_SENSOR]->(:Sensor)       — Room has a sensor
(:Sensor)-[:MONITORS]->(:ACUnit)       — Sensor monitors an AC unit
```

### Seed Graph

The seed script creates:
- **8 rooms** — Room01–Room06 (dorm), Room07–Room08 (mechanical_room)
- **2 AC units** — AC1 (in Room07), AC2 (in Room08)
- **12 sensors** — Temp_ and Occ_ for each of 6 dorm rooms
- **21+ relationships** connecting them all

## Tech Stack

| Category | Technology |
|---|---|
| **Language** | Python 3.9+ |
| **Web Framework** | [Streamlit](https://streamlit.io) |
| **Graph Database** | [Neo4j](https://neo4j.com) (Aura or local) |
| **LLM Framework** | [LangChain](https://langchain.com) (`langchain-openai`) |
| **LLM Backend** | [OpenRouter](https://openrouter.ai) (default), also works with any OpenAI-compatible endpoint (Ollama, local LLMs, etc.) |
| **Models** | Claude Sonnet 4, GPT-4o, Gemini 2.5 Pro, DeepSeek-V3, Qwen 2.5 72B, Llama 3.3 70B, Gemini 2.0 Flash (user-selectable) |
| **Front-end** | Custom `animate.js` (vanilla JS, canvas-based, zero external deps) + [vis.js](https://visjs.org) for network graphs, [Tom Select](https://tom-select.js.org) for dropdowns |
| **Deployment** | [Render](https://render.com) via `render.yaml` |

## Quickstart

### Prerequisites

- Python 3.9+
- [Neo4j Aura](https://console.neo4j.io) (or local Neo4j) instance

### Setup

```bash
git clone https://github.com/your-username/Dorm-Graph-Timeseries-Dashboard.git
cd Dorm-Graph-Timeseries-Dashboard
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```ini
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=your_username
NEO4J_PASSWORD=your_password
```

Optional LLM configuration (uses OpenRouter by default):

```ini
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=qwen/qwen-2.5-72b-instruct
```

### Load Seed Data

```bash
python main/load_graph.py
```

### Run

```bash
streamlit run main/app.py
```

## Features

### 🎨 Polished Chatbot UI
Dark warm gradient theme, chat bubbles with user/assistant avatars, smooth CSS transitions, bouncing dots typing indicator, landing page with suggestion chips and live graph statistics.

### 📊 Animated Visualizations
- **Metrics cards** — count-up animation with colored accent bars on load
- **Line charts** — canvas-based smooth curves with gradient fill and draw animation
- **Network graph** — interactive vis.js force-directed graph of the knowledge graph

### 🧠 Hybrid Query Routing
- **Regex fast-path** — instantly handles simple queries: show, add, delete nodes, connect/disconnect relationships
- **LLM fallback** — routes complex, multi-step, or analytical questions to the LLM agent with 20+ tool definitions for precise Cypher generation

### 🔗 Compound Commands
Multi-step requests like *"Add a room called Room09 and connect it to AC1 with a temperature sensor"* are decomposed and executed by the LLM agent.

### 📈 Mock Time Series Data
Seeded deterministic 24-hour data generated on first request per node — room temperature/humidity, AC power/load, and sensor readings. No external data source required.

### 🔌 Flexible LLM Support
Compatible with any OpenAI-compatible API endpoint. 7 preset models from OpenRouter, or enter a custom model ID. Switch models on the fly from the sidebar.

## Query Examples

**Simple (regex fast-path):**
```
Show all rooms
Which rooms have AC?
Where is AC1 located?
Tell me about Room02
Add a room called Room09
Delete Room09
Connect AC2 to Room04
```

**Complex (LLM-powered):**
```
Compare Room02 and Room03 with temperature data
Get me rooms with temperature sensors but without occupancy sensors
How many rooms, AC units, and sensors are there?
What's the average number of sensors per room?
Add a room called Room09 and connect it to AC1
Show time series data for AC1
```

## Deploy on Render

This repository includes a `render.yaml` for one-click deployment on Render. Set the required environment variables (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `LLM_BASE_URL`, `LLM_API_KEY`) in the Render dashboard.

## License

MIT — see [LICENSE](LICENSE).
