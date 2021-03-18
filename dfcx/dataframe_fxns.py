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
    def __init__(self, creds: str):
        self.dfcx =  DialogflowCX(creds)
        self.dffx =  DialogflowFunctions(creds)


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

        if mode == 'advanced':
            phrase_schema_master = pd.DataFrame(index=['training_phrase',
                'part', 'text', 'parameter_id'],
                columns=[0], 
                data=['int32', 'int32','string','string']).astype({0:'string'})
            param_schema_master = pd.DataFrame(index=['id',
                'entity_type'], 
                columns=[0], 
                data=['string','string']).astype({0:'string'})

        elif mode == 'basic':
            train_phrases = train_phrases[['text']]
            phrase_schema_master = pd.DataFrame(index=['text'], columns=[0], data=['string']).astype({0:'string'})
        else:
            raise ValueError('mode must be basic or advanced')

        phrase_schema_user = train_phrases.dtypes.to_frame().astype({0:'string'})
        param_schema_user = params.dtypes.to_frame().astype({0:'string'})

        if (phrase_schema_user.equals(phrase_schema_master))==False:
            raise ValueError('training phrase schema must be {} for {} mode'.format(tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql'), mode))
        if mode == 'advanced': 
            if (param_schema_user.equals(param_schema_master))==False and len(params)>0:
                raise ValueError('parameter schema must be {}'.format(tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql')))

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
        if mode == 'advanced':
            phrase_schema_master = pd.DataFrame(index=['display_name', 'training_phrase','part','text','parameter_id'], columns=[0], data=['string','int32', 'int32','string','string']).astype({0:'string'})
            param_schema_master = pd.DataFrame(index=['display_name', 'id', 'entity_type'], columns=[0], data=['string','string','string']).astype({0:'string'})

        elif mode == 'basic':
            train_phrases_df = train_phrases_df[['display_name', 'text']]
            phrase_schema_master = pd.DataFrame(index=['display_name','text'], columns=[0], data=['string','string']).astype({0:'string'})
        else:
            raise ValueError('mode must be basic or advanced')

        # TODO - check if user provided DF is in the right shape
        phrase_schema_user = train_phrases_df.dtypes.to_frame().astype({0:'string'})
        param_schema_user = params_df.dtypes.to_frame().astype({0:'string'})

        if (phrase_schema_user.equals(phrase_schema_master))==False:
            logging.error('training phrase schema must be\n {} \n'.format(
                tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql')))
            logging.error('got schema \n {}'.format(
                tabulate(phrase_schema_user.transpose(), headers='keys', tablefmt='psql')))
            logging.error('df.head \n%s', train_phrases_df.head() )
            # raise ValueError('wrong schema format \n%s' % phrase_schema_user)

        if mode =='advanced':
            if (param_schema_user.equals(param_schema_master))==False and len(params_df)>0:
                raise ValueError('parameter schema must be {}'.format(tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql')))

        logging.info('updating agent_id %s', agent_id)

        intents_map = self.dffx.get_intents_map(agent_id=agent_id, reverse=True)
        intent_names = list(set(train_phrases_df['display_name']))


        new_intents = {}
        for intent_name in intent_names:
            tps = train_phrases_df.copy()[train_phrases_df['display_name']==intent_name].drop(columns='display_name')
            params = pd.DataFrame()
            if mode == 'advanced':
                params = params_df.copy()[params_df['display_name']==intent_name].drop(columns='display_name')

            if not intent_name in new_intents:
                logging.error('FAIL to update - intent not found: [%s]', intent_name)
                continue

            new_intents[intent_name] = new_intent
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
