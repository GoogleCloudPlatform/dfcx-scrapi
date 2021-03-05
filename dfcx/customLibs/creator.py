#!/usr/bin/env python
# coding: utf-8

# In[7]:


import pandas as pd
import os, sys
import numpy as np
import time
import math
import google.cloud.dialogflowcx_v3beta1.types as types
import json
import ast
from google.oauth2 import service_account
import pygsheets
import gspread
import pickle
#authorization
from oauth2client.service_account import ServiceAccountCredentials

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
        self.creds = creds
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
    def create_intents(self, gsheet, worksheet, naming_convention = None):
        
        
        scope = ['https://spreadsheets.google.com/feeds',
                         'https://www.googleapis.com/auth/drive']
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(self.creds, scope)
        client = gspread.authorize(creds_gdrive)
        g_sheets = client.open(gsheet)
        sheet = g_sheets.worksheet(worksheet)
        dataPull = data = sheet.get_all_values()
        new_intents_phrases = pd.DataFrame(columns=dataPull[0],data=dataPull[1:])
        
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
    def create_tps_intents(self, gsheet, worksheet):
        scope = ['https://spreadsheets.google.com/feeds',
                         'https://www.googleapis.com/auth/drive']
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(self.creds, scope)
        client = gspread.authorize(creds_gdrive)
        g_sheets = client.open(gsheet)
        sheet = g_sheets.worksheet(worksheet)
        dataPull = data = sheet.get_all_values()
        tps = pd.DataFrame(columns=dataPull[0],data=dataPull[1:])
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
    def create_transition_route(self, intent, condition, target_flow, target_page,
                                customPayload, webhook, webhook_tag, parameter_presets, fulfillment_text):
        transitionRoute = types.TransitionRoute()
        transitionRoute.intent = intent
        transitionRoute.condition = condition
        transitionRoute.target_page = target_page
        transitionRoute.target_flow = target_flow

        #fulfillment
        fulfillment = types.Fulfillment()
        fulfillment.webhook = webhook
        fulfillment.tag = webhook_tag

        custy_payloads = []
        if customPayload:
            customPayload = json.loads(customPayload)
            for cp in customPayload:
                custy_payloads.append({'payload':cp})

        if fulfillment_text:
            fulfillment_text = ast.literal_eval(fulfillment_text)

        #custom payloads and text
        #cp = json.loads(customPayload)
        payload = {"messages": 
            custy_payloads +
            [{'text': {'text': fulfillment_text}}]
                  }


        payload_json = json.dumps(payload) 
        payload_json = json.dumps(payload) 
        fulfillment = types.Fulfillment.from_json(payload_json)

        #parameter - presets
        set_param_actions = []

        if parameter_presets:
            parameter_presets = json.loads(parameter_presets)
            for param in parameter_presets.keys():
                set_param_action = types.Fulfillment.SetParameterAction()
                set_param_action.parameter = param
                set_param_action.value = parameter_presets[param]
                set_param_actions.append(set_param_action)
        fulfillment.set_parameter_actions = set_param_actions
        transitionRoute.trigger_fulfillment = fulfillment

        return transitionRoute



    def create_routeGroup(self, display_name, routes, flow_id):
        existing_rgs = dict((v,k) for k,v in self.dffx.get_route_groups_map(flow_id=flow_id).items())
        if display_name in existing_rgs.keys():
            raise ValueError('route group name {0} exists in flow {1}'.format(display_name,flow_id))
        rg = types.TransitionRouteGroup()
        rg.display_name = display_name
        rg.transition_routes = routes
        return rg
    
    def create_RG(self, gsheet,worksheet,RG_name,flow_name):
        scope = ['https://spreadsheets.google.com/feeds',
                         'https://www.googleapis.com/auth/drive']
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(self.creds, scope)
        client = gspread.authorize(creds_gdrive)
        g_sheets = client.open(gsheet)
        sheet = g_sheets.worksheet(worksheet)

        flow_map = dict((v,k) for k,v in self.dffx.get_flows_map(agent_id=self.agent_id).items())
        intents_map = dict((v,k) for k,v in self.dffx.get_intents_map(agent_id=self.agent_id).items())

        flow_i = flow_map[flow_name]
        page_map = dict((v,k) for k,v in self.dffx.get_pages_map(flow_id=flow_i).items())
        routes = []
        i = 0
        dataPull = sheet.get_all_values()[1:]
        i = 0
        for data in dataPull:
            data = [None if x=='' else x for x in data]
            intent = intents_map.get(data[0] if 0 < len(data) else None ,None)
            if intent == None:
                print(data)
            condition=data[1] if 1 < len(data) else None
            fulfillment_text = data[2] if 2 < len(data) else None
            customPayload=data[3] if 3 < len(data) else None
            parameter_presets=data[4] if 4 < len(data) else None
            webhook=data[5] if 5 < len(data) else None
            webhook_tag=data[6] if 6 < len(data) else None
            target_flow= flow_map.get(data[7] if 7 < len(data) else None ,None)
            target_page=page_map.get(data[8] if 8 < len(data) else None ,None)

            route = self.create_transition_route(intent=intent, condition=condition, fulfillment_text=fulfillment_text,
                                    customPayload=customPayload, parameter_presets=parameter_presets, webhook=webhook,
                                   webhook_tag=webhook_tag,target_flow=target_flow, target_page=target_page)
            i+=1
            routes.append(route)
            self.progressBar(current=i,total=len(dataPull))

        RG = self.create_routeGroup(routes=routes, flow_id=flow_i,display_name=RG_name)
        
        self.dfcx.create_transition_route_group(flow_id=flow_map[flow_name],obj=RG)

        return RG


    
    def restore(self,gsc_bucket_uri_spec= None):
            if gsc_bucket_uri_spec:
                return self.dfcx.restore_agent(agent_id=self.agent_id,gcs_bucket_uri=gsc_bucket_uri_spec)
            return self.dfcx.restore_agent(agent_id=self.agent_id,gcs_bucket_uri=self.gcs_bucket_uri)
        
    


    
