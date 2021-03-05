#!/usr/bin/env python
# coding: utf-8

# In[48]:


'''
Purpose: maniuplate existing intent composition, add net new intents from external data sources
Author: Henry Drescher
Best practice is to do intent tp removal and intent disambiguation first so none of the other functions mess up the tp matching'''
#add create new intents with and without entity tagging. 
#Do add tp to intents with and without tagging. 
#See about re

import pandas as pd
import os, sys
import numpy as np
import math
import google.cloud.dialogflowcx_v3beta1.types as types
from pytz import timezone
from datetime import datetime
import time
import re
import time

import pandas_gbq
from pandas_gbq import schema
from google.oauth2 import service_account

import string as string_pckg
import re

from nltk.tokenize import wordpunct_tokenize, WhitespaceTokenizer, word_tokenize
import itertools



module_path = os.path.abspath(os.path.join('../../../..'))
if module_path not in sys.path:
    sys.path.append(module_path)
    
module_path = os.path.abspath(os.path.join('../../intent_lib'))
if module_path not in sys.path:
    sys.path.append(module_path)

from update_intents_lib import *

from python_df_cx_api.dfcx.dfcx import DialogflowCX
from python_df_cx_api.dfcx.dfcx_functions import DialogflowFunctions


# In[66]:


class intent_lib:
    
    def __init__(self, creds, agent_id=None, gcs_bucket_uri = None, store=True, intent_limit=2000):
        # Set the environment variable to use your uploaded creds
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds
        #Get class
        self.dfcx = DialogflowCX(creds)
        self.dffx = DialogflowFunctions(creds)
        self.agent_id = agent_id
        self.gcs_bucket_uri = gcs_bucket_uri
        self.store = store
        self.intent_limit = intent_limit
        self.creds = creds
    

    #Split an intent from a protobuff to 2 dataframes 1 with training phrase data and one with parameter and meta data
    def granular_intent(self,intent):
        granular_intent_df = pd.DataFrame()
        training_phrase, part, text, parameter_id,tp_ids,repeated_count = [], [], [], [],[], []
        training_phrases = getattr(intent,'training_phrases')
        tp_num = 0
        for tp in training_phrases:
            parts = getattr(tp,'parts')
            part_num = 0
            for pt in parts:
                training_phrase.append(tp_num)
                repeated_count.append(tp.repeat_count)
                part.append(part_num)
                text.append(pt.text)
                if pt.parameter_id:
                    parameter_id.append(pt.parameter_id)
                else:
                    parameter_id.append(np.nan)
                if tp.id:
                    tp_ids.append(tp.id)
                else:
                    tp_ids.append(np.nan)
                part_num+=1
            tp_num+=1

        params = getattr(intent,'parameters')
        params_df = pd.DataFrame()
        id_, entity_type = [], []

        for param in params:
            id_.append(param.id)
            entity_type.append(param.entity_type)

        if len(id_) > 0:
            params_df['id'] = id_
            params_df['entity_type'] = entity_type
        else:
            id_ = [np.nan]
            entity_type = [np.nan]
            params_df['id'] = id_
            params_df['entity_type'] = entity_type
        params_df['priority'] = intent.priority
        params_df.insert(0,'display_name',intent.display_name)
        params_df.insert(0,'name',intent.name)
        granular_intent_df['training_phrase'] = training_phrase
        granular_intent_df['part'] = part
        granular_intent_df['text'] = text
        granular_intent_df['parameter_id'] = parameter_id
        granular_intent_df.insert(0,'display_name',intent.display_name)
        granular_intent_df.insert(0,'name',intent.name)
        granular_intent_df['repeat_count'] = repeated_count
        granular_intent_df['training_phrase_id'] = tp_ids

        return granular_intent_df,params_df


    #Get all intents from an agent into two dataframes 1 for training phrases and one for parameters
    def parse_intents(self):
        agent = self.agent_id
        intents = self.dfcx.list_intents(agent_id=agent)
        parsed_tps = pd.DataFrame()
        parsed_params = pd.DataFrame()
        for intent in intents:
            intent_df = self.granular_intent(intent=intent)
            tp_df = intent_df[0]
            params_df = intent_df[1]
            if len(parsed_tps)==0:
                parsed_tps = tp_df
            else:
                parsed_tps = parsed_tps.append(tp_df)
            parsed_params = parsed_params.append(params_df)
        if self.store == True:
            self.dfcx.export_agent(agent_id=self.agent_id,gcs_bucket_uri=self.gcs_bucket_uri)
        return parsed_tps.reset_index(drop=True),parsed_params
    
    
    
    #Turn a dataframe to a dict to create a protobuff with it
    def intent_df_to_dict(self,one_intent_tp, one_intent_params):
        one_intent_tp = one_intent_tp.sort_values(by=['training_phrase', 'part'],ascending=True).reset_index(drop=True)
        one_intent_params = one_intent_params.reset_index(drop=True)
        intent_dict = {}
        intent_dict['name'] = one_intent_tp['name'].iloc[0]
        intent_dict['display_name'] = one_intent_tp['display_name'].iloc[0]
        training_phrases_lst = []
        for tp in range(0,max(int(one_intent_tp['training_phrase'].max()+1),1)):
            one_tf = one_intent_tp[one_intent_tp['training_phrase']==tp]
            if len(one_tf) > 0:
                training_phrase = {}
                parts = []
                for index, row in one_tf.iterrows():
                    if isinstance(row['parameter_id'],str):
                        part_dict = {
                            'text':row['text'],
                            'parameter_id':row['parameter_id']
                        }
                    else: 
                        if pd.isna(row['parameter_id'])==True:
                            part_dict = {
                                'text':row['text']
                            }
                    parts.append(part_dict)
                training_phrase['parts'] = parts
                training_phrase['repeat_count'] = one_tf['repeat_count'].iloc[0].astype(int)
                if isinstance(row['training_phrase_id'],str):
                    training_phrase['training_phrase_id'] = str(one_tf['training_phrase_id'].iloc[0])
                training_phrases_lst.append(training_phrase)
        intent_dict['training_phrase'] = training_phrases_lst
        if len(one_intent_params[~one_intent_params['id'].isna()]) > 0:
            one_intent_params = one_intent_params[~one_intent_params['id'].isna()]
            parameters = []
            for index, row in one_intent_params.iterrows():
                parameter = {}
                parameter['id'] = row['id']
                parameter['entity_type'] = row['entity_type']
                parameters.append(parameter)
            intent_dict['parameters'] = parameters
        intent_dict['priority'] = one_intent_params['priority'].iloc[0]
        return intent_dict

    
    #Convert dict to protobuff
    def intent_dict_to_protobuff(self,intent_dict):
        intent = types.intent.Intent()
        training_phrases = []
        for training_phrase in intent_dict['training_phrase']:
            tps = []
            tp = types.intent.Intent.TrainingPhrase()
            parts = []
            for pt in training_phrase['parts']:
                part = types.intent.Intent.TrainingPhrase.Part()
                part.text = pt['text']
                part.parameter_id = pt.get('parameter_id')
                parts.append(part)
                
            tp.parts = parts
            tp.repeat_count = training_phrase.get("repeat_count")
            tp.id = training_phrase.get('training_phrase_id')
            training_phrases.append(tp)

        param_list = []
        if 'parameters' in intent_dict.keys():
            for param in intent_dict['parameters']:
                param_ = types.intent.Intent.Parameter()
                param_.id = param['id']
                param_.entity_type=param['entity_type']
                param_list.append(param_)

        setattr(intent, 'training_phrases', training_phrases)
        setattr(intent, 'name', intent_dict['name'])
        setattr(intent, 'display_name', intent_dict['display_name'])
        setattr(intent, 'priority', intent_dict['priority'])    
        setattr(intent,'parameters',param_list)
        return intent
    
    
    #training phrase and params df to protobuff for updating cx
    def intent_df_protobuff(self,one_intent_tp,one_intent_params):
        dxnary = self.intent_df_to_dict(one_intent_tp, one_intent_params)
        return self.intent_dict_to_protobuff(dxnary)

        
    def remove_blank_tp(self, dataframe_tp):
        phrases = dataframe_tp.groupby(['name','training_phrase', 'display_name'])['text'].apply(list).reset_index()
        def blank(text):
            text = ''.join(text)
            text = re.sub(r'[^\w\s]','',text)
            text = text.replace(' ','')
            if len(text.split()) > 0:
                return False
            else:
                return True
            
        phrases['blank'] = phrases['text'].apply(blank)
        blank_tp = phrases[phrases['blank']==True][['name','training_phrase','blank']]
        dataframe_tp = pd.merge(dataframe_tp,blank_tp,on=['name','training_phrase'],how='left')
        dataframe_tp = dataframe_tp[(dataframe_tp['blank']!=True)]
        #remove onlyblank parts too
        return dataframe_tp.drop(columns='blank')
    
    def progressBar(self,current, total, barLength = 50):
        percent = float(current) * 100 / total
        arrow   = '-' * int(percent/100 * barLength - 1) + '>'
        spaces  = ' ' * (barLength - len(arrow))
        print('Progress({0}/{1})'.format(current, total) + '[%s%s] %d %%' % (arrow, spaces, percent), end='\r')
    

    #Agg function to run pipelines
    def pipeline(self,pipeline_config, Generic_Cleanup=True, dfcx_update_intents=False,
             display_changes=False):
        update_intent_func = maniupulators()
        function_map = {
        'remove_specific_words': update_intent_func.remove_specific_words,
        'white_space_punc_tokenizer': update_intent_func.white_space_punc_tokenizer,
        'rmv_tp_spec_intent': update_intent_func.rmv_tp_spec_intent,
        'spell_checker': update_intent_func.spell_checker,
        'swap': update_intent_func.swap,
        'intent_disambiguation': update_intent_func.intent_disambiguation
        }

        parsed_intents = self.parse_intents()
        training_phrase_data = parsed_intents[0]
        parameter_data = parsed_intents[1]
   
        training_phrase_data['text'] = training_phrase_data.apply(lambda x: x['text'].replace('\n','').replace('\t','').replace('\r',''),axis=1)
        
        training_phrase_data['original'] = training_phrase_data['text']
        training_phrase_data['op_seq'] = training_phrase_data.apply(lambda x: list(),axis=1)
        
        #run pipeline
        pipeline = pipeline_config['operations']
        for sequence in pipeline:
            operation = function_map[sequence['function']]
            if sequence['function'] != 'intent_disambiguation':
                training_phrase_data = operation(training_phrase_data=training_phrase_data,params=sequence['args'])
            else:
                training_phrase_data, parameter_data = operation(training_phrase_data=training_phrase_data,parameter_data = parameter_data, params=sequence['args'])

        #Remove any new line chartacters, tabs, returns etc. do tokenization steps ie extra spaces removed, lowercase, etc. (See how this works coming after pipeline and before)
        if Generic_Cleanup:
            training_phrase_data['text'] = training_phrase_data.apply(lambda x: ''.join(update_intent_func.white_space_punc_tokenizer(x['text'])) if x['text'].split() else x['text'],axis=1)
            def mutated(text, new_text,op_seq, op):
                if text.lower()!= new_text.lower() and 'gcu' not in op_seq:
                    op_seq.append(op)
                    return op_seq
                else:
                    return op_seq
            op_seq = training_phrase_data.apply(lambda x: mutated(x['original'],x['text'],x['op_seq'], "gcu"), axis=1)
            training_phrase_data['op_seq'] = op_seq

        #Check the oness that get removed. find faster way for this.
        update_intents = self.remove_blank_tp(training_phrase_data)
        #remove any leading space on the first part just incase
        update_intents['text'] = update_intents.apply(lambda x: x['text'].lstrip() if x['part']==float(0) else x['text'],axis=1)
        update_intents = update_intents[update_intents['text']!='']
        
        parameter_data = parameter_data.drop_duplicates()
        #List to user what intents updated
        update_intents_naming = update_intents[update_intents.apply(lambda x: True if len(x['op_seq'])>0 else False, axis=1)][['name','display_name']].drop_duplicates()
        too_many_tp = []
        if dfcx_update_intents:
            i = 0
            for index, row in update_intents_naming.iterrows():
                intent = row['name']
                
                one_intent_tp = update_intents[update_intents['name']==intent]
                if one_intent_tp['training_phrase'].max() > self.intent_limit:
                    too_many_tp.append(row['display_name'])
                else:
                    one_intent_params = parameter_data[parameter_data['name']==intent]
                    intent_protobuff = self.intent_df_protobuff(one_intent_tp=one_intent_tp, one_intent_params=one_intent_params)
                    intent_name_pieces = str(intent_protobuff.name).split('/')
                    self.dfcx.update_intent(intent_id=intent_protobuff.name, obj= intent_protobuff)
                    if i % 179 == 0 and i != 0:
                        time.sleep(61)
                i+=1
                self.progressBar(i, len(update_intents_naming))
                    
        if len(update_intents_naming) == 0:
            return "Nothing was updated"
        if len(too_many_tp) > 0:
            print('\n {0} intents had over {1} training phrases and could not be updated \n non-updated: {2}'.format(len(too_many_tp), self.intent_limit,too_many_tp))
        
        if self.store:
            self.dfcx.export_agent(agent_id=self.agent_id,gcs_bucket_uri = self.gcs_bucket_uri[:-5] + '_postProcessing.blob')

        return update_intents

    '''revert to before pipeline changes'''
    def restore(self,gsc_bucket_uri_spec= None):
            if gsc_bucket_uri_spec:
                return self.dfcx.restore_agent(agent_id=self.agent_id,gcs_bucket_uri=gsc_bucket_uri_spec)
            return self.dfcx.restore_agent(agent_id=self.agent_id,gcs_bucket_uri=self.gcs_bucket_uri)
    


# In[61]:



        
        
        


# In[ ]:





# In[33]:





# In[34]:





# In[14]:





# In[ ]:





# In[ ]:





# In[ ]:




