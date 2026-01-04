import asyncio, os

# --- FIX: Create an event loop for the Streamlit thread ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import streamlit as st
from custom_functions.init_chromaDB import init_chromaDB
from custom_functions.get_response import get_response


# Setting page configuration
st.set_page_config(
    page_title="HQ HR",
    page_icon="https://framerusercontent.com/images/gVBdWe1mOwPpV6Z7x9I2kLuIWs.jpg",
    layout="centered",
)

# Initializing ChromaDB
chromaDB = init_chromaDB()

# Adding logo to the sidebar
project_path = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(project_path,'images','haqdarshak_logo.jpg')
st.logo(logo_path, size='large')

# Setting Title of the page
st.title("Haqdarshak HR Assistant")
st.markdown("Hello! I'm Harshil, your HR assistant for Haqdarshak company. I can answer your queries about HR policies. What can I help you with today?")

# Initializing session state for messages
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Showing chat history
if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

# Getting input from the user.
if user_query:= st.chat_input("Type your query here and I'll try to answer from the HR policies."):
    # Adding and printing user input to the chat history
    st.session_state.messages.append({"role":"user", "content":user_query})
    with st.chat_message('user'):
        st.markdown(user_query)

    # Getting response from the Gemini model
    with st.spinner('Generating response...'):
        response = get_response(usrQuery=user_query, db=chromaDB)

    # Adding & printing response to the chat history
    st.session_state.messages.append({'role':'assistant', 'content':response})
    with st.chat_message('assistant'):
        st.markdown(response)