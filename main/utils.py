from datetime import datetime
import numpy as np
from openai import OpenAI
import streamlit as st

# Set a random seed for reproducibility in all random operations
np.random.seed(42)

# --- SHARED CONSTANTS ---

# List of all room IDs in the simulation
ROOMS = ["Room1", "Room2", "Room3", "Room4", "Room5", "Room6"]

# Occupancy profiles for different room types (active hours)
PROFILES = {
    "full_time": [(7, 9), (13, 15), (20, 22)],  # Full-time rooms: active during these hours
    "night_student": [(6, 8), (16, 18), (21, 23)]  # Night student rooms: active during these hours
}

# Mapping of each room to its occupancy profile type
ROOM_PROFILES = {
    "Room1": "full_time",
    "Room2": "night_student",
    "Room3": "full_time",
    "Room4": "night_student",
    "Room5": "full_time",
    "Room6": "night_student"
}

# List of rooms that are exposed to sunlight (affects temperature simulation)
SUNNY_ROOMS = ["Room1", "Room2", "Room3"]

# --- FUNCTIONS ---

def enrich_timestamp(t):
    """
    Add additional information to a timestamp, such as the day of the week and whether it's a weekend.

    Args:
        t (datetime): The timestamp to enrich.

    Returns:
        dict: A dictionary containing enriched timestamp information.
    """
    return {
        "hour": t.hour,
        "minute": t.minute,
        "day_of_week": t.strftime("%A"),  # Full name of the day (e.g., "Monday")
        "is_weekend": t.weekday() >= 5    # True if Saturday or Sunday
    }

def cosine_similarity(a, b):
    """
    Compute cosine similarity between two vectors.

    Args:
        a (np.ndarray): First vector.
        b (np.ndarray): Second vector.

    Returns:
        float: Cosine similarity score between -1 and 1.
    """
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def chunk_text(text, max_tokens=4000):
    """
    Split long text into chunks that fit within token limits for embedding or LLM input.

    Args:
        text (str): The input text to split.
        max_tokens (int): Maximum tokens per chunk.

    Returns:
        list: List of text chunks.
    """
    words = text.split()  # Split the input text into individual words
    chunks = []           # List to hold all resulting text chunks
    current_chunk = []    # List to build the current chunk of words
    current_length = 0    # Estimated token count for the current chunk
    estimated_tokens_per_word = 1.33  # Rough estimate: 1 token ≈ 0.75 words

    for word in words:
        word_tokens = len(word) / estimated_tokens_per_word  # Estimate tokens for this word
        # If adding this word would exceed the max token limit, start a new chunk
        if current_length + word_tokens > max_tokens:
            chunks.append(" ".join(current_chunk))  # Save the current chunk as a string
            current_chunk = [word]                  # Start a new chunk with the current word
            current_length = word_tokens            # Reset token count for new chunk
        else:
            current_chunk.append(word)              # Add word to current chunk
            current_length += word_tokens           # Update token count

    if current_chunk:
        chunks.append(" ".join(current_chunk))      # Add any remaining words as the last chunk

    return chunks  # Return the list of text chunks

def validate_openai_api_key(api_key):
    """
    Validates the provided OpenAI API key by attempting a minimal API call.

    Args:
        api_key (str): The OpenAI API key to validate.

    Returns:
        bool: True if the key is valid, False otherwise.
    """
    try:
        test_client = OpenAI(api_key=api_key)
        # Try a minimal call (list models)
        test_client.models.list()
        return True
    except Exception as e:
        st.error("Invalid OpenAI API key. Please check your key and try again.")
        return False

def get_embedding(text, client, model="text-embedding-ada-002"):
    """
    Generate an embedding vector for the given text using OpenAI's embedding model.

    Args:
        text (str): The input text to embed.
        client (OpenAI): An instance of the OpenAI client.
        model (str): The embedding model to use.

    Returns:
        np.ndarray: The embedding vector as a numpy array.
    """
    text = text.replace("\n", " ")  # Remove newlines for cleaner embedding
    resp = client.embeddings.create(input=[text], model=model)
    return np.array(resp.data[0].embedding)  # Return the embedding as a numpy array