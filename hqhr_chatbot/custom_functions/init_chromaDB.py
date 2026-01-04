import streamlit as st, os
from langchain_google_genai import GoogleGenerativeAIEmbeddings as google_embed
from langchain_chroma import Chroma
from dotenv import load_dotenv
# Loading Google embedding API key from environment
load_dotenv()
GOOGLE_EMBED_API_KEY = os.environ.get("GOOGLE_EMBED_API_KEY")

@st.cache_resource
def init_chromaDB():
    # Initializing Google embedding model
    embedding = google_embed(model = 'models/gemini-embedding-001', google_api_key=GOOGLE_EMBED_API_KEY)

    # Getting the path to chromaDB folder
    project_path = os.path.dirname(os.path.abspath(__file__))
    chromaDB_path = os.path.join(project_path,'ChromaDB')
    
    # Initializing ChromaDB
    chroma_db = Chroma(collection_name="HQHR",
                       embedding_function=embedding,
                       persist_directory=chromaDB_path
                       )
    return chroma_db