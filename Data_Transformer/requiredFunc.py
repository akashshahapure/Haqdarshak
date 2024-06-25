#-------- IMPORTING REQUIRED LIBRARIES ---------
import pandas as pd, numpy as np, xlsxwriter, time, matplotlib.pyplot as plt, math
from datetime import datetime as dt
from openpyxl import load_workbook
from notifypy import Notify
from state import states
from googletrans import Translator
print("\n*****Required libraries imported from requiredFunc*****")

# Defining a function to identify the file type and read the data
def csvORexcel(file, file_Name):
    init_file_size = len(file.getvalue())/1048576 # Storing file size
    
    if file_Name.split('.')[-1].startswith('c'):
        df = pd.read_csv(file)
        return df, init_file_size
    elif file_Name.split('.')[-1].startswith('x'):
        df = pd.read_excel(file)
        return df, init_file_size
    
# Defining a function for translation
def Trans(x):
    t = Translator()
    attempt = 0
    max_attempts = 5
    alph = [chr(i) for i in range(65,122)]

    while attempt < max_attempts:
        if x[0] not in alph:
            try:
                xlated = t.translate(x)
                return xlated.text
            except AttributeError as e:
                if 'raise_Exception' in str(e):
                    print(f"Encountered rate limit error, attempt {attempt+1}/{max_attempts}. Retrying in 8 seconds...")
                    time.sleep(8)
                    attempt += 1
                else:
                    raise
            except Exception as e:
                print(e)
                break
            return "Failed to translate after multiple attempts."
        else:
            return x.title()

    

# Defining a function for data cleaning
def cleaner(df):
    data0 = df
    # Remove last row.
    data0.drop(index = data0[data0.Createdon.isna()].index, inplace=True)

    # Replace null values
    data0['Scheme/Doc'].fillna('a', inplace=True)
    data0['Citizen Name'].fillna('a', inplace=True)
    data0['HD Name'].fillna('blank', inplace=True)
    data0.Mobile.fillna(0, inplace=True)

    # Changing status values and keeping only "Open/Submit/BR"
    data0['Status'] = data0['Status'].apply(lambda x: 'Open' if x == 'Data complete' else 'Submitted' if (x=='Docket submitted' or x=='Document ready') else "Benefit Received" if x=='Scheme/Document received' else x)

    # Changing Case Organization values from state initials to full state name.
    data0['Case Organization'] = data0['Case Organization'].apply(lambda x: states[x[:2]])

    # Renaming column "Case Organiisation" & "Case District" to "State" & "Disctrict"
    data0.rename(columns={"Case Organization":"State","Case District":"District"}, inplace=True)

    # Convert Mobile column from float to string for concatenation.
    data0['Mobile'] = data0['Mobile'].apply(lambda x: str(x).strip())
    #data0['Mobile'] = data0['Mobile'].astype('int64')
    data0['Mobile'] = data0['Mobile'].astype('str')

    # Change gender from initial letter to full form.
    data0['Gender'] = data0['Gender'].apply(lambda x: 'Male' if x=='M' else 'Female' if x=='F' else 'Other' if x=='O' else x)

    # Convert "Createdon", "Docket Submitted Date", "Benefit received Date" column data type to Datetime format
    dt_col = ['Createdon', 'Docket Submitted Date', 'Benefit received Date', 'DOB']

    for col in dt_col:
        try:
            data0[col] = pd.to_datetime(data0[col], format='mixed', errors='ignore')
        except KeyError:
            continue

    # Deleting records with status "Case Aborted" and "Application rejected"
    rejectedDF = data0[(data0.Status == 'Case Aborted') | (data0.Status == 'Application rejected')] # Storing prev step deleted data
    data0 = data0[(data0['Status'] != 'Case Aborted') & (data0['Status'] != 'Application rejected')]

    data0.reset_index(inplace=True, drop=True)

    # Renaming Case District name from local language to english
    dist = {} # Declaring a blank dictionary to store translated district names.

    for d in data0['District'].value_counts().index: # For loop for grouping and translating dist names
        if d in dist.keys():
            break
        else:
            dist[d] = Trans(d) # Store translated names to dictionary

    data0['District'] = data0['District'].map(dist) # Map translated names from dist dictionary.

    return data0, rejectedDF

