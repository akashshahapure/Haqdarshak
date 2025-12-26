import streamlit as st
import asyncio
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# --- FIX: Create an event loop for the Streamlit thread ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

with open(r'.\ref\HQgeminiAPIKey.txt', 'r')as HQfile:
        GOOGLE_API_KEY = HQfile.read()

@st.cache_resource
def googleORopenAI(key=GOOGLE_API_KEY):
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings as google_embed
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    if not key.startswith("sk"):
        llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash', google_api_key=key)
        embedding = google_embed(model = 'models/gemini-embedding-001', google_api_key=key)
    else:
        llm = ChatOpenAI(model_name='gpt-3.5-turbo', temperature=0, openai_api_key=key)
        embedding = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=key)
    return llm, embedding

with st.sidebar:
    st.header("API Key Configuration")
    with st.form("api_key_form"):
        api_key = st.text_input("Enter OpenAI or Google API key", type="password")
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state.api_key = api_key

if "api_key" in st.session_state:
    llm, embedding = googleORopenAI(st.session_state.api_key)
else:
    st.warning("Please enter OpenAI or Google API key.")

# --- Page Config ---
st.set_page_config(
    page_title="Research Paper Assistant",
    page_icon="🤖",
    layout="centered"
)

# --- 1. Define your RAG Backend Wrapper ---
@st.cache_resource
def get_rag_response(usrQuery):
    from langchain_community.vectorstores import FAISS
    from langchain_core.runnables import RunnablePassthrough
    import faiss
    from langchain_core.runnables import RunnablePassthrough, RunnableParallel
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    rag_prompt = '''You are an AI assistant who is a good & polite helper who will answer user questions from the given context only and if you won't find the answer in the 
    context then you will politely deny and will ask another question from user. Also, make sure you save the tokens as much as possible.

    question: {question}
    context: {context}
    '''
    faiss_vector_store = FAISS.load_local(r'C:\Users\akash\Documents\Haqdarshak\Work\RAG_QA\FAISS', embedding, allow_dangerous_deserialization=True) # Load existing FAISS vector DB
    retriever = faiss_vector_store.as_retriever(search_type='similarity', k=5) # Create retriever from FAISS vector DB
    rag_prompt_template = ChatPromptTemplate.from_template(rag_prompt) # Create prompt template
    setup_retrieval = RunnableParallel({'context' : retriever, 'question' : RunnablePassthrough()})
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    qa_rag_chain = setup_retrieval.assign(answer = (RunnablePassthrough.assign(context=lambda x: format_docs(x['context']))
                                                    |rag_prompt_template
                                                    | llm
                                                    | StrOutputParser())) # Create RAG chain
    response = qa_rag_chain.invoke(usrQuery) # Get response from RAG chain
    return response['answer']

# --- 2. Session State Initialization ---
# This ensures the chat history is not lost when the script reruns
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. UI Layout ---
st.title("🤖 Research Paper Assistant")
st.markdown("Ask me anything about below research papers.")
st.markdown("1.Attention Is All You Need")
st.markdown("2.Language Models are Few-Shot Learners")
st.markdown("3.RAG for Knowledge-Intensive NLP Tasks.")

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
            
            # Add assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Display response
            st.markdown(response)

    