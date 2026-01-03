import streamlit as st, os
@st.cache_resource
def loadLLMfromText():
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings as google_embed
    from dotenv import load_dotenv
    load_dotenv()

    GOOGLE_API_KEY = os.environ.get(GOOGLE_API_KEY)
    GOOGLE_EMBED_API_KEY = os.environ.get(GOOGLE_EMBED_API_KEY)
    
    gemini = ChatGoogleGenerativeAI(model='gemini-2.5-flash', google_api_key=GOOGLE_API_KEY)
    embedding = google_embed(model = 'models/gemini-embedding-001', google_api_key=GOOGLE_EMBED_API_KEY)
    return gemini, embedding

gemini, embedding = loadLLMfromText()

# --- 1. Define your RAG Backend Wrapper ---
def get_rag_response(usrQuery):
    rag_prompt = '''You are an AI assistant who is a good & polite helper who will answer user questions from the given context only and if you won't find the answer in the 
    context then you will politely deny and will ask another question from user. Also, make sure you save the tokens as much as possible.

    question: {question}
    context: {context}
    '''
    faiss_vector_store = FAISS.load_local('./FAISS', embedding, allow_dangerous_deserialization=True) # Load existing FAISS vector DB
    retriever = faiss_vector_store.as_retriever(search_type='similarity', k=5) # Create retriever from FAISS vector DB
    rag_prompt_template = ChatPromptTemplate.from_template(rag_prompt) # Create prompt template
    qa_rag_chain = ({"context":retriever,
                    "question": RunnablePassthrough()} | rag_prompt_template | gemini) # Create RAG chain
    responce = qa_rag_chain.invoke(usrQuery) # Get response from RAG chain

    
    # Simulating processing time
    time.sleep(1) 
    
    return responce

# --- 2. Session State Initialization ---
# This ensures the chat history is not lost when the script reruns
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. UI Layout ---
st.title("🤖 RAG Knowledge Assistant")
st.markdown("Ask me anything about your document database.")

# Optional: Add a "Clear Chat" button in the sidebar
with st.sidebar:
    st.header("Settings")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- 4. Display Chat History ---
# We iterate through the history and display it every time the app reruns
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. Handle User Input ---
if prompt := st.chat_input("What would you like to know?"):
    # A. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # B. Add User Message to History
    st.session_state.messages.append({"role": "user", "content": prompt})

    # C. Generate Response
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            # CALL YOUR RAG FUNCTION HERE
            response = get_rag_response(prompt)
            
            # Display response
            st.markdown(response)
            
    # D. Add Assistant Message to History
    st.session_state.messages.append({"role": "assistant", "content": response})


    '''# D. Display Assistant Message
    with st.chat_message("assistant"):
        st.markdown(response)'''