# Merging project data with orgwise schemes data
def orgwiseMerge(projectDF, orgwise):
    data0 = projectDF
    schemeDetails = orgwise

    # Removing blank rows from "Parent Scheme GUID" column.
    schemeDetails = schemeDetails[~schemeDetails['Parent Scheme GUID'].isna()]

    # Removing colomuns except 'Scheme Id','Scheme type','Benefit Value' to merge with main dataframe
    for s in schemeDetails.columns:
        if s not in ['Scheme Id','Scheme type','Benefit Value','Parent Scheme']:
            schemeDetails.drop(columns=s, inplace=True)

    # Merging scheme details with main dataframe to get data of Scheme type & Benefit Value.
    data0 = data0.merge(schemeDetails.drop_duplicates(subset=['Scheme Id']), left_on='Scheme/Doc GUID', right_on="Scheme Id", how='left')

    # Removing non required column "Scheme ID"
    data0.drop(columns = 'Scheme Id', inplace=True)

    # Changing short form to "Scheme" & "Document"
    data0['Scheme type'] = data0['Scheme type'].apply(lambda x: 'Scheme' if x=='sch' else 'Document' if x=='doc' else x)

    # Converting "Benefit Value" columns to integer type
    data0['Benefit Value'].fillna('0', inplace=True)
    data0['Benefit Value'] = data0['Benefit Value'].apply(lambda x: int(x) if x.isnumeric() else 0)
    data0['Benefit Value'] = data0['Benefit Value'].astype('int64')

    return data0

# Defining a function to separate DFL and E-Gov data then separate the data for duplicate and unique records
def eGov_DFL_dup(data0):
    # DFL Schemes
    #- SH0009SW = Digital productivity Service_ Basic
    #- SH000BM6 = Digital productivity Service_Basic
    #- SH000AG6 = Digital Productivity Services_Advanced
    #- SH000A32 = Long Training on Digital & Financial Inclusion_Private
    #- SH0009SW = Short Training on Digital & Financial Inclusion_Private
    #- SH000AG6 = Digital Productivity Services and and employability training_Advanced

    # Adding new column for E-GOV and DFL
    data0["Scheme Category"] = data0['Scheme/Doc GUID'].apply(lambda x: "DFL" if (x=="SH0009SW" or x=="SH000AG6" or x=="SH000A32" or x=="SH0009SW" or x=="SH000AG6" or x=="SH000BM6") else "E-Gov")
    
    og_DF=data0.copy() # Storing all data for further use.

    # Storing DFL data
    dfl = data0[(data0['Scheme/Doc GUID'] == 'SH0009SW') | (data0['Scheme/Doc GUID'] == 'SH000AG6') | (data0['Scheme/Doc GUID'] == 'SH000A32') | (data0['Scheme/Doc GUID']=='SH0009SW') | (data0['Scheme/Doc GUID']=='SH000AG6') | (data0['Scheme/Doc GUID']=='SH000BM6')]

    # Storing E-Gov data
    data0 = data0[(data0['Scheme/Doc GUID'] != 'SH0009SW') & (data0['Scheme/Doc GUID'] != 'SH000AG6') & (data0['Scheme/Doc GUID'] != 'SH000A32') & (data0['Scheme/Doc GUID']!='SH0009SW') & (data0['Scheme/Doc GUID']!='SH000AG6') & (data0['Scheme/Doc GUID']!='SH000BM6')]

    # Filling missing values of "Parent Scheme" from "Scheme/Doc" column
    for i in data0[data0['Parent Scheme'].isna()].index:
        data0['Parent Scheme'][i] = data0['Scheme/Doc'][i]
        
    # Adding column with name 'parent_duplicate' by concatenation
    #data0['duplicate'] = data0['Scheme/Doc'] + data0['Citizen Name'] + data0['Mobile'] # Concatenation using scheme name for E-Gov data
    data0['parent_duplicate'] = data0['Parent Scheme'] + data0['Citizen Name'] + data0['Mobile'] # Concatenation using Parent scheme name for E-Gov data
    dfl['duplicate'] = dfl['Scheme/Doc'] + dfl['Citizen Name'] + dfl['Mobile'] # Concatenation using scheme name for DFL data

    # Converting duplicate column in lower case because python considers ASCII values of each character while checking for duplicates.
    #data0['duplicate'] = data0['duplicate'].apply(lambda x: x.lower())
    data0['parent_duplicate'] = data0['parent_duplicate'].apply(lambda x: x.lower())
    dfl['duplicate'] = dfl['duplicate'].apply(lambda x: x.lower())
    
    data0.Mobile = data0.Mobile.apply(lambda x : int(x.split('.')[0])) # Converting "Mobile" column to interger data type
    #dfl.Mobile = dfl.Mobile.apply(lambda x : int(x.split('.')[0])) # Converting "Mobile" column to interger data type

    # Checking number of all duplicate records
    #duplicateData = data0[data0.duplicated(['duplicate'],keep=False)].sort_values('duplicate') # Storing duplicate data based on scheme name for E-Gov data
    parentDuplicateData = data0[data0.duplicated(['parent_duplicate'],keep=False)].sort_values('parent_duplicate') # Storing duplicate data based on Parent scheme name for E-Gov data
    dflDuplicates = dfl[dfl.duplicated(['duplicate'],keep=False)].sort_values('duplicate') #  # Storing duplicate data based on scheme name for DFL data
    
    duplicateData = pd.concat([parentDuplicateData,dflDuplicates], ignore_index=True)
    duplicateData.reset_index(inplace=True, drop = True)

    # Keeping uniques excluding duplicates
    #df = data0.drop(index = data0[data0.duplicated(['duplicate'], keep='last')].index) # Keep unique data based on scheme name duplicate column for E-Gov
    df = data0.drop(index = data0[data0.duplicated(['parent_duplicate'], keep='last')].index) # Keep unique data based on parent scheme name duplicate column for E-Gov
    df.reset_index(inplace=True, drop = True) # Resetting index to unique data

    """ try:
            duplicateData.drop(index=duplicateData.index[-1], inplace=True)
        except IndexError:
            print(duplicateData.shape)
     try:
        df.drop(index=df.index[-1], inplace=True)
    except IndexError:
        print(df.shape)
    """
    return df, duplicateData, og_DF

