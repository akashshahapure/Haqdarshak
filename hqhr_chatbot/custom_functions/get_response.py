from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from custom_functions.init_chromaDB import init_chromaDB
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
import os

# Loading Google API key from environment
load_dotenv()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

gemini = ChatGoogleGenerativeAI(model='gemini-2.5-flash', google_api_key=GOOGLE_API_KEY)

prompt='''
You are Harshil, an HR assistant for Haqdarshak company. Your sole purpose is to answer employee queries using **only** the provided context.

**Strict Instructions for Response Generation:**

1.  **Context Reliance:** Base your answer **strictly and exclusively** on the provided `Context`. Do not use external knowledge or invent facts.
2.  **Answering Style:**
    * Be **direct, simple, and concise**. The answer should ideally be $\le 2$ lines.
    * **NEVER** generate introductory or concluding sentences. Start directly with the answer.
    * **Example:** Q: How many PL a year? A: 16 Days
3.  **Handling Missing Information:**
    * If the answer is **not found** in the `Context`, reply with: "I cannot answer this from the current knowledge base."
    * **Do not** provide external or general knowledge (e.g., the definition of Casual Leave). This violates Instruction 2 and consumes unnecessary tokens.
4.  **Token Efficiency:** Prioritize short, accurate responses to minimize token usage.

Question: {question}

Context: {context}

Answer:
'''

# Initializing ChromaDB
chroma_db = init_chromaDB()

# Formatting the response
def format_res(res):
    return "\n\n".join(content.page_content for content in res)

# Symantic Retrieval, chat prompt template and chat RAG chain
def retriever_chat_rag_chain(k=5, query="Haqarshak Empowerment Solutions Pvt. Ltd.", chat_prompt=prompt):
    # Symantic Retrieval
    symantic_retriever = chroma_db.as_retriever(search_type='similarity', search_kwargs={'k':k})

    # Chat prompt template
    rag_prompt_template = ChatPromptTemplate.from_template(chat_prompt)

    # Chat RAG chain
    chat_rag_chain=({'context':(symantic_retriever | format_res),
                     'question':RunnablePassthrough()} | rag_prompt_template | gemini)

    # Storing the reponse
    response = chat_rag_chain.invoke(query)
    
    return response, k

# Get the response from the RAG chain
def get_response(usrQuery):
    # Initializing RAG chain
    chat_response, ks = retriever_chat_rag_chain(query=usrQuery)

    # Handling insufficient knowledge
    while chat_response == 'I cannot answer this from the current knowledge base.':
                if ks > 20:
                    break
                else:
                    ks += 3
                    chat_response, ks = retriever_chat_rag_chain(k=ks, query=usrQuery)

    return chat_response