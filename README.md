# Dorm-Graph-Timeseries-Dashboard

## Overview

This project creates a live dashboard for visualizing and interacting with dormitory building data using both time series and graph-based approaches. It merges IoT sensor simulation (e.g., temperature and occupancy data) with spatial modeling of infrastructure (e.g., dorm rooms and AC units) in a graph database.

Built with Python and Streamlit, the dashboard leverages:

- **Neo4j** for spatial and logical relationships (e.g., which AC unit serves which rooms),
- **MongoDB** for storing and querying time series sensor data, and
- **LLM-powered tools** (via LlamaIndex and Google Generative AI) to enable advanced querying and insights.

## Motivation

Modern smart buildings rely on interconnected data sources to optimize comfort, energy efficiency, and maintenance. This project simulates such a system and enables intuitive querying and visualization for:

- Room-specific sensor histories,
- AC unit relationships,
- Higher-level entity control (e.g., energy service units managing ACs),
- Time-aware analysis of environmental patterns.

## Features

- Graph-based data modeling (Neo4j)
- Time series data generation and logging (temperature, occupancy)
- MongoDB for efficient time-based storage
- PyVis-based interactive graph visualization in Streamlit
- Secure environment configuration with `.env`
- Compatibility with LLM-driven assistants (LlamaIndex, Gemini)
  
## Quickstart

### Clone the repository

```bash
git clone https://github.com/your-username/Dorm-Graph-Timeseries-Dashboard.git
cd Dorm-Graph-Timeseries-Dashboard
```
### Install dependencies
#### Using requirements.txt:

```bash
pip install -r requirements.txt
```
#### Or manually:

```bash
pip install streamlit pymongo neo4j pyvis pandas numpy matplotlib llama_index google-generativeai python-dotenv
```
### Run the Streamlit app
#### Make sure MongoDB and Neo4j are both running, then:

```bash
streamlit run main/app.py
```
#### The app will open in your default web browser.

### Project Structure
```bash
.
├── app.py                   # Main dashboard interface
├── data_storage.py          # MongoDB connection & utilities
├── load_graph.py            # Graph builder for Neo4j
├── neo4j_utils.py           # Neo4j helper functions
├── time_series_generator.py # Time series data simulator
├── utils.py                 # Shared helper functions
├── requirements.txt         # Python dependencies
```
### .env File Format
#### Create a .env file in your project directory with:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=your_username
NEO4J_PASSWORD=your_password
MONGO_URI=your_uri_name
MONGO_DB=your_db_name
MONGO_COLLECTION=your_collection_name
VECTOR_INDEX_COLLECTION=your_vector_index_collection_name
```
#### This avoids hardcoding sensitive credentials into the codebase.

### LLM Integration
- This project optionally supports natural language interfaces using LLMs like Google Gemini through:

- llama_index: to convert graph + time series data into queryable context.

- google-generativeai: for querying and generating insights from structured data.

- Make sure your API keys are set up if using these features.

### Use Cases
- Visualize AC unit-to-room service mappings

- Track changes in occupancy or temperature over time

- Run LLM-powered diagnostics like:

- "Which AC unit had the most load yesterday?"

- "Which room was unoccupied during high-temperature periods?"

### Future Improvements
- Add user authentication and role-based access

- Support historical anomaly detection and graph alerts

- Expand to support multi-building systems