# Adding a column to map no. of cases against citizen GUID
def casesCount(df):
    # Creating table citizen to scheme ratio.
    cit_sch_ratio = pd.DataFrame(df['Citizen GUID'].value_counts())
    cit_sch_ratio.rename(columns={'count':'No of cases'}, inplace=True)
    cit_sch_ratio.reset_index(inplace=True)
    # Merging no of cases with main project data.
    df = df.merge(cit_sch_ratio.drop_duplicates(subset=['Citizen GUID']), on = 'Citizen GUID', how = 'left')
    df['No of cases'].fillna(0.0, inplace=True)
    df['No of cases'] = df['No of cases'].astype('int64')

    return df

# Defining a function for status wise summary
def statusSummary(df):
    projectwise_O_S_BR = pd.DataFrame(df.Status.value_counts()) 
    projectwise_O_S_BR.rename(columns={'count':'Total Application'}, inplace=True)
    projectwise_O_S_BR.reset_index(inplace=True)
    projectwise_O_S_BR.loc[len(projectwise_O_S_BR.index)] = ['Grand Total', projectwise_O_S_BR['Total Application'].sum()] # Total of all status
    
    # Defining a function for pie chart labels
    def func(pct, allvalues):
        absolute = int(pct / 100.*np.sum(allvalues))
        return "{:.1f}%\n{:d}".format(pct, absolute)

    # Plotting data using pie chart
    try:
        projectwise_O_S_BR = projectwise_O_S_BR.iloc[[1,2,0,3]]
        fig, ax = plt.subplots()
        ax.pie(projectwise_O_S_BR['Total Application'][0:3], labels=projectwise_O_S_BR['Status'][0:3], rotatelabels=False, autopct=lambda pct: func(pct, projectwise_O_S_BR['Total Application'][0:3]), explode=[0.01,0.05,0.09], shadow = True, textprops={'fontsize' : 'small'}, labeldistance = 0.8)
        ax.set_title('Statuswise Summary')
    except IndexError:
        try:
            projectwise_O_S_BR = projectwise_O_S_BR.iloc[[1,0,2]]
            fig, ax = plt.subplots()
            ax.pie(projectwise_O_S_BR['Total Application'][0:2], labels=projectwise_O_S_BR['Status'][0:2], rotatelabels=False, autopct=lambda pct: func(pct, projectwise_O_S_BR['Total Application'][0:2]), explode=[0.01,0.05], shadow = True, textprops={'fontsize' : 'small'}, labeldistance = 0.8)
            ax.set_title('Statuswise Summary')
        except IndexError:
            fig, ax = plt.subplots()
            ax.pie(projectwise_O_S_BR['Total Application'][0:1], labels=projectwise_O_S_BR['Status'][0:1], rotatelabels=False, autopct=lambda pct: func(pct, projectwise_O_S_BR['Total Application'][0:1]), explode=[0.05], shadow = True, textprops={'fontsize' : 'small'}, labeldistance = 0.8)
            ax.set_title('Statuswise Summary')

    # District wise status summary
    districtWise = pd.pivot_table(data=df, index='District', columns='Status', values='Case Id', aggfunc='count', fill_value=0).reset_index()

    if 'Benefit Received' not in list(df.Status.value_counts().index):
        districtWise.loc[len(districtWise)] = ['Grand Total',districtWise['Open'].sum(),districtWise['Submitted'].sum()]
        districtWise['Total'] = districtWise['Open']+districtWise['Submitted']
        districtWise = districtWise[['District', 'Open', 'Submitted', 'Total']]

    elif 'Submitted' not in list(df.Status.value_counts().index):
        districtWise.loc[len(districtWise)] = ['Grand Total',districtWise['Benefit Received'].sum(),districtWise['Open'].sum()]
        districtWise['Total'] = districtWise['Benefit Received']+districtWise['Open']
        districtWise = districtWise[['District', 'Open', 'Benefit Received', 'Total']]

    elif 'Open' not in list(df.Status.value_counts().index):
        districtWise.loc[len(districtWise)] = ['Grand Total',districtWise['Benefit Received'].sum(),districtWise['Submitted'].sum()]
        districtWise['Total'] = districtWise['Benefit Received']+districtWise['Submitted']
        districtWise = districtWise[['District', 'Submitted', 'Benefit Received', 'Total']]

    else:
        districtWise.loc[len(districtWise)] = ['Grand Total',districtWise['Benefit Received'].sum(),districtWise['Open'].sum(),districtWise['Submitted'].sum()]
        districtWise['Total'] = districtWise['Benefit Received']+districtWise['Submitted']+districtWise['Open']
        districtWise = districtWise[['District', 'Open', 'Submitted', 'Benefit Received', 'Total']]

    # Scheme wise status summary
    Sch_O_S_BR = pd.pivot_table(data = df, index='Scheme/Doc', columns='Status', values='Case Id', aggfunc='count', fill_value=0)
    Sch_O_S_BR = pd.DataFrame(Sch_O_S_BR).reset_index()
    if 'Benefit Received' not in Sch_O_S_BR.columns:
        if 'Submitted' not in Sch_O_S_BR.columns:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Open']] # Open' & 'Submitted
            Sch_O_S_BR['Total'] = Sch_O_S_BR['Open'].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Open.sum(), Sch_O_S_BR.Total.sum()]
        elif 'Open' not in Sch_O_S_BR.columns:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Submitted']] # Open' & 'Submitted
            Sch_O_S_BR['Total'] = Sch_O_S_BR['Submitted'].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Submitted.sum(), Sch_O_S_BR.Total.sum()]
        else:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Open', 'Submitted']]
            Sch_O_S_BR['Total'] = Sch_O_S_BR[['Open', 'Submitted']].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Open.sum(), Sch_O_S_BR.Submitted.sum(), Sch_O_S_BR.Total.sum()]
    elif 'Submitted' not in Sch_O_S_BR.columns:
        if 'Benefit Received' not in Sch_O_S_BR.columns:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Open']] # Open' & 'Submitted
            Sch_O_S_BR['Total'] = Sch_O_S_BR['Open'].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Open.sum(), Sch_O_S_BR.Total.sum()]
        elif 'Open' not in Sch_O_S_BR.columns:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Benefit Received']] # Open' & 'Submitted
            Sch_O_S_BR['Total'] = Sch_O_S_BR['Benefit Received'].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR['Benefit Received'].sum(), Sch_O_S_BR.Total.sum()]
        else:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Open', 'Benefit Received']]
            Sch_O_S_BR['Total'] = Sch_O_S_BR[['Open', 'Benefit Received']].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Open.sum(), Sch_O_S_BR['Benefit Received'].sum(), Sch_O_S_BR.Total.sum()]
    elif 'Open' not in Sch_O_S_BR.columns:
        if 'Benefit Received' not in Sch_O_S_BR.columns:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Submitted']] # Open' & 'Submitted
            Sch_O_S_BR['Total'] = Sch_O_S_BR['Submitted'].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Open.sum(), Sch_O_S_BR.Total.sum()]
        elif 'Submitted' not in Sch_O_S_BR.columns:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Benefit Received']] # Open' & 'Submitted
            Sch_O_S_BR['Total'] = Sch_O_S_BR['Benefit Received'].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR['Benefit Received'].sum(), Sch_O_S_BR.Total.sum()]
        else:
            Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Submitted', 'Benefit Received']]
            Sch_O_S_BR['Total'] = Sch_O_S_BR[['Submitted', 'Benefit Received']].sum(axis=1)
            Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Submitted.sum(), Sch_O_S_BR['Benefit Received'].sum(), Sch_O_S_BR.Total.sum()]
    else:
        Sch_O_S_BR = Sch_O_S_BR[['Scheme/Doc', 'Open', 'Submitted', 'Benefit Received']]
        Sch_O_S_BR['Total'] = Sch_O_S_BR[['Open', 'Submitted', 'Benefit Received']].sum(axis=1)
        Sch_O_S_BR.loc[len(Sch_O_S_BR)] = ['Grand Total', Sch_O_S_BR.Open.sum(), Sch_O_S_BR.Submitted.sum(), Sch_O_S_BR['Benefit Received'].sum(), Sch_O_S_BR.Total.sum()]
        
    return projectwise_O_S_BR, districtWise, Sch_O_S_BR, fig

