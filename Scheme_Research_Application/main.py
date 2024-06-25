import openai, requests, pickle, os, streamlit as st
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA 

# Load OpenAI API key from .config file
def load_api_key():
    try:
        with open(r'C:\Users\akash\Documents\Haqdarshak\Work\Scheme_Research_Application\.config', 'r') as file:
            api_key = file.readline().strip()
            os.environ["OPENAI_API_KEY"] = api_key # Creating virtual environment to store Open AI API key virtuallly.
            return api_key
    except Exception as e:
        st.error(f"Error loading API key: {e}")
        return None

api_key = load_api_key()
openai.api_key = api_key

def fetch_article_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status() 
        return response.text
    except Exception as e:
        st.error(f"Error fetching content from {url}: {e}")
        return ""

# Defining a function to vectorize the text for embedding
def generate_embeddings(text, api_key):
    try:
        text_splitter = CharacterTextSplitter(chunk_size=3, chunk_overlap=0, separator="\n,.:")
        texts = text_splitter.split_text(text)
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        return embeddings.embed_documents(texts)
    except Exception as e:
        st.error(f"Error generating embeddings: {e}")
        return []

# Defining a function to store indexes of embeddings
def save_faiss_index(index, path):
    try:
        with open(path, 'wb') as f:
            pickle.dump(index, f)
    except Exception as e:
        st.error(f"Error saving FAISS index: {e}")

# Defining a function to load indexes from the pickle store
def load_faiss_index(path):
    try:
        with open(path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        st.error(f"Error loading FAISS index: {e}")
        return None

# Defining a function to generate summary of the document
def get_summary(faiss_index, openai_api_key):
   llm = ChatOpenAI(temperature=0.5, model_name='gpt-3.5-turbo', openai_api_key = openai_api_key) #text-embedding-3-large
   pdf_qa = RetrievalQA.from_chain_type(
       llm,
       retriever=faiss_index.as_retriever(search_kwargs={'k': 4}),
       chain_type="stuff",
       )
   # Defining the Query. 
   query = """ Write a summary for the document passed to you. You are getting a PDF document and your job \
        is to interpret the information in the document and to provide a summary. This summary should highlight \
        key points like Scheme Benefits, Scheme Application Process, Eligibility, and Documents required"""
    
    # Executing the RetreivalIQA model with the defined query. 
   result = pdf_qa.run(query)

   return result

# Title of web interface.
st.title("Scheme Research Application")

# Getting URL of the file from user.
urls = st.sidebar.text_area("Enter URLs (one per line):")

# Creating action button "Process URL" and steps to follow.
if st.sidebar.button("Process URLs"):
    urls = urls.split("\n")
    all_texts = []
    for url in urls:
        with st.spinner(f"Fetching content from: {url}"):
            content = fetch_article_content(url)
        if content:
            all_texts.append(content)
    
    combined_text = "\n".join(all_texts)


    if combined_text:
        with st.spinner("Generating embeddings..."):
            embedding_vectors = generate_embeddings(combined_text, api_key)
        
        if embedding_vectors:
            st.write("Indexing with FAISS...")
            faiss_index = FAISS.from_documents(embedding_vectors)
            save_faiss_index(faiss_index, r'C:\Users\akash\Documents\Haqdarshak\Work\Scheme_Research_Application\faiss_store_openai.pkl')
            st.success("Processing complete and FAISS index saved.")
            with st.spinner("Generating summary..."):
                summary = get_summary(faiss_index, api_key)
                st.write(summary)

        else:
            st.error("Failed to generate embeddings.")
    else:
        st.error("Failed to fetch or combine content from URLs.")

question = st.text_input("Enter your question:")
if st.button("Ask Question"):
    faiss_index = load_faiss_index(r'C:\Users\akash\Documents\Haqdarshak\Work\Scheme_Research_Application\faiss_store_openai.pkl')
    if faiss_index and question:
        st.write("Fetching answer...")
        similar_docs = faiss_index.similarity_search(question)
        if similar_docs:
            answer = similar_docs[0]['text']
            st.write(f"Answer: {answer}")
            st.write(f"Source URL: {similar_docs[0]['metadata']['source']}")
        else:
            st.error("No relevant documents found.")
    else:
        st.error("Failed to load FAISS index or no question provided.")