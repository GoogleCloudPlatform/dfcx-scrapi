#!/usr/bin/env python
# coding: utf-8

# In[5]:


#notes
#enable autocomplete - %config Completer.use_jedi = False
'''
Take first one in the list and vz chooses which is belongs to out of intents and then they can pick and move all to that one. 
Move all to one or remove all the ones that are not within the selcted one. 
Need to add funcitonality for other validation results ie removing non connected pages?
'''

import os, sys
module_path = os.path.abspath(os.path.join('../../../../'))
if module_path not in sys.path:
    sys.path.append(module_path)
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.client import GoogleCredentials
import numpy as np
import google.cloud.dialogflowcx_v3beta1.types as types

    

from dfcx_sapi.dfcx.dfcx import DialogflowCX
from dfcx_sapi.dfcx.dfcx_functions import DialogflowFunctions

import pygsheets
import gspread
import pickle
import re
#authorization
from oauth2client.service_account import ServiceAccountCredentials


# In[38]:


class reader:
    
    def __init__(self, creds, agent_id=None):
        self.creds= creds
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds
        self.dfcx = DialogflowCX(creds)
        self.dffx = DialogflowFunctions(creds)
        self.agent_id= agent_id
        
    
    #Static methods
    def create_col(self, num, list_):
        '''helps format for gsheets transition'''
        if num < len(list_):
            return list_[num]
        else:
            return ''
                
    def intent_disambg_internal(self,gsheets=False, flow_parse = None):
        '''uses validation function to create all validaiton for intent disambiguation'''
        validation = self.dfcx.validate(self.agent_id)
        validation_df = self.dffx.validation_results_to_dataframe(validation)
        if flow_parse != None:
            validation_df = validation_df[validation_df['flow']==flow_parse]
        #Parse df
        validation_df = validation_df[['flow','detail','resource1','resource2','resource3','resource4']]
        disambig_id,intents_list, tp_list,id_  = [], [], [], 0
        flows = []
        for index, row in validation_df.iterrows():
            deets, flow = row['detail'], row['flow']
            if bool(re.search('Multiple intents share training phrases which are too similar:',deets)):
                intents = re.findall('Intent \'(.*)\': training phrase ', deets)
                training_phrases = re.findall('training phrase \'(.*)\'',deets)
                intents_list = intents_list + intents
                tp_list = tp_list + training_phrases
                disambig_id = disambig_id + ([id_]*len(training_phrases))
                flows = flows + ([flow]*len(training_phrases))
                id_ += 1

        extraction = pd.DataFrame()
        extraction['disambig_id'] = disambig_id
        extraction.insert(0,'flow',flows)
        extraction['intent'] = intents_list
        extraction['training_phrase'] = tp_list
        intent_options = extraction.groupby(['disambig_id'])['intent'].apply(list).reset_index().rename(columns={'intent':'intents'})
        intent_options['intents'] = intent_options.apply(lambda x: list(set(x['intents'])),axis=1)
        extraction = pd.merge(extraction, intent_options, on=['disambig_id'],how='left')
        internal = extraction.copy()
        internal['intent_count'] = internal.apply(lambda x: len(x['intents']),axis=1)
        external = extraction.groupby(['flow','disambig_id'])[['training_phrase','intents']].first().reset_index()
        external['intent_count'] = external.apply(lambda x: len(x['intents']),axis=1)
        
        count_cols = external['intent_count'].max()
        if gsheets:
            for i in range(0,count_cols):
                external['intent option '+ str(i+1)] = external.apply(lambda x: self.create_col(i, x['intents']),axis=1)
                external['include in intent ' + str(i+1)] = ['']*len(external)
            external = external.copy().drop(columns=['intent_count','intents'])

        return {'internal':internal , 'external': external}
    
    
    def list_files_service_acct(self):
        '''Lists files in the service account g-drive'''
        
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(self.creds, scope)
        service = build('drive', 'v3', credentials=creds_gdrive, cache_discovery=False)
        # Call the Drive v3 API
        results = service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
        else:
            print('Existing Shared Files:')
            files = []
            for item in items:
                print(u'{0}: {1}'.format(item['name'], item['id']))
                files.append(item['name'])
        return files
    
    
    def create_gsheets(self, gsheet_name, internal_data, external_data):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(self.creds, scope)
        client = gspread.authorize(creds_gdrive)
        try:
            g_sheets = client.open(gsheet_name)
        except:
            list_files_service_acct(creds=creds)
            raise ValueError('Is the selected gsheet shared with the email in your creds file?')
        try:
            external = g_sheets.worksheet('external')
        except: 
            external = g_sheets.add_worksheet(title="external", rows=str(len(external_data)), cols=str(len(external_data.columns)))    
        try:
            internal = g_sheets.worksheet('internal')
        except:
            internal = g_sheets.add_worksheet(title="internal", rows=str(len(internal_data)), cols=str(len(internal_data.columns)))

        set_with_dataframe(external, external_data)
        set_with_dataframe(internal, internal_data)
        try:
            initial_sheet = g_sheets.worksheet('Sheet1')
            g_sheets.del_worksheet(initial_sheet)
            return "success"
        except:
            return "success"
        
        
    def internal_disambiguation(self, gsheet_name=None):
        if gsheet_name:
            intent_disambg = self.intent_disambg_internal(gsheets=True)
            self.create_gsheets(gsheet_name=gsheet_name, internal_data=intent_disambg['internal'], external_data=intent_disambg['external'])
        else:
            return self.intent_disambg_internal()
            
        
    
    





# In[ ]:





# In[ ]:





# In[ ]:





# In[115]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




