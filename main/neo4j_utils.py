from neo4j import GraphDatabase
import streamlit as st
import pandas as pd


def get_graph_data(uri, user, password):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    nodes = []
    edges = []

    with driver.session() as session:
        result = session.run("MATCH (n) RETURN elementId(n) AS id, n, labels(n) AS labels")
        for record in result:
            nodes.append({
                "id": record["id"],
                "props": dict(record["n"]),
                "labels": record["labels"]
            })

        edge_result = session.run("MATCH (n)-[r]->(m) RETURN elementId(n) AS s, elementId(m) AS t, r.type AS type")
        for record in edge_result:
            edges.append({
                "source": record["s"],
                "target": record["t"],
                "type": record["type"]
            })

    driver.close()
    return nodes, edges


def node_display_name(props, labels):
    return props.get("room_id") or props.get("ac_id") or props.get("sensor_id") or "(unnamed)"


def node_type_label(labels, props):
    if "Room" in labels:
        return "Mechanical Room" if props.get("room_type") == "mechanical_room" else "Room"
    elif "ACUnit" in labels:
        return "AC Unit"
    elif "Sensor" in labels:
        return f"Sensor ({props.get('type', 'unknown')})"
    return "Unknown"
