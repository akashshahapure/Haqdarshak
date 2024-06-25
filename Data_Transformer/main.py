#-------- IMPORTING REQUIRED LIBRARIES ---------
import pandas as pd
import numpy as np
import xlsxwriter
import matplotlib.pyplot as plt
import tempfile
import os
import io
import seaborn as sns
import requiredFunc as rf
import streamlit as st
from datetime import datetime as dt
from openpyxl import load_workbook
from notifypy import Notify
from state import states
from googletrans import Translator
import warnings
warnings.filterwarnings('ignore')

notification = Notify()

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
print("\n*****Required libraries imported from main*****")

# Initialize session state variables if they don't exist
if 'unique_data' not in st.session_state:
    st.session_state.unique_data = None
if 'duplicateData' not in st.session_state:
    st.session_state.duplicateData = None
if 'og_DF' not in st.session_state:
    st.session_state.og_DF = None
if 'rejectedDF' not in st.session_state:
    st.session_state.rejectedDF = None
if 'project_name' not in st.session_state:
    st.session_state.project_name = None
if 
if 'transform_clicked' not in st.session_state:
    st.session_state.transform_clicked = False

# Title of web interface.
st.title(":rainbow[Excel Data Transformer]")

# Getting project file from user.
project = st.sidebar.file_uploader("Choose Excel or CSV file:*", type=['xlsx','xls','xlsb','csv'])

# Getting "Orgwise Scheme Applied" file from user.
orgwise = st.sidebar.file_uploader("Choose latest 'Orgwise Scheme Applied' file from Metabase. Data period should be from begining to till date:*", type=['xlsx','xls','xlsb','csv'])

def transform_data():
    if project is not None:
        data0, file_size = rf.csvORexcel(project, project.name)  # Reading uploaded file and storing as dataframe.
        data0, rejectedDF = rf.cleaner(data0)  # Cleaning the data.
        st.session_state.rejectedDF = rejectedDF
        st.session_state.project_name = project.name
    else:
        st.write("Project file is compulsory!")

    if orgwise is not None:
        schemeDetails, fs = rf.csvORexcel(orgwise, orgwise.name)  # Reading uploaded file and storing as dataframe.
        data0 = rf.orgwiseMerge(data0, schemeDetails)  # Merging project data with orgwise scheme applied data.
        unique_data, duplicateData, og_DF = rf.eGov_DFL_dup(data0)  # Separating DFL and E-Gov duplicate and unique data.
        st.session_state.unique_data = unique_data
        st.session_state.duplicateData = duplicateData
        st.session_state.og_DF = og_DF
    else:
        st.write("Please choose Orgwise_Scheme_Applied file to proceed further.")

if st.sidebar.button('Transform'):
    st.session_state.transform_clicked = True
    transform_data()
    st.experimental_rerun()

# Showing project name
if st.session_state.project_name:
    st.header((st.session_state.project_name).split('_')[2])
    st.divider()

cols = st.columns(2, gap='medium')

