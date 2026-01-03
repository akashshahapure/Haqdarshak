import streamlit as st
import asyncio, os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# --- FIX: Create an event loop for the Streamlit thread ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

@st.cache_resource
def init_chromaDB():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings as google_embed
    from langchain_chroma import Chroma
    from dotenv import load_dotenv
    import os

    # Loading Google embedding API key from environment
    load_dotenv()
    GOOGLE_EMBED_API_KEY = os.environ.get("GOOGLE_EMBED_API_KEY")

    # Initializing Google embedding model
    embedding = google_embed(model = 'models/gemini-embedding-001', google_api_key=GOOGLE_EMBED_API_KEY)

    # Initializing ChromaDB
    chroma_db = Chroma(collection_name="HQHR",
                       embedding_function=embedding,
                       persist_directory=r"C:\Users\akash\Documents\Haqdarshak\Work\hqhr_chatbot\ChromaDB"
                       )
    return chroma_db