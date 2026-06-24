# Dorm-Graph-Timeseries-Dashboard

Streamlit Q&A agent over a Neo4j dormitory knowledge graph (rooms, AC units, sensors) with hybrid regex/LLM chat and mock time series data.

## Architecture

- **`main/app.py`** — Streamlit entry point, hybrid chat flow (regex fast-path → LLM fallback)
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
