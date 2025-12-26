print('Importing required libraries...')
import warnings, os
warnings.filterwarnings('ignore')
from glob import glob
from datetime import datetime as dt
import time
import faiss
from langchain_core.rate_limiters import InMemoryRateLimiter

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders.parsers import TesseractBlobParser
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from google.api_core.exceptions import ResourceExhausted
from IPython.display import display, Markdown
from dotenv import load_dotenv
load_dotenv()
print('Required libraries imported!')

def loadLLM():
    from langchain_core.rate_limiters import InMemoryRateLimiter
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings as google_embed
    with open(r'C:\Users\akash\Documents\Haqdarshak\Work\RAG_QA\ref\HQgeminiAPIKey.txt', 'r')as HQfile:
        GOOGLE_API_KEY = HQfile.read()

    with open(r'C:\Users\akash\Documents\Haqdarshak\Work\RAG_QA\ref\geminiAPIKey.txt', 'r')as file:
        GOOGL_EMBED_API_KEY = file.read()
    
    rate_limiter = InMemoryRateLimiter(requests_per_second=0.1,
                                       check_every_n_seconds=0.1,  # How often the limiter checks if a request is allowed
                                       max_bucket_size=10,)         # Maximum burst size
    gemini = ChatGoogleGenerativeAI(model='gemini-2.5-flash', google_api_key=GOOGLE_API_KEY, rate_limiter=rate_limiter)
    embedding = google_embed(model = 'models/gemini-embedding-001', google_api_key=GOOGL_EMBED_API_KEY, rate_limiter=rate_limiter)
    return gemini, embedding

def get_google_api_key():
    # 1. Get the folder where THIS script (app.py) is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Build the absolute path to the key file
    file_path = os.path.join(script_dir, 'ref', 'HQgeminiAPIKey.txt')

    with open(file_path, 'r')as HQfile:
            GOOGLE_API_KEY = HQfile.read()

    return GOOGLE_API_KEY

# Reading PDF files from the folder './PDF/'
def read_pdfs(file_path):
    papers=[]

    loader = PyMuPDFLoader(file_path, mode="page", images_inner_format="html-img", images_parser=TesseractBlobParser(), extract_tables="markdown",)
    data = loader.load()
    for doc in data:
        doc.metadata['source'] = file_path.split('\\')[-1]
        doc.metadata['title'] = file_path.split('\\')[-1].split('.')[0]
        papers.append(doc)
    return papers

# Filtering metadata and Splitting the documents into smaller chunks
def process_documents(papers):
    filtered_papers = filter_complex_metadata(papers) # Filter out unsupported metadata types
    splitter = RecursiveCharacterTextSplitter(chunk_size = 1500, chunk_overlap = 300) # Initialize text splitter
    chunks = splitter.split_documents(filtered_papers)
    return chunks

# Creating and/or Adding data to FAISS vector DB
# *********************RUN BELOW FUNCTION ONLY ONCE******************************
def add_data_to_FAISS(chunks, embedding):
    if os.path.isfile('./FAISS/index.faiss') and os.path.isfile('./FAISS/index.pkl'):
        faiss_vector_store = FAISS.load_local('./FAISS')
        try:
            print('Adding chunks to exisitng FAISS vector DB.')
            faiss_vector_store.add_documents(chunks, embedding)
            print('Added chunks to exisitng FAISS vector DB.')
        except ResourceExhausted:
            print('Token quota exceeded hence waiting for 10 seconds')
            time.sleep(10)
            print('Adding chunks to exisitng FAISS vector DB.')
            faiss_vector_store.add_documents(chunks, embedding)
            print('Added chunks to exisitng FAISS vector DB.')
    else:
        print('Creating and adding FAISS vector DB.')
        faiss_vector_store = FAISS.from_documents(chunks, embedding)
        faiss_vector_store.save_local('./FAISS')
        print('Created and added FAISS vector DB.')

