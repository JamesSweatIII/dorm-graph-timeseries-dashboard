import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage


SYSTEM_PROMPT = """You are a precise dormitory management assistant. You have access to a Neo4j knowledge graph (rooms, AC units, sensors) and time-series data.

CRITICAL RULES — You MUST follow these every time:

1. ALWAYS use `query_knowledge_graph` to look up entities, relationships, counts, or aggregations. NEVER guess or infer from memory.

2. ALWAYS use `fetch_time_series_metrics` for any numerical reading (temperature, humidity, power, load, etc.). NEVER invent metric values.

3. If a tool returns empty, null, or an error, say "I don't have enough information to answer that" and ask the user to clarify.

4. Break complex questions into multiple tool calls. For example: first find the entity, then query its metrics. The tools can be called sequentially.

Available node labels:
  - Room (properties: room_id, room_type)
  - ACUnit (properties: ac_id)
  - Sensor (properties: sensor_id, type)

Relationship types: :SERVICES, :LOCATED_IN, :HAS_SENSOR, :MONITORS

Useful Cypher patterns:
  - MATCH (r:Room) RETURN r.room_id, r.room_type
  - MATCH (a:ACUnit)-[:SERVICES]->(r:Room) RETURN a.ac_id, r.room_id
  - MATCH (a:ACUnit)-[:LOCATED_IN]->(r:Room) RETURN a.ac_id, r.room_id
  - MATCH (r:Room)-[:HAS_SENSOR]->(s:Sensor) RETURN r.room_id, s.sensor_id, s.type
  - MATCH (s:Sensor)-[:MONITORS]->(a:ACUnit) RETURN s.sensor_id, a.ac_id
  - For averages: MATCH (r:Room)-[:HAS_SENSOR]->(s:Sensor {type:'temperature'}) RETURN count(DISTINCT r) AS rooms, count(s) AS sensors
  - For counts: MATCH (n) RETURN count(n) AS total

Rooms are zero-padded (Room01, Room02...). If a user says "room 1", query for "Room01".

If you cannot determine the answer from the tools, say "I don't know" and ask for clarification."""


class Agent:
    def __init__(self, service, model=None, base_url=None, api_key=None):
        self.service = service
        self.model = model or os.getenv("LLM_MODEL", "qwen2.5:7b")
        base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        api_key = api_key or os.getenv("LLM_API_KEY", "ollama")

        @tool
        def query_knowledge_graph(cypher_query: str) -> str:
            """Execute a Cypher query against the Neo4j knowledge graph. Use this to look up rooms, AC units, sensors, their relationships, counts, and aggregations (avg, min, max). Returns JSON results."""
            return self.service.query_knowledge_graph(cypher_query)

        @tool
        def fetch_time_series_metrics(entity_id: str, metric: str = "") -> str:
            """Fetch 24-hour time series readings for a node. Use for temperature, humidity, power, load data. entity_id is the node name (e.g. Room01, AC1, T01). metric is optional: 'temperature', 'humidity', 'power_kw', 'load_pct', 'value', or leave empty for all."""
            return self.service.fetch_time_series_metrics(entity_id, metric)

        self.tools = [query_knowledge_graph, fetch_time_series_metrics]

        try:
            self.llm = ChatOpenAI(
                model=self.model,
                base_url=base_url,
                api_key=api_key,
                temperature=0.05,
            )
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        except Exception as e:
            self.llm = None
            self.llm_with_tools = None

        self.messages = [SystemMessage(content=SYSTEM_PROMPT)]

    def is_available(self):
        return self.llm is not None

    def _call_tool(self, name, args):
        fn_map = {
            "query_knowledge_graph": self.service.query_knowledge_graph,
            "fetch_time_series_metrics": self.service.fetch_time_series_metrics,
        }
        fn = fn_map.get(name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            return fn(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def ask(self, user_input):
        if not self.llm:
            return None

        self.messages.append(HumanMessage(content=user_input))
        max_turns = 10

        for _ in range(max_turns):
            try:
                response = self.llm_with_tools.invoke(self.messages)
            except Exception as e:
                return f"LLM error: {e}"

            if not response.tool_calls:
                self.messages.append(response)
                return response.content

            self.messages.append(response)

            for tc in response.tool_calls:
                result = self._call_tool(tc.name, tc.args)
                self.messages.append(ToolMessage(content=result, tool_call_id=tc.id))

        return "I've reached the maximum number of reasoning steps. Please try a simpler question."

    def reset(self):
        self.messages = [SystemMessage(content=SYSTEM_PROMPT)]
