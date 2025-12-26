import os
with open('./HQgeminiAPIKey.txt', 'r')as HQfile:
    GOOGLE_API_KEY = HQfile.read()
os.environ['GOOGLE_API_KEY'] = GOOGLE_API_KEY
with open('./geminiAPIKey.txt', 'r')as file:
    GOOGL_EMBED_API_KEY = file.read()
os.environ['GOOGL_EMBED_API_KEY'] = GOOGL_EMBED_API_KEY

print('Importing required libraries...')
import warnings
warnings.filterwarnings('ignore')
from glob import glob
from datetime import datetime as dt
import time
import faiss
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings as google_embed
rate_limiter = InMemoryRateLimiter(requests_per_second=0.1,
                                   check_every_n_seconds=0.1,  # How often the limiter checks if a request is allowed
                                   max_bucket_size=10,)         # Maximum burst size
gemini = ChatGoogleGenerativeAI(model='gemini-2.5-flash', google_api_key=GOOGLE_API_KEY, rate_limiter=rate_limiter)
embedding = google_embed(model = 'models/gemini-embedding-001', google_api_key=GOOGL_EMBED_API_KEY, rate_limiter=rate_limiter)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredPDFLoader
from langchain_community.document_loaders.parsers import TesseractBlobParser, RapidOCRBlobParser
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from IPython.display import display, Markdown
from dotenv import load_dotenv
load_dotenv()
print('Required libraries imported!')


# Function to read PDF file, summarise and chunk
def chunking(file_path, chunks = 1000, overlap = 200):
    print("Reading policies of {0}".format(file_path.split('\\')[-1]))                
    loader = UnstructuredPDFLoader(file_path = file_path, stratergy='hi-res', infer_table_structure=True, extract_images=True,
                                   image_output_dir_path='./images', mode='paged', chunking_strategy="by_title")
    doc = loader.load()
    docs = [d.page_content for d in doc]
    print("Policy reading of {0} has completed!".format(file_path.split('\\')[-1]) )
    print()
    print('Getting the summary of leave policy {0}'.format(file_path.split('\\')[-1]))
    summary = gemini.invoke([
    ('system',
     '''You are a best document summarizer of HR department for a company who can summarize brief and short by highlighting only key points. 
     You will get the doc which is a HR policy from which you have to briefly summarize the policy'''),
    ("human",
     docs)]).content
    metadata = {'source':'Gemini AI',
                'filename' : file_path.split('\\')[-1],
                'category' : 'Summary'}
    summary_doc = Document(metadata=metadata, page_content=summary)
    doc.append(summary_doc)
    print("Added the summary of {0} which is as below\n********************************************\n\n".format(file_path.split('\\')[-1]))
    display(Markdown(summary))
    print('\n\n********************************************')      
    print()
    print('Getting the definition of important terminologies from {0}'.format(file_path.split('\\')[-1]))
    definitions = gemini.invoke([
    ('system',
     '''You are a senior HR key point identifier from given documents and you are good at finding important terminologies from the given text document and
     if these terminologies have no any explanation or definition available in the given text then you get the brief and precise definition. Please refer the given example.
     Example 1, Privilege leave (PL), also known as earned leave, is a paid type of leave that employees accrue based on their days worked.
     Example 2. FT Employees, refers to full-time employees, who are typically permanent staff working 30–40+ hours per week and are eligible for a full benefits package, including health insurance and paid time off.'''),
    ("human",
     docs)]).content
    metadata = {'source':'Gemini AI',
                'filename' : file_path.split('\\')[-1],
                'category' : 'Definitions'}
    definitions_doc = Document(metadata=metadata, page_content=definitions)
    doc.append(definitions_doc)
    print("Added the definitions of key terminologies from {0} which is as below\n********************************************\n\n{1}\n\n********************************************".
        format(file_path.split('\\')[-1], display(Markdown(definitions))))
    #print()
    print()
    print("Chunking the policy of {0}".format(file_path.split('\\')[-1]))
    print()
    print('Filtering complex metadata from the document!')
    # Filtering extra metadata from chunk files
    filtered_chunks = filter_complex_metadata(doc)
    print("Complex metadata has been Filtered!")
    print()
    print('Chunking the document with chunk size {0} words and overlapping text with {1} words!'.format(chunks,overlap))
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunks, chunk_overlap=overlap)
    doc_chunks = splitter.split_documents(filtered_chunks)
    print("HR Policy processing of {0} has completed!".format(file_path.split('\\')[-1]))

    return doc_chunks