# Defining a function to get orgwise scheme diversity
def orgwiseSchDiv(df):
    orgSchDiver = df.pivot_table(index=['State','Scheme/Doc'], values='Case Id', aggfunc='count') # Pivoting unique data with "Case Organization" & "Scheme/Doc" rows and count of column "Case Id"
    orgSchDiver.reset_index(inplace=True)
    Orgwise_Scheme_Diversity = pd.DataFrame(orgSchDiver['State'].value_counts()).reset_index().rename(columns={'count':'Count of unique schemes'}).sort_values('State') # Converting pivot table to pandas data frame
    Orgwise_Scheme_Diversity['Total Applications'] = orgSchDiver.groupby(by = 'State')['Case Id'].sum().values # Adding "Total no. of cases" column

    '''# 18-35 - DFL Advance/Basic BR
    digital_Adult = df[(df['Age'] >= 18) & (df['Age'] <= 35) & (df['Status'] == 'Benefit Received')]
    digital_Adult = pd.pivot_table(data=digital_Adult, index = 'Scheme/Doc', values = 'Case Id', aggfunc='count').reset_index()
    try:
        Orgwise_Scheme_Diversity['18-35 - DFL Advance/Basic BR'] = digital_Adult[(digital_Adult['Scheme/Doc'] == 'Digital productivity Service_ Basic') |
                                                                            (digital_Adult['Scheme/Doc'] == 'Digital Productivity Services_Advanced')].sum()[1]
    except IndexError:
        Orgwise_Scheme_Diversity['18-35 - DFL Advance/Basic BR'] = digital_Adult[(digital_Adult['Scheme/Doc'] == 'Digital productivity Service_ Basic') |
                                                                            (digital_Adult['Scheme/Doc'] == 'Digital Productivity Services_Advanced')].sum()[0]'''

    # Shcemes with more than 10% application
    orgDict = {} # Declaring a empty dictionary to store Shcemes with more than 10% application
    for org in Orgwise_Scheme_Diversity['State']:
        maxApp = pd.DataFrame(orgSchDiver[orgSchDiver['State'] == org].groupby('Scheme/Doc')['Case Id'].sum()
                            >
                            int(orgSchDiver[orgSchDiver['State'] == org]['Case Id'].sum()/10)) # Getting list of more then 10% application
        orgDict[org] = list(maxApp[maxApp['Case Id'] == True].index)
    Orgwise_Scheme_Diversity['Shcemes with more than 10% application'] = orgDict.values() # Adding "Shcemes with more than 10% application" column

    Orgwise_Scheme_Diversity.rename(columns={"Count of unique schemes":"Total unique schemes"}, inplace=True)
    
    # Ploting the data on bar chart.
    fig, ax = plt.subplots(1,2, sharex=True)

    bar_container1 = ax[0].bar(Orgwise_Scheme_Diversity.State, Orgwise_Scheme_Diversity['Total unique schemes'], color = '#FF796C')
    bar_container2 = ax[1].bar(Orgwise_Scheme_Diversity.State, Orgwise_Scheme_Diversity['Total Applications'], color = '#029386')

    ax[0].tick_params(axis = 'y', labelsize = 7.0)
    ax[1].tick_params(axis = 'y', labelsize = 7.0)

    ax[0].bar_label(bar_container1, fmt='{:,.0f}', fontsize=6.0)
    ax[1].bar_label(bar_container2, fmt='{:,.0f}', fontsize=6.0)

    ax[0].set_xticklabels(Orgwise_Scheme_Diversity.State, fontsize=5.0, rotation=45)
    ax[1].set_xticklabels(Orgwise_Scheme_Diversity.State, fontsize=5.0, rotation=45)

    if len(Orgwise_Scheme_Diversity.State)>1:
        ax[0].set(title = 'Total unique schemes')
        ax[1].set(title = 'Total Applications')
    else:
        ax[0].set(title = 'Total unique schemes', ylim = (math.floor(Orgwise_Scheme_Diversity['Total unique schemes'])-1, math.ceil(Orgwise_Scheme_Diversity['Total unique schemes'])+2))
        ax[1].set(title = 'Total Applications', ylim = (math.floor(Orgwise_Scheme_Diversity['Total Applications']), math.ceil(Orgwise_Scheme_Diversity['Total Applications'])))

    return Orgwise_Scheme_Diversity, fig

# Deffining a function to get citizen scheme ratio
def citSchRatio(df):
    # Initiate dictionary to store values
    cit_sch_ratio = {'Scheme Variety':[],
                    'Total Citizens':[],
                    'Total Cases':[]}

    no_of_cases = list(set(df['No of cases'].value_counts().index))
    no_of_case = []
    no_of_cit = []
    for n in no_of_cases:
        if n == 0:
            df.drop(index=(df[df['No of cases'] == n].index), inplace=True)
        
        elif n>0 and n<=3: 
            cit_sch_ratio['Scheme Variety'].append('With {0} scheme'.format(n))
            cit_sch_ratio['Total Citizens'].append(len(df[df['No of cases'] == n]['Citizen GUID'].value_counts()))
            cit_sch_ratio['Total Cases'].append(len(df[df['No of cases'] == n]))
        
        elif n>3: # Citizen with more than 3 scheme
            if 'More than 3 schemes' in cit_sch_ratio['Scheme Variety']:
                no_of_case.append(len(df[df['No of cases'] == n]))
                no_of_cit.append(len(df[df['No of cases'] == n]['Citizen GUID'].value_counts()))
                
            else:
                cit_sch_ratio['Scheme Variety'].append('More than 3 schemes')
                no_of_case.append(len(df[df['No of cases'] == n]))
                no_of_cit.append(len(df[df['No of cases'] == n]['Citizen GUID'].value_counts()))
        
        else:
            break

    # Adding sum of cases and citizens against "More than 3 schemes"
    if n>3:
        cit_sch_ratio['Total Cases'].append(sum(no_of_case))
        cit_sch_ratio['Total Citizens'].append(sum(no_of_cit))

    # Grand Total
    cit_sch_ratio['Scheme Variety'].append('Grand Total')
    cit_sch_ratio['Total Citizens'].append(sum(cit_sch_ratio['Total Citizens']))
    cit_sch_ratio['Total Cases'].append(sum(cit_sch_ratio['Total Cases']))

    # More than 7 schemes
    if len(df[df['No of cases'] >= 7]) > 0:
        cit_sch_ratio['Scheme Variety'].append('More than 7 schemes')
        cit_sch_ratio['Total Cases'].append(len(df[df['No of cases'] >= 7]))
        cit_sch_ratio['Total Citizens'].append(len(df[df['No of cases'] >= 7]['Citizen GUID'].value_counts()))

    # Plotting data using line chart
    cit_sch_ratio = pd.DataFrame(cit_sch_ratio)
    x = cit_sch_ratio[~(cit_sch_ratio['Scheme Variety']=='Grand Total')]

    fig, ax = plt.subplots(1)
    ax.plot(x['Scheme Variety'], x[['Total Citizens','Total Cases']], marker = 'H', linestyle = '-.')
    ax.set_xticklabels(labels=x['Scheme Variety'], fontdict={'fontsize':7.0})
    ax.legend(['Total Citizens','Total Cases'])
    ax.set(title = 'Citizen Scheme Ratio')
    for i, (xi, yi, zi) in enumerate(zip(x['Scheme Variety'], x['Total Citizens'], x['Total Cases'])):
        ax.annotate(f'Citizens:\n<{yi}>', (xi, yi), textcoords="offset points", xytext=(0, 10), ha='right', va='top', fontsize = 6.0, fontname='sans-serif', color = 'red')
        ax.annotate(f'Cases:\n<{zi}>', (xi, zi), textcoords="offset points", xytext=(0, 10), ha='left', va='bottom', fontsize = 6.0, fontname='sans-serif', color = 'red')

    return cit_sch_ratio, fig

# Defining a function to get achievement of HDs
def hdAchv(df):
    step = df.copy() # Copying data to another variable to make some changes.
    step['HD ID'] = step['HD ID'].fillna('a') # Replacing missing values with simple character 'a'
    step['HD ID'] = step['HD ID'].astype('str') # Changing HD ID column data type to string so that all values can be converted to lower case.
    step['HD ID'] = step['HD ID'].apply(lambda x: x.lower()) # Changing values to lower case.
    
    step1 = pd.pivot_table(data = step, index = ['HD ID', 'HD Name','Scheme/Doc GUID'], values = 'Case Id', aggfunc = 'count') # Pivoting to get unique HD ID/ HD Name/ Scheme Name
    step1 = pd.DataFrame(step1.drop(columns='Case Id').reset_index()) # Delete unwanted column 'Case Id'
    step1 = pd.DataFrame(pd.pivot_table(data=step1, index=['HD ID','HD Name'], values='Scheme/Doc GUID', aggfunc='count').reset_index()).rename(columns={'Scheme/Doc GUID' : 'Total unique schemes'}) # Pivoting to get unique HD ID/ HD Name and unique count of schemes.
    
    step2 = pd.DataFrame(step.groupby(by = 'HD ID')['Case Id'].count()).reset_index().rename(columns={'Case Id' : 'Total Applications'})
    
    step3 = step.groupby('HD ID')['Benefit Value'].sum().reset_index()
    
    top_bottom_hd = step1.merge(step2, on = 'HD ID', how='left').merge(step3, on = 'HD ID', how='left')
    top_bottom_hd.rename(columns={'Benefit Value':'Benefit Value Delivered'}, inplace=True)
    top_bottom_hd.loc[len(top_bottom_hd)] = ['Grand Total', '', top_bottom_hd['Total unique schemes'].sum(),
                                            top_bottom_hd['Total Applications'].sum(), top_bottom_hd['Benefit Value Delivered'].sum()]
    
    return top_bottom_hd

# Defining a function to get schemewise achievement
def schAchv(df):
    Scheme_Categorisation = pd.DataFrame(pd.pivot_table(data = df, index=['Scheme type', 'Scheme/Doc', 'Benefit Value'], values='Case Id', aggfunc= 'count')).reset_index()
    Scheme_Categorisation['Total BV Delivered'] = Scheme_Categorisation['Benefit Value']*Scheme_Categorisation['Case Id']
    Scheme_Categorisation.rename(columns={'Case Id':'Total Applications'}, inplace=True)
    Scheme_Categorisation.loc[len(Scheme_Categorisation)] = ['Grand Total', '', '', Scheme_Categorisation['Total Applications'].sum(), Scheme_Categorisation['Total BV Delivered'].sum()]
    
    return Scheme_Categorisation

# Defining a function to check the distribution of gender.
def genderDist(df):
    gen_Bif = pd.DataFrame(df['Gender'].value_counts()).reset_index()
    gen_Bif['% Contri.'] = round((gen_Bif['count']/df['Gender'].value_counts().sum())*100,2)
    gen_Bif.rename(columns={'count':'Total Applications'},inplace=True)
    gen_Bif.loc[len(gen_Bif)] = ['Total', gen_Bif['Total Applications'].sum(), '']
    gen_Bif[['Gender', 'Total Applications']][0:3].set_index('Gender').plot(kind='barh', color='#F5A3C7')

    # Plotting data using horizontal bar chart
    fig, ax = plt.subplots(1)

    if len(gen_Bif['Gender']) == 4:
        bar_container = ax.barh(data = gen_Bif[['Gender', 'Total Applications']][0:3], y = gen_Bif['Gender'][0:3], width = gen_Bif['Total Applications'][0:3], color = '#F5A3C7')
    elif len(gen_Bif['Gender']) == 3:
        bar_container = ax.barh(data = gen_Bif[['Gender', 'Total Applications']][0:2], y = gen_Bif['Gender'][0:2], width = gen_Bif['Total Applications'][0:2], color = '#F5A3C7')
    else:
        bar_container = ax.barh(data = gen_Bif[['Gender', 'Total Applications']][0:1], y = gen_Bif['Gender'][0:1], width = gen_Bif['Total Applications'][0:1], color = '#F5A3C7')

    ax.bar_label(bar_container, fmt='{:,.0f}', fontsize=8.0, fontfamily='serif', fontweight='bold')
    ax.set(title = 'Gender Bifurcation')

    fig.show()

    return gen_Bif, fig

