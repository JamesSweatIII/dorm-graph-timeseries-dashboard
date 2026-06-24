# Dorm-Graph-Timeseries-Dashboard

Streamlit Q&A agent over a Neo4j dormitory knowledge graph (rooms, AC units, sensors) with hybrid regex/LLM chat, mock time series data, and a polished animated chatbot UI.

## Architecture

- **`main/app.py`** — Streamlit entry point, professional chatbot UI with animated components
- **`main/animate_component.py`** — Python bridge that generates animated HTML components using `animate.js`
- **`lib/animate.js`** — Animation engine powering all UI animations (fade, slide, count-up, canvas charts, typing indicator, vis.js network)
- **`main/dorm_service.py`** — Neo4j query/mutation layer (20+ methods: CRUD for nodes, relationships, stats)
- **`main/query_router.py`** — Regex fast-path router with complexity heuristic and `FALLBACK` sentinel
- **`main/agent.py`** — LLM agent with OpenAI-compatible client, system prompt, and 20+ function tool definitions
- **`main/time_series.py`** — Generates mock 24h time series data (room temp/humidity, AC power/load, sensor values)
- **`main/load_graph.py`** — Seeds the Neo4j graph with rooms, AC units, sensors, and relationships

## Data Model

- `Room` — `room_id` (e.g. Room01), `room_type` (dorm, mechanical_room)
- `ACUnit` — `ac_id` (e.g. AC1)
- `Sensor` — `sensor_id` (e.g. T01), `type` (temperature, occupancy)

Relationships: `SERVICES`, `LOCATED_IN`, `HAS_SENSOR`, `MONITORS`

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

Create a `.env` file:

```
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=your_username
NEO4J_PASSWORD=your_password
```

Optional LLM configuration (uses OpenRouter by default):

```
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=qwen/qwen-2.5-72b-instruct
```

### Run

```bash
streamlit run main/app.py
```

## Features

- **Polished chatbot UI** — dark warm theme, chat bubbles with avatars, typing indicator, smooth animations
- **Animated metrics** — count-up cards with accent bars on load
- **Animated charts** — Canvas-based line charts that draw smoothly with gradient fill
- **Hybrid query routing** — simple queries handled instantly via regex, complex queries routed to LLM
- **Compound command support** — multi-step requests (e.g. "Add a room and connect it to AC1") handled by LLM

## Query Examples

**Simple (regex fast-path):**
- "Show all rooms"
- "Which rooms have AC?"
- "Where is AC1 located?"
- "Tell me about Room02"
- "Add a room called Room09"
- "Delete Room09"

**Complex (LLM-powered):**
- "Compare Room02 and Room03 with temperature data"
- "Get me rooms with temperature sensors but without occupancy sensors"
- "How many rooms, AC units, and sensors are there?"
- "What's the average number of sensors per room?"
- "Add a room called Room09 and connect it to AC1"