# Initializing ChromaDB : **Please run this only once**
def init_ChrmDB(filtered_chunks):
    if os.path.isdir('ChromaDB'):
        chromadb = Chroma(persist_directory="./ChromaDB",
                          embedding_function=embedding,
                          collection_name="HQHR")
        if len(filtered_chunks)==1:
            chromadb.add_documents(documents=filtered_chunks[0])
        else:
            for chunk in filtered_chunks:
                time.sleep(10)
                print("{0} : Waiting for 10 seconds for embedding {1} policy".
                    format(dt.now().strftime("%d-%m-%Y %H:%M:%S"),chunk[0].metadata['filename']))
                chromadb.add_documents(documents=chunk)
    else:
        if len(filtered_chunks)==1:
            chromadb = Chroma.from_documents(documents=filtered_chunks[0],
                                             persist_directory="./ChromaDB",
                                             collection_name='HQHR',
                                             collection_metadata = {"hnsw:space":"cosine"},
                                             embedding=embedding)
        else:
            for chunk in filtered_chunks:
                time.sleep(10)
                print("{0} : Waiting for 10 seconds for embedding {1} policy".
                    format(dt.now().strftime("%d-%m-%Y %H:%M:%S"),chunk[0].metadata['filename']))
                if os.path.isdir('ChromaDB'):
                    chromadb.add_documents(documents=chunk)
                else:
                    chromadb = Chroma.from_documents(documents=chunk,
                                                     persist_directory="./ChromaDB",
                                                     collection_name='HQHR',
                                                     collection_metadata = {"hnsw:space":"cosine"},
                                                     embedding=embedding)

    chromadb = Chroma(persist_directory="./ChromaDB",
                          embedding_function=embedding,
                          collection_name="HQHR")
    print("Database created and embedded data added to Chroma DB with total policy collection of {0}.".format(chromadb._collection.count()))

    return chromadb

# Loading Embeddings from database
chroma_db = Chroma(collection_name="HQHR",
                   embedding_function=embedding,
                   persist_directory="./ChromaDB"
                  )

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

def format_res(res):
    return "\n\n".join(content.page_content for content in res)


# Symantic Retrieval, chat prompt template and chat RAG chain
def retriever_chat_rag_chain(k=5, query="Haqarshak Empowerment Solutions Pvt. Ltd."):
    # Symantic Retrieval
    symantic_retriever = chroma_db.as_retriever(search_type='similarity', search_kwargs={'k':k})

    # Chat prompt template
    rag_prompt_template = ChatPromptTemplate.from_template(prompt)

    # Chat RAG chain
    chat_rag_chain=({'context':(symantic_retriever | format_res),
                     'question':RunnablePassthrough()} | rag_prompt_template | gemini)

    # Storing the reponse
    response = chat_rag_chain.invoke(query)
    
    return response, k

html_code = """
<p style="color: hotpink; background-color: purple; padding: 1px; display: inline-block; font-size: 10px; font-weight: bold;">
    हक़
</p>
"""
'''chat_response = chat_rag_chain.invoke("Introduce yourself in professional manner and ask politely how you can help")
display(Markdown(html_code+" : "+chat_response.content))
print('**********************************************\n')'''

INITIAL_GREETING = "Hello! I'm Harshil, your HR assistant for Haqdarshak company. I can answer your queries about HR policies. What can I help you with today?\n\n"
def chtbot():
    display(Markdown(html_code+" : "+INITIAL_GREETING))
    
    while True:

        usrQuery = input(" Please ask your query related to Haqdarshak's HR Policies. \n If you are done then type Exit or Quit to finish.\n\n🗣️ :")
        if usrQuery.lower() in ['exit', 'quit']:
            break
        else:
            print('\n')
            #chat_response = chat_rag_chain.invoke(query)
            chat_response, ks = retriever_chat_rag_chain(query=usrQuery)
            
            while chat_response == 'I cannot answer this from the current knowledge base.':
                if ks>20:
                    break
                else:
                    ks+=3
                    chat_response, ks = retriever_chat_rag_chain(k=ks, query=usrQuery)
                    #chat_response = chat_rag_chain.invoke(query)
                    
            display(Markdown(html_code+" : "+chat_response.content))
            print('**********************************************\n')

chtbot()