with cols[0]:
    if st.session_state.unique_data is not None:
        with st.spinner('Processing unique data...'):
            unique_data = rf.casesCount(st.session_state.unique_data)  # This should return a new DataFrame
            projectwise_O_S_BR, districtWise_O_S_BR, Sch_O_S_BR, statusFig = rf.statusSummary(unique_data)
            Orgwise_Scheme_Diversity, schDivFig = rf.orgwiseSchDiv(unique_data)
            cit_sch_ratio, citSchRatioFig = rf.citSchRatio(unique_data) # Citizen scheme ratio report
            top_bottom_hd = rf.hdAchv(unique_data) # HDwise achievement
            Scheme_Categorisation = rf.schAchv(unique_data) # Schemewise achievement
            gen_Bif, genFig = rf.genderDist(unique_data) # Gender distribution
            repeat_mobile = rf.repeatMobile(unique_data) # Getting repeatative mobile numbers
            
            # Visualizing insights from unique data.
            st.pyplot(statusFig)
            st.pyplot(schDivFig)
            st.pyplot(citSchRatioFig)
            st.pyplot(genFig)

            uniqueBuffer = io.BytesIO()

            with pd.ExcelWriter(uniqueBuffer, engine='xlsxwriter') as uwriter:
                unique_data.to_excel(uwriter, sheet_name='Schemes Data', index=False)  # Exporting unique data
                projectwise_O_S_BR.to_excel(uwriter, sheet_name='projectwise_O_S_BR', index=False)
                districtWise_O_S_BR.to_excel(uwriter, sheet_name='Districtwise achv', index=False)
                Sch_O_S_BR.to_excel(uwriter, sheet_name='Schemewise achv', index=False)
                Orgwise_Scheme_Diversity.to_excel(uwriter, sheet_name='Org_Sch_Diversity', index=False)
                cit_sch_ratio.to_excel(uwriter, sheet_name='Cit_Sch_Ratio', index=False)
                top_bottom_hd.to_excel(uwriter, sheet_name='HD Performance', index=False)
                Scheme_Categorisation.to_excel(uwriter, sheet_name='Scheme Categorisation', index=False)
                gen_Bif.to_excel(uwriter, sheet_name='Gender Bifurcation', index=False)
                st.session_state.duplicateData.to_excel(uwriter, sheet_name='Duplicate Data', index=False)
                st.session_state.rejectedDF.to_excel(uwriter, sheet_name='Rejected Data', index=False)
                uwriter.close()

            if st.sidebar.download_button(label='Download Unique Data Insights',
                                          data=uniqueBuffer, file_name='unique_' + (st.session_state.project_name).split('.')[0] + '.xlsx',
                                          mime="application/vnd.ms-excel"):
                st.stop()

with cols[1]:
    if st.session_state.og_DF is not None:
        with st.spinner('Processing all data...'):
            og_DF = rf.casesCount(st.session_state.og_DF)  # This should return a new DataFrame
            ogprojectwise_O_S_BR, ogdistrictWise_O_S_BR, ogSch_O_S_BR, ogStatusFig = rf.statusSummary(og_DF)
            ogOrgwise_Scheme_Diversity, ogOrgschDivFig = rf.orgwiseSchDiv(og_DF)
            ogcit_sch_ratio, ogCitSchRatioFig = rf.citSchRatio(og_DF) # Citizen scheme ratio report
            ogtop_bottom_hd = rf.hdAchv(og_DF) # HDwise achievement
            ogScheme_Categorisation = rf.schAchv(og_DF) # Schemewise achievement
            ogGen_Bif, ogGenFig = rf.genderDist(og_DF) # Gender distribution
            ogrepeat_mobile = rf.repeatMobile(og_DF) # Getting repeatative mobile numbers            
            
            # Visualizing insights from original data.
            st.pyplot(ogStatusFig)
            st.pyplot(ogOrgschDivFig)
            st.pyplot(ogCitSchRatioFig)
            st.pyplot(ogGenFig)

            allBuffer = io.BytesIO()

            with pd.ExcelWriter(allBuffer, engine='xlsxwriter') as awriter:
                og_DF.to_excel(awriter, sheet_name='Schemes Data', index=False)  # Exporting unique data
                ogprojectwise_O_S_BR.to_excel(awriter, sheet_name='projectwise_O_S_BR', index=False)
                ogdistrictWise_O_S_BR.to_excel(awriter, sheet_name='Districtwise achv', index=False)
                ogSch_O_S_BR.to_excel(awriter, sheet_name='Schemewise achv', index=False)
                ogOrgwise_Scheme_Diversity.to_excel(awriter, sheet_name='Org_Sch_Diversity', index=False)
                ogcit_sch_ratio.to_excel(awriter, sheet_name='Cit_Sch_Ratio', index=False)
                ogtop_bottom_hd.to_excel(awriter, sheet_name='HD Performance', index=False)
                ogScheme_Categorisation.to_excel(awriter, sheet_name='Scheme Categorisation', index=False)
                ogGen_Bif.to_excel(awriter, sheet_name='Gender Bifurcation', index=False)
                st.session_state.duplicateData.to_excel(awriter, sheet_name='Duplicate Data', index=False)
                st.session_state.rejectedDF.to_excel(awriter, sheet_name='Rejected Data', index=False)
                awriter.close()

            if st.sidebar.download_button(label='Download All Data Insights',
                                          data=allBuffer, file_name='All_' + (st.session_state.project_name).split('.')[0] + '.xlsx',
                                          mime="application/vnd.ms-excel"):
                st.stop()
