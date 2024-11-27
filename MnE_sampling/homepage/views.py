from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from datetime import datetime as dt
import pandas as pd, numpy as np
import xlsxwriter, openpyxl, os


# Create your views here.
def sampling_data(request):
    if request.method == 'POST' and request.FILES['file']:
        
        file = request.FILES['file']
        percent = round(int(request.POST.get('percent'))/100,2)
        uname = request.POST.get('name')
        uemail = request.POST.get('email')

        fs = FileSystemStorage(location="\\upload\\", base_url="\\upload\\")
        file_Name = fs.save(file.name, file)
        path = os.path.join(fs.location, file_Name)

        # Reading the file
        def csvORexcel(file_Name, path):
            try:
                if file_Name.split('.')[-1].startswith('c'):
                    df = pd.read_csv(path)
                    return df
                elif file_Name.split('.')[-1].startswith('x'):
                    df = pd.read_excel(path)
                    return df
            except FileNotFoundError:
                print("The file name {0} has not found".format(path))
        
        # Data Cleaning
        def cleaner(data0):
            # Replace null values
            if 'Scheme/Doc GUID' in data0.columns.to_list():
                data0['Scheme/Doc GUID'].fillna('a', inplace=True)
            else:
                try:
                    data0['Scheme Guid'].fillna('a', inplace=True)
                except Exception:
                    pass
            data0['Citizen Name'].fillna('a', inplace=True)
            data0['HD Name'].fillna('blank', inplace=True)
            data0['Citizen Mobile'].fillna(0, inplace=True)

            # Convert Mobile column from float to string for concatenation.
            data0['Citizen Mobile'] = data0['Citizen Mobile'].apply(lambda x: str(x).strip())
            #data0['HD Mobile'] = data0['HD Mobile'].apply(lambda x: str(x).strip())
            #data0['Mobile'] = data0['Mobile'].astype('int64')
            data0['Citizen Mobile'] = data0['Citizen Mobile'].astype('str')
            #data0['HD Mobile'] = data0['HD Mobile'].astype('str')
            
            # Changing Scheme column name to 'Scheme Name'.
            if 'Scheme Name' not in data0.columns.to_list():
                for col in data0.columns.to_list():
                    if 'e/' in col:
                        data0.rename(columns={col:'Scheme Name'},inplace=True)
                        break
                        
            # Checking duplicate records based on citizrn mobile number.
            duplicates = data0[data0.duplicated(['Citizen Mobile'], keep=False)] # Keeping duplicate records
            data0 = data0.drop(index = data0[data0.duplicated(['Citizen Mobile'], keep='last')].index) # Removing duplicate records.

            data0.reset_index(inplace=True, drop=True)
            duplicates.reset_index(inplace=True, drop=True)
            
            return(data0, duplicates)
        
        # Data Sampling
        def sampling(data0, percent):
            fr = percent
            samp = pd.DataFrame()
            try:
                for hd in data0['HD ID'].value_counts().index:
                    for sid in data0[data0['HD ID'] == hd]['Scheme/Doc GUID'].value_counts().index:
                        conditional_data = data0[(data0['HD ID'] == hd) & (data0['Scheme/Doc GUID'] == sid)]
                        if len(conditional_data) == 1:
                            if len(samp) == 0:
                                samp = conditional_data
                            else:
                                samp = pd.concat([samp, conditional_data])
                        elif len(conditional_data) == 2:
                            if len(samp) == 0:
                                samp = conditional_data.sample(n=1, random_state=1, replace=False)
                            else:
                                samp = pd.concat([samp,conditional_data.sample(n=1, random_state=1, replace=False)], ignore_index=False)
                        elif len(conditional_data) <= 4:
                            if len(samp) == 0:
                                samp = conditional_data.sample(frac=fr, random_state=1, replace=False)
                            else:
                                samp = pd.concat([samp,conditional_data.sample(frac=fr, random_state=1, replace=False)], ignore_index=False)
                        else:
                            if len(samp) == 0:
                                samp = conditional_data.sample(frac=fr, random_state=1, replace=False)
                            else:
                                samp = pd.concat([samp,conditional_data.sample(frac=fr, random_state=1, replace=False)], ignore_index=False)    
            except Exception:
                try:
                    for hd in data0['HD Name'].value_counts().index:
                        for sid in data0[data0['HD Name'] == hd]['Scheme Guid'].value_counts().index:
                            conditional_data = data0[(data0['HD Name'] == hd) & (data0['Scheme Guid'] == sid)]
                            if len(conditional_data) == 1:
                                if len(samp) == 0:
                                    samp = conditional_data
                                else:
                                    samp = pd.concat([samp, conditional_data])
                            elif len(conditional_data) == 2:
                                if len(samp) == 0:
                                    samp = conditional_data.sample(n=1, random_state=1, replace=False)
                                else:
                                    samp = pd.concat([samp,conditional_data.sample(n=1, random_state=1, replace=False)], ignore_index=False)
                            elif len(conditional_data) <= 4:
                                if len(samp) == 0:
                                    samp = conditional_data.sample(frac=fr, random_state=1, replace=False)
                                else:
                                    samp = pd.concat([samp,conditional_data.sample(frac=fr, random_state=1, replace=False)], ignore_index=False)
                            else:
                                if len(samp) == 0:
                                    samp = conditional_data.sample(frac=fr, random_state=1, replace=False)
                                else:
                                    samp = pd.concat([samp,conditional_data.sample(frac=fr, random_state=1, replace=False)], ignore_index=False)
                except Exception:
                    for hd in data0['HD Name'].value_counts().index:
                        for sid in data0[data0['HD Name'] == hd]['Scheme Name'].value_counts().index:
                            conditional_data = data0[(data0['HD Name'] == hd) & (data0['Scheme Name'] == sid)]
                            if len(conditional_data) == 1:
                                if len(samp) == 0:
                                    samp = conditional_data
                                else:
                                    samp = pd.concat([samp, conditional_data])
                            elif len(conditional_data) == 2:
                                if len(samp) == 0:
                                    samp = conditional_data.sample(n=1, random_state=1, replace=False)
                                else:
                                    samp = pd.concat([samp,conditional_data.sample(n=1, random_state=1, replace=False)], ignore_index=False)
                            elif len(conditional_data) <= 4:
                                if len(samp) == 0:
                                    samp = conditional_data.sample(frac=fr, random_state=1, replace=True)
                                else:
                                    samp = pd.concat([samp,conditional_data.sample(frac=fr, random_state=1, replace=False)], ignore_index=False)
                            else:
                                if len(samp) == 0:
                                    samp = conditional_data.sample(frac=fr, random_state=1, replace=False)
                                else:
                                    samp = pd.concat([samp,conditional_data.sample(frac=fr, random_state=1, replace=False)], ignore_index=False)
            
            samp.reset_index(inplace=True, drop=True)
            samp['sampling'] = str(fr*100)+'%' # Adding a column to identify sampled records
            data0 = data0.merge(samp[['Case ID','sampling']], how='left', on='Case ID') # Merging sampled identified column with unique data
            data0.sampling.fillna(value = str(100.0-(fr*100))+'%_2', inplace=True) # Filling missing values which have not identified
            remain=data0[data0.sampling == str(100.0-(fr*100))+'%'] # Filtering remaining data and storing with new variable.
            
            # Removing sampling column
            data0 = data0.drop(columns = 'sampling')
            samp = samp.drop(columns = 'sampling')
            remain = remain.drop(columns = 'sampling')
            
            return(samp, data0, remain, fr)
        
        # Exporting data to excel.
        def export_to_excel(samp, data0, remain, duplicates, path, fr):
            with pd.ExcelWriter(path) as writer:
                samp.to_excel(writer, sheet_name=str(fr*100)+'% sampling_1', index=False)
                remain.to_excel(writer, sheet_name=str(100.0-(fr*100))+'% sampling_2', index=False)
                data0.to_excel(writer, sheet_name='unique data', index=False)
                if duplicates.shape[0]>0:
                    duplicates.to_excel(writer, sheet_name='duplicates', index=False)

        try:
            exe_start = dt.now()
            data0 = csvORexcel(file_Name, path)
            data0, duplicates = cleaner(data0)
            samp, data0, remain, fr = sampling(data0, percent)
            export_to_excel(samp, data0, remain, duplicates, path, fr)
            exe_end = dt.now()

            # Logging the execution process.
            log = pd.DataFrame({'Date':[dt.now().strftime("%d/%m/%Y")], 'u_name':[uname], 'u_email':[uemail], 'file_name':[file_Name], 'percent':int(percent*100), 'exec_start':[exe_start.strftime("%H:%M:%S")], 'exec_end':[exe_end.strftime("%H:%M:%S")], 'processing_time(s)':[(exe_end-exe_start).seconds], 'status':['Success']})
            logs = pd.read_excel('upload/logs.xlsx')
            logs = pd.concat([logs,log])
            with pd.ExcelWriter('upload/logs.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                logs.to_excel(writer, sheet_name='logs', index=False)

            with open(path, 'rb') as file:
                response = HttpResponse(file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="{file_Name}"'

            # Optionally delete the file after serving it
            os.remove(path)

            return response


        except Exception as e:

            response = HttpResponse("Please provide the correct format of the data", status=409)
            exe_end = dt.now()

            # Logging the execution process.
            log = pd.DataFrame({'Date':[dt.now().strftime("%d/%m/%Y")], 'u_name':[uname], 'u_email':[uemail], 'file_name':[file_Name], 'percent':int(percent*100), 'exec_start':[exe_start.strftime("%H:%M:%S")], 'exec_end':[exe_end.strftime("%H:%M:%S")], 'processing_time(s)':[(exe_end-exe_start).seconds], 'status':['{0} : {1}'.format(type(e), e)]})
            logs = pd.read_excel('upload/logs.xlsx')
            logs = pd.concat([logs,log])
            with pd.ExcelWriter('upload/logs.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                logs.to_excel(writer, sheet_name='logs', index=False)

            # Optionally delete the file after serving it
            os.remove(path)  

            return response

    return render(request, "home.html")

