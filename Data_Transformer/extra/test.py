from googletrans import Translator
from ai4bharat.transliteration import XlitEngine
import os, time
import pandas as pd, numpy as np, streamlit as st
print('Required Libraries Imported')
'''
t = Translator(service_urls=['translate.google.co.in'])
txlated = t.translate(text = "सीतामढ़ी", dest='en')


#df = pd.read_csv("C:\Python\read\cases_report_Nasscom1.0_All_(All States)_2024-05-17.csv")

#txlited = df['Case District'].apply(lambda x: translit(x))
'''

#file = st.file_uploader("Choose latest 'Orgwise Scheme Applied' file.\nData period should be from begining to till date:")



import streamlit as st

if "value" not in st.session_state:
    st.session_state.value = "Title"

##### Option using st.rerun #####
st.header(st.session_state.value)

if st.button("Foo"):
    st.session_state.value = "Foo"
    st.rerun()