# Defining a function to get repeatative mobile numbers
def repeatMobile(df):
    repeat_mobile = pd.pivot_table(data=df, index=['District', 'Mobile', 'Citizen GUID'], values='Case Id', aggfunc='count').sort_values(by='Case Id', ascending=False).reset_index()
    repeat_mobile = pd.pivot_table(data=repeat_mobile, index=['District', 'Mobile'], values='Citizen GUID', aggfunc='count').sort_values(by='Citizen GUID', ascending=False).reset_index()
    repeat_mobile = repeat_mobile[repeat_mobile['Citizen GUID']>30]
    if repeat_mobile['Citizen GUID'].sum()>0:
        repeat_mobile.loc[len(repeat_mobile)] = ['Grand Total','',repeat_mobile['Citizen GUID'].sum()]
    repeat_mobile.rename(columns={"Citizen GUID":"Total Citizens"}, inplace=True)
    return repeat_mobile

# Defining a function to log the execution process
def logging(category,uname,uemail,init_file_size, exe_start, exe_end, data, duplicateData, rejectedDF, fn):

    log = [category, uname, uemail, init_file_size, exe_start.strftime("%d/%m/%Y %H:%M:%S"),
           exe_end.strftime("%d/%m/%Y %H:%M:%S"), int(round((exe_end-exe_start).total_seconds(),0)),
           fn.split('.')[0],data.shape[0],duplicateData.shape[0],rejectedDF.shape[0]]

    lwb = load_workbook('.\Logs Remove Duplicate for Dashboard.xlsx') # Loading the workbook
    lws = lwb.worksheets[0] # Setting the worksheet
    lws.append(log) # Appending the log row
    lwb.save('.\Data_Transformer\Logs Remove Duplicate for Dashboard.xlsx') # Saving the logged data