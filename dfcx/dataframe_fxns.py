'''DFCX manipulation functions to extend dfcx_sapi lib'''

from typing import List

import json
import logging
import os
import google.cloud.dialogflowcx_v3beta1.types as types
from tabulate import tabulate
from .dfcx import *
from .dfcx_functions import *


# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class Dataframe_fxns:
    def __init__(self, creds_path: str):
        logging.info('create dfcx creds %s', creds_path)
        self.dfcx =  DialogflowCX(creds_path)
        logging.info('create dffx creds %s', creds_path)
        self.dffx =  DialogflowFunctions(creds_path)


    def update_intent_from_dataframe(self, intent_id: str, train_phrases: List[str],
                                     params=pd.DataFrame(), mode='basic'):
        """update an existing intents training phrases and parameters
        the intent must exist in the agent
        this function has a dependency on the agent

        Args:
            intent_id: name parameter of the intent to update
            train_phrases: dataframe of training phrases 
                in advanced have training_phrase and parts column to track the build
            params(optional): dataframe of parameters
            mode: 
                basic - build assuming one row is one training phrase no entities, 
                advance - build keeping track of training phrases and 
                    parts with the training_phrase and parts column. 

        Returns:
            intent_pb: the new intents protobuf object
        """

        if mode == 'basic':
            try: 
                train_phrases = train_phrases[['text']]
                train_phrases = train_phrases.astype({'text':'string'})
            except:
                tpSchema = pd.DataFrame(index=['text','parameter_id'], columns=[0], data=['string','string']).astype({0:'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))

        elif mode == 'advanced':
            try: 
                train_phrases = train_phrases[['training_phrase', 'part','text', 'parameter_id']]
                train_phrases = train_phrases.astype({'training_phrase': 'int32', 'part':'int32',
                                                      'text':'string', 'parameter_id':'string'})
                if len(params) > 0:
                    params = params[['id','entity_type']]
                    params = params.astype({'id':'string', 
                                                     'entity_type':'string'})
            except:
                tpSchema = pd.DataFrame(index=['training_phrase', 'part','text','parameter_id'], columns=[0], data=['int32', 'int32','string','string']).astype({0:'string'})
                pSchema = pd.DataFrame(index=['id','entity_type'], columns=[0], data=['string','string']).astype({0:'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))
                logging.error('{0} mode parameter schema must be {1} \n'.format(
                    mode, tabulate(pSchema.transpose(), headers='keys', tablefmt='psql')))
                
        else:
            raise ValueError('mode must be basic or advanced')

 

        original = self.dfcx.get_intent(intent_id=intent_id)
        intent = {}
        intent['name'] = original.name
        intent['display_name'] = original.display_name
        intent['priority'] = original.priority
        intent['is_fallback'] = original.is_fallback
        intent['labels'] = dict(original.labels)
        intent['description'] = original.description

        #training phrases
        if mode == 'advanced':
            trainingPhrases = []
            for tp in range(0, int(train_phrases['training_phrase'].astype(int).max() + 1)):
                tpParts = train_phrases[train_phrases['training_phrase'].astype(int)==int(tp)]
                parts = []
                for _index, row in tpParts.iterrows():
                    part = {
                        'text': row['text'],
                        'parameter_id':row['parameter_id']
                    }
                    parts.append(part)

                trainingPhrase = {'parts': parts,
                                 'repeat_count':1,
                                 'id':''}
                trainingPhrases.append(trainingPhrase)
            
            intent['training_phrases'] = trainingPhrases
            parameters = []
            for _index, row in params.iterrows():
                parameter = {
                    'id':row['id'],
                    'entity_type':row['entity_type'],
                    'is_list':False,
                    'redact':False
                }
                parameters.append(parameter)
            
            if len(parameters) > 0:
                intent['parameters'] = parameters

        elif mode == 'basic':
            trainingPhrases = []
            for index, row in train_phrases.iterrows():
                part = {
                    'text': row['text'],
                    'parameter_id': None
                }
                parts = [part]
                trainingPhrase = {'parts': parts,
                                 'repeat_count':1,
                                 'id':''}
                trainingPhrases.append(trainingPhrase)
            intent['training_phrases'] = trainingPhrases
        else:
            raise ValueError('mode must be basic or advanced')

        jsonIntent = json.dumps(intent)
        intent_pb = types.Intent.from_json(jsonIntent)
        return intent_pb


    def bulk_update_intents_from_dataframe(self, agent_id, train_phrases_df, 
                                           params_df=pd.DataFrame(), mode='basic', update_flag=False):
        """update an existing intents training phrases and parameters

        Args:
            agent_id: name parameter of the agent to update_flag - full path to agent
            train_phrases_df: dataframe of bulk training phrases
                required columns: text, display_name
                in advanced mode have training_phrase and parts column to track the build
            params_df(optional): dataframe of bulk parameters
            mode: basic|advanced
                basic: build assuming one row is one training phrase no entities
                advanced: build keeping track of training phrases and parts with the training_phrase and parts column. 
            update_flag: True to update_flag the intents in the agent

        Returns:
            new_intents: dictionary with intent display names as keys and the new intent protobufs as values

        """
        if mode == 'basic':
            try: 
                train_phrases_df = train_phrases_df[['display_name','text']]
                train_phrases_df = train_phrases_df.astype({'display_name': 'string','text':'string'})
            except:
                tpSchema = pd.DataFrame(index=['display_name','text','parameter_id'], columns=[0], data=['string','string','string']).astype({0:'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))

        elif mode == 'advanced':
            try: 
                train_phrases_df = train_phrases_df[['display_name','training_phrase', 'part','text', 'parameter_id']]
                train_phrases_df = train_phrases_df.astype({'display_name':'string','training_phrase': 'int32', 'part':'int32',
                                                      'text':'string', 'parameter_id':'string'})
                if len(params_df) > 0:
                    params_df = params_df[['display_name','id','entity_type']]
                    params_df = params_df.astype({'display_name':'string', 'id':'string', 
                                                     'entity_type':'string'})
            except:
                tpSchema = pd.DataFrame(index=['display_name','training_phrase', 'part','text','parameter_id'], columns=[0], data=['string', 'int32', 'int32','string','string']).astype({0:'string'})
                pSchema = pd.DataFrame(index=['display_name','id','entity_type'], columns=[0], data=['string','string','string']).astype({0:'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))
                logging.error('{0} mode parameter schema must be {1} \n'.format(
                    mode, tabulate(pSchema.transpose(), headers='keys', tablefmt='psql')))
                
        else:
            raise ValueError('mode must be basic or advanced')

 

        logging.info('updating agent_id %s', agent_id)

        intents_map = self.dffx.get_intents_map(agent_id=agent_id, reverse=True)
        intent_names = list(set(train_phrases_df['display_name']))


        new_intents = {}
        for intent_name in intent_names:
            tps = train_phrases_df.copy()[train_phrases_df['display_name']==intent_name].drop(columns='display_name')
            params = pd.DataFrame()
            if mode == 'advanced':
                params = params_df.copy()[params_df['display_name']==intent_name].drop(columns='display_name')

            if not intent_name in intents_map.keys():
                logging.error('FAIL to update - intent not found: [%s]', intent_name)
                continue

            new_intents[intent_name] = intent_name
            logging.info('update intent %s', intent_name)
            new_intent = self.update_intent_from_dataframe(
                intent_id=intents_map[intent_name],
                train_phrases=tps,
                params=params,
                mode=mode)
            new_intents[intent_name] = new_intent
            if update_flag:
                self.dfcx.update_intent(intent_id=new_intent.name, obj=new_intent)

        return new_intents
