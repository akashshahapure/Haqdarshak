#-------- IMPORTING REQUIRED LIBRARIES ---------
import pandas as pd, xlsxwriter, io, requiredFunc as rf, streamlit as st
from datetime import datetime as dt
from notifypy import Notify
notification = Notify()
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
if 'parentDuplicateData' not in st.session_state:
    st.session_state.parentDuplicateData = None
if 'og_DF' not in st.session_state:
    st.session_state.og_DF = None
if 'rejectedDF' not in st.session_state:
    st.session_state.rejectedDF = None
if 'project_name' not in st.session_state:
    st.session_state.project_name = None
if 'transform_clicked' not in st.session_state:
    st.session_state.transform_clicked = False
if 'init_file_size' not in st.session_state:
    st.session_state.init_file_size = None
if 'exe_start' not in st.session_state:
    st.session_state.exe_start = None

# Title of the tab
st.set_page_config(page_title="Excel Data Transformer")

# Title of web interface.
st.title(":rainbow[Excel Data Transformer]")

# Getting user name and email ID
uname = st.sidebar.text_input('Name : ', placeholder='Enter your name')
if uname is None:
    st.warning('Please enter your name!', icon="⚠️")
    st.stop()

uemail = st.sidebar.text_input('Email : ', placeholder='Enter your Haqdarshak email ID')
if uemail is None:
    st.warning('Please enter your Haqdarshak email ID!', icon="⚠️")
    st.stop()

# Getting project file from user.
st.sidebar.image('DATA_TRANSFORMER/info portal required columns - cases report.jpg', caption="Required columns while downloading cases report from info server", use_column_width='always')
project = st.sidebar.file_uploader("Choose Excel or CSV cases report from info portal:*", type=['xlsx','xls','xlsb','csv'])

# Getting "Orgwise Scheme Applied" file from user.
orgwise = st.sidebar.file_uploader("Choose latest 'Orgwise Scheme Applied' file from Metabase. Data period should be from begining to till date:*", type=['xlsx','xls','xlsb','csv'])

# Getting "Rate Card" file from user.
rate_card = st.sidebar.file_uploader("Choose 'Rate Card' file from Metabase.*", type=['xlsx','xls','xlsb','csv'])

def transform_data():
    st.session_state.exe_start = dt.now() # Recording execution start time.
    
    if project is not None:
        data0, init_file_size = rf.csvORexcel(project, project.name)  # Reading uploaded file and storing as dataframe.
        data0, rejectedDF = rf.cleaner(data0)  # Cleaning the data.
        st.session_state.rejectedDF = rejectedDF
        st.session_state.project_name = project.name
        st.session_state.init_file_size = init_file_size
    else:
        st.warning("Project file is compulsory!", icon="⚠️")
        st.stop()

    if orgwise is not None:
        schemeDetails, fs = rf.csvORexcel(orgwise, orgwise.name)  # Reading uploaded file and storing as dataframe.
        data0 = rf.orgwiseMerge(data0, schemeDetails)  # Merging project data with orgwise scheme applied data.
    else:
        st.warning("Please choose Orgwise_Scheme_Applied file to proceed further.", icon="⚠️")
        st.stop()

    if rate_card is not None:
        data0 = rf.hdPayment(data0, rate_card) # Adding prices from rate card and calculate hd payment.
        unique_data, duplicateData, parentDuplicateData, og_DF = rf.eGov_DFL_dup(data0)  # Separating DFL and E-Gov duplicate and unique data.
        st.session_state.unique_data = unique_data
        st.session_state.duplicateData = duplicateData
        st.session_state.parentDuplicateData = parentDuplicateData
        st.session_state.og_DF = og_DF
    else:
        st.warning("Please choose rate_card file to proceed further.", icon="⚠️")
        st.stop()

if st.sidebar.button('Transform'):
    st.session_state.transform_clicked = True
    transform_data()
    st.experimental_rerun()

# Showing project name
if st.session_state.project_name:
    try:
        st.header((st.session_state.project_name).split('_')[2])
        st.divider()
    except:
        st.header(st.session_state.project_name)
        st.divider()

cols = st.columns(2, gap='large')

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
            st.subheader('Unique Data Insights')
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
                if st.session_state.duplicateData.shape[0] > 0:
                    st.session_state.duplicateData.to_excel(uwriter, sheet_name='Duplicate Data', index=False)
                if st.session_state.parentDuplicateData.shape[0] > 0:
                    st.session_state.parentDuplicateData.to_excel(uwriter, sheet_name='Duplicate Data', index=False)
                if st.session_state.rejectedDF.shape[0] > 0:
                    st.session_state.rejectedDF.to_excel(uwriter, sheet_name='Duplicate Data', index=False)
                exe_end = dt.now() # Recording execution end time
                uwriter.close()

            # Logging Unique data execution process.
            rf.logging('Unique', uname, uemail, st.session_state.init_file_size, st.session_state.exe_start, exe_end, unique_data, st.session_state.duplicateData, st.session_state.rejectedDF, project.name)

            if st.sidebar.download_button(label='Download Unique Data Insights',
                                          data=uniqueBuffer, file_name='unique_' + (st.session_state.project_name).split('.')[0] + '.xlsx',
                                          mime="application/vnd.ms-excel"):
                st.experimental_rerun()
                #st.stop()

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
            st.subheader('All Data Insights')
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
                if st.session_state.duplicateData.shape[0] > 0:
                    st.session_state.duplicateData.to_excel(awriter, sheet_name='Duplicate Data', index=False)
                if st.session_state.parentDuplicateData.shape[0] > 0:
                    st.session_state.parentDuplicateData.to_excel(awriter, sheet_name='Duplicate Data', index=False)
                if st.session_state.rejectedDF.shape[0] > 0:
                    st.session_state.rejectedDF.to_excel(awriter, sheet_name='Duplicate Data', index=False)
                exe_end = dt.now()
                awriter.close()
            
            # Logging All data execution process.
            rf.logging('All', uname, uemail, st.session_state.init_file_size, st.session_state.exe_start, exe_end, og_DF, st.session_state.duplicateData, st.session_state.rejectedDF, project.name)

            if st.sidebar.download_button(label='Download All Data Insights',
                                          data=allBuffer, file_name='All_' + (st.session_state.project_name).split('.')[0] + '.xlsx',
                                          mime="application/vnd.ms-excel"):
                #st.stop()
                st.experimental_rerun()
