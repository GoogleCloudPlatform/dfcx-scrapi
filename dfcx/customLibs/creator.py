#!/usr/bin/env python
# coding: utf-8

# In[7]:


import pandas as pd
import os, sys
import numpy as np
import time
import math
import google.cloud.dialogflowcx_v3beta1.types as types

module_path = os.path.abspath(os.path.join('../../../..'))
if module_path not in sys.path:
    sys.path.append(module_path)
    
from dfcx_sapi.dfcx.dfcx import DialogflowCX
from dfcx_sapi.dfcx.dfcx_functions import DialogflowFunctions


# In[20]:


#Create with and without entity tagging as toggle
#Different methods is from .csv or existing bot, etc. 
class creators:
    
    def __init__(self, creds, gcs_bucket_uri = None, store=True, agent_id=None):
        # Set the environment variable to use your uploaded creds
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds
        #Get class
        self.dfcx = DialogflowCX(creds)
        self.dffx = DialogflowFunctions(creds)
        self.agent_id = agent_id
        self.gcs_bucket_uri = gcs_bucket_uri
        self.store = store
        if store:
            self.dfcx.export_agent(agent_id=self.agent_id,gcs_bucket_uri = self.gcs_bucket_uri)
        return
        
        
        
    def progressBar(self,current, total, barLength = 50):
        percent = float(current) * 100 / total
        arrow   = '-' * int(percent/100 * barLength - 1) + '>'
        spaces  = ' ' * (barLength - len(arrow))
        print('Progress({0}/{1})'.format(current, total) + '[%s%s] %d %%' % (arrow, spaces, percent), end='\r')
        
        
        
    ''' 
    ***create an intent from a file with intent_name, training_phrase
    To do is add entity tagging. 
    '''
    def create_intents(self, filePath, naming_convention = None):
        if filePath == None:
            raise ValueError('must provide a file path in the parameters with the filePath key')
            
        new_intents_phrases = pd.read_csv(filePath)
        existing_intents = self.dfcx.list_intents(agent_id=self.agent_id)
        names = []
        for intent in existing_intents:
            names.append(intent.display_name)
        overlap = list(set(names) & set(new_intents_phrases['intent_name']))
        
        if len(overlap) > 0:
            print('{0} intent_name(s) are in new intents and existing intents'.format(overlap))

        i = 0
        for intent_ in list(set(new_intents_phrases['intent_name'])):
            if intent_ not in names:
                intent = types.intent.Intent()
                one_intent = new_intents_phrases[new_intents_phrases['intent_name']==intent_]
                training_phrases = []
                for index, row in one_intent.iterrows():
                    tps, parts = [], []
                    tp = types.intent.Intent.TrainingPhrase()
                    part = types.intent.Intent.TrainingPhrase.Part()
                    part.text = row['training_phrase']
                    parts.append(part)
                    tp.parts = parts
                    tp.repeat_count = 1
                    training_phrases.append(tp)

                setattr(intent, 'training_phrases', training_phrases)
                if naming_convention:
                    setattr(intent, 'display_name', naming_convention + row['intent_name'])
                else:
                    setattr(intent, 'display_name', row['intent_name'])
                setattr(intent, 'priority', 50000) 
                if i % 150 == 0 and i != 0:
                    time.sleep(61)
                self.dfcx.create_intent(agent_id=self.agent_id, obj=intent)
                i+=1
                self.progressBar(i, len(list(set(new_intents_phrases['intent_name']))) - len(overlap))
        if self.store:
            self.dfcx.export_agent(agent_id=self.agent_id,gcs_bucket_uri = self.gcs_bucket_uri[:-5] + '_postProcessing.blob')
        return

    '''Add training phrases to new intents'''
    def create_tps_intents(self, filePath):
        tps = pd.read_csv(filePath)
        intents = self.dfcx.list_intents(agent_id=self.agent_id)
        intents_update = list(set(tps['display_name']))
        i=0
        for intent in intents_update:
            new_phrases = tps[tps['display_name']==intent]
            for intentPb in intents:
                if intentPb.display_name == intent:
                    training_phrases = intentPb.training_phrases 
                    for index, row in new_phrases.iterrows():
                        training_phrase = types.Intent.TrainingPhrase()
                        part = types.Intent.TrainingPhrase.Part()
                        part.text = row['training_phrase']
                        training_phrase.parts = [part]
                        training_phrase.repeat_count = 1
                        training_phrases.append(training_phrase)
                    intentPb.training_phrases = training_phrases
                    if i % 150 == 0 and i != 0:
                        time.sleep(61)
                    self.dfcx.update_intent(intent_id=intentPb.name, obj=intentPb)
                    i+=1
                    self.progressBar(i, len(intents_update))
        
        if self.store:
            self.dfcx.export_agent(agent_id=self.agent_id,gcs_bucket_uri = self.gcs_bucket_uri[:-5] + '_postProcessing.blob')

                    
                    
                    
                    
    '''create route group by providing intents + other data like params and fullfillment and transition first 
    display_name, parameters, .... intents should be created first. '''
    def create_route_group(self, rg):
        return
    
    
    def restore(self,gsc_bucket_uri_spec= None):
            if gsc_bucket_uri_spec:
                return self.dfcx.restore_agent(agent_id=self.agent_id,gcs_bucket_uri=gsc_bucket_uri_spec)
            return self.dfcx.restore_agent(agent_id=self.agent_id,gcs_bucket_uri=self.gcs_bucket_uri)
        
    



