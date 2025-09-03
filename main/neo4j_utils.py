from neo4j import GraphDatabase  # Import Neo4j driver for database connection
import tempfile                 # For creating temporary files to store HTML
from pyvis.network import Network  # For visualizing graphs in HTML
import streamlit as st          # For displaying in Streamlit web app


# --- FUNCTIONS ---

def get_neo4j_driver(uri, user, password):
    """
    Create and return a Neo4j driver.

    Args:
        uri (str): Neo4j connection URI.
        user (str): Neo4j username.
        password (str): Neo4j password.

    Returns:
        GraphDatabase.driver: A Neo4j driver instance.
    """
    return GraphDatabase.driver(uri, auth=(user, password))

def query_graph(session, query):
    """
    Run a query on the Neo4j graph database.

    Args:
        session (neo4j.Session): Neo4j session to run the query.
        query (str): Cypher query to execute.

    Returns:
        list: A list of dictionaries containing query results.
    """
    results = session.run(query)
    # Extract source, relationship, and target from each record
    return [
        {
            "source": record["source"],
            "relationship": record["relationship"],
            "target": record["target"]
        }
        for record in results
    ]

def display_neo4j_graph(neo4j_uri, user, password):

    st.markdown("### Run Custom Cypher Command")
    cypher_query = st.text_area("Enter Cypher command to modify the graph (e.g., CREATE, MERGE, DELETE, etc.)", height=68)
    run_query = st.button("Run Cypher Command", key="run_cypher_btn")

    if run_query and cypher_query.strip():
        try:
            driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
            with driver.session() as session:
                session.run(cypher_query)
            st.session_state["cypher_success"] = True
        except Exception as e:
            st.error(f"Error running Cypher command: {e}")

    if st.session_state.get("cypher_success"):
        st.success("Cypher command executed successfully!")
        st.session_state["cypher_success"] = False  # Reset after showing

    if st.button("Refresh Graph"):
        st.rerun()  # Only rerun when this button is pressed

    driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
    node_data = {}
    edges = []

    with driver.session() as session:
        result = session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100")
        for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]
            node_data[n.id] = {"props": dict(n), "labels": list(n.labels)}
            node_data[m.id] = {"props": dict(m), "labels": list(m.labels)}
            edges.append((n.id, m.id, r.type))

    net = Network(height="500px", width="100%", notebook=False)

    label_to_color = {
        "Dorm": "#388E3C",           # green
        "MechanicalRoom": "#C62828", # red
        "ACUnit": "#1565C0"          # blue
    }

    sensor_type_colors = {
        "temperature": "#F57C00",    # orange
        "occupancy": "#FBC02D"       # yellow
    }

    for node_id, data in node_data.items():
        props = data["props"]
        labels = data["labels"]

        if not props and not labels:
            continue

        node_label = ""  # No label text on node

        color = "#757575"  # default gray
        if "Room" in labels:
            if props.get("room_type") == "mechanical_room":
                color = label_to_color["MechanicalRoom"]
            else:
                color = label_to_color["Dorm"]
        elif "ACUnit" in labels:
            color = label_to_color["ACUnit"]
        elif "Sensor" in labels:
            sensor_type = props.get("type", "").lower()
            color = sensor_type_colors.get(sensor_type, color)

        net.add_node(node_id, label=node_label, title=str(props), color=color)

    existing_node_ids = set(net.node_ids)
    for src, dst, rel in edges:
        if src in existing_node_ids and dst in existing_node_ids:
            net.add_edge(src, dst, label=rel, length=100)  # Increased length

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.write_html(tmp_file.name)
        html = open(tmp_file.name, "r").read()

    # Add toolbar buttons
    button_html = """
    <style>
    .graph-toolbar {
        position: absolute;
        top: 18px;
        right: 28px;
        z-index: 1000;
        display: flex;
        flex-direction: row;
        gap: 6px;
        background: rgba(255,255,255,0.85);
        border-radius: 6px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.12);
        padding: 4px 8px;
        align-items: center;
        transition: opacity 0.2s;
    }
    .graph-toolbar button {
        background: none;
        border: none;
        padding: 4px 6px;
        font-size: 16px;
        cursor: pointer;
        outline: none;
        border-radius: 3px;
        transition: background 0.18s;
        color: #444;
        display: flex;
        align-items: center;
    }
    .graph-toolbar button:hover {
        background: #e0e0e0;
    }
    .graph-toolbar .material-icons {
        font-size: 18px;
        vertical-align: middle;
    }
    .vis-network:fullscreen {
        background: #fff !important;
    }
    .vis-network:fullscreen .graph-toolbar,
    .graph-toolbar:fullscreen {
        position: fixed !important;
        top: 18px !important;
        right: 28px !important;
        z-index: 2000 !important;
        opacity: 1 !important;
        display: flex !important;
    }
    </style>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <div class="graph-toolbar" id="graph-toolbar">
        <button title="Center Graph" onclick="centerGraph()"><span class="material-icons">center_focus_strong</span></button>
        <button title="Zoom In" onclick="zoomInGraph()"><span class="material-icons">zoom_in</span></button>
        <button title="Zoom Out" onclick="zoomOutGraph()"><span class="material-icons">zoom_out</span></button>
        <button title="Full Screen" onclick="toggleFullScreen()"><span class="material-icons">fullscreen</span></button>
        <button title="Group by AC Unit" onclick="groupByACUnit()"><span class="material-icons">account_tree</span></button>
    </div>
    <script>
    let acUnitGrouped = false;

    function centerGraph() {
        if (window.network) window.network.fit();
    }
    function zoomInGraph() {
        if (window.network) {
            let scale = window.network.getScale();
            window.network.moveTo({scale: scale * 1.2});
        }
    }
    function zoomOutGraph() {
        if (window.network) {
            let scale = window.network.getScale();
            window.network.moveTo({scale: scale / 1.2});
        }
    }
    function toggleFullScreen() {
        var el = document.querySelector('.vis-network');
        if (!el) return;
        if (!document.fullscreenElement) {
            if (el.requestFullscreen) el.requestFullscreen();
            else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
            else if (el.msRequestFullscreen) el.msRequestFullscreen();
        } else {
            if (document.exitFullscreen) document.exitFullscreen();
            else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
            else if (document.msExitFullscreen) document.msExitFullscreen();
        }
    }
    function groupByACUnit() {
        if (window.network) {
            if (!acUnitGrouped) {
                window.network.setOptions({
                    layout: {
                        hierarchical: {
                            enabled: true,
                            direction: "LR",
                            sortMethod: "hubsize"
                        }
                    },
                    physics: {
                        hierarchicalRepulsion: {
                            nodeDistance: 150
                        }
                    }
                });
            } else {
                window.network.setOptions({
                    layout: {
                        hierarchical: {
                            enabled: false
                        }
                    },
                    physics: {
                        forceAtlas2Based: {
                            gravitationalConstant: -50,
                            centralGravity: 0.01,
                            springLength: 150,
                            springConstant: 0.08
                        },
                        maxVelocity: 50,
                        solver: "forceAtlas2Based",
                        timestep: 0.35,
                        stabilization: { iterations: 150 }
                    }
                });
            }
            acUnitGrouped = !acUnitGrouped;
        }
    }
    document.addEventListener('fullscreenchange', function() {
        var el = document.querySelector('.vis-network');
        var toolbar = document.getElementById('graph-toolbar');
        if (document.fullscreenElement && el && toolbar) {
            el.appendChild(toolbar);
        } else if (!document.fullscreenElement && toolbar) {
            document.body.appendChild(toolbar);
        }
    });
    </script>
    """

    # Add legend HTML for graph node color meanings
    legend_html = """
    <style>
    .legend-box {
        position: absolute;
        bottom: 20px;
        left: 20px;
        background: rgba(255,255,255,0.9);
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 6px;
        font-size: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .legend-item {
        display: flex;
        align-items: center;
        margin-bottom: 4px;
    }
    .legend-color {
        width: 14px;
        height: 14px;
        margin-right: 6px;
        border: 1px solid #555;
    }
    </style>
    <div class="legend-box">
        <div class="legend-item"><div class="legend-color" style="background:#1565C0;"></div>AC Unit</div>
        <div class="legend-item"><div class="legend-color" style="background:#388E3C;"></div>Dorm</div>
        <div class="legend-item"><div class="legend-color" style="background:#C62828;"></div>Mechanical Room</div>
        <div class="legend-item"><div class="legend-color" style="background:#F57C00;"></div>Temperature Sensor</div>
        <div class="legend-item"><div class="legend-color" style="background:#FBC02D;"></div>Occupancy Sensor</div>
    </div>
    """

    # Inject the toolbar and legend HTML into the generated Pyvis HTML
    # This ensures the controls and legend appear above the graph visualization
    html = html.replace("</body>", f"{button_html}{legend_html}</body>")

    # Display the final interactive graph in Streamlit with custom toolbar and legend
    st.components.v1.html(html, height=600, scrolling=True)
