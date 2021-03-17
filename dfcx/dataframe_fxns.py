import json
import logging
import os
import google.cloud.dialogflowcx_v3beta1.types as types
from tabulate import tabulate
from .dfcx import *
from .dfcx_functions import *

from typing import List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class Dataframe_fxns:
    def __init__(self, creds: str):
        self.dfcx =  DialogflowCX(creds)
        self.dffx =  DialogflowFunctions(creds)

        

    def update_intent_from_dataframe(self,intent_id, train_phrases, params=pd.DataFrame(), mode='basic'):
        """update an existing intents training phrases and parameters

        Args:
            intent_id: name parameter of the intent to update
            train_phrases: dataframe of training phrases in advanced have training_phrase and parts column to track the build
            params(optional): dataframe of parameters
            mode: basic - build assuming one row is one training phrase no entities, advance - build keeping track of training phrases and parts with the training_phrase and parts column. 

        Returns:
            intentPb: the new intents protobuf object
        """

        if mode == 'advanced':
            tpSchema = pd.DataFrame(index=['training_phrase','part','text','parameter_id'], columns=[0], data=['int32', 'int32','string','string']).astype({0:'string'})
            pSchema = pd.DataFrame(index=['id','entity_type'], columns=[0], data=['string','string']).astype({0:'string'})

        elif mode == 'basic':
            train_phrases = train_phrases[['text']]
            tpSchema = pd.DataFrame(index=['text'], columns=[0], data=['string']).astype({0:'string'})
        else:
            raise ValueError('mode must be basic or advanced')

        myTpSchema = train_phrases.dtypes.to_frame().astype({0:'string'})
        myPSchema = params.dtypes.to_frame().astype({0:'string'})

        if (myTpSchema.equals(tpSchema))==False:
            raise ValueError('training phrase schema must be {} for {} mode'.format(tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql'), mode))
        if mode == 'advanced': 
            if (myPSchema.equals(pSchema))==False and len(params)>0:
                raise ValueError('parameter schema must be {}'.format(tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))

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
                for index, row in tpParts.iterrows():
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
            for index, row in params.iterrows():
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
        intentPb = types.Intent.from_json(jsonIntent)
        return intentPb
    
    
    def bulk_update_intent_from_dataframe(self,agent_id, blk_train_phrases, blk_params=pd.DataFrame(), mode='basic', update=False):
        """update an existing intents training phrases and parameters

        Args:
            agent_id: name parameter of the agent to update
            blk_train_phrases: dataframe of bulk training phrases in advanced mode have training_phrase and parts column to track the build
            blk_params(optional): dataframe of bulk parameters
            mode: basic - build assuming one row is one training phrase no entities, advance - build keeping track of training phrases and parts with the training_phrase and parts column. 
            update: True to update the intents in the agent

        Returns:
            newIntents: dictionary with intent display names as keys and the new intent protobufs as values. 
        """
        if mode == 'advanced':
            tpSchema = pd.DataFrame(index=['display_name', 'training_phrase','part','text','parameter_id'], columns=[0], data=['string','int32', 'int32','string','string']).astype({0:'string'})
            pSchema = pd.DataFrame(index=['display_name','id','entity_type'], columns=[0], data=['string','string','string']).astype({0:'string'})

        elif mode == 'basic':
            blk_train_phrases = blk_train_phrases[['display_name','text']]
            tpSchema = pd.DataFrame(index=['display_name','text'], columns=[0], data=['string','string']).astype({0:'string'})
            
        else:
            raise ValueError('mode must be basic or advanced')

        myTpSchema = blk_train_phrases.dtypes.to_frame().astype({0:'string'})
        myPSchema = blk_params.dtypes.to_frame().astype({0:'string'})


        if (myTpSchema.equals(tpSchema))==False:
            raise ValueError('training phrase schema must be {} for {} mode'.format(tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql'), mode))
        if mode =='advanced':
            if (myPSchema.equals(pSchema))==False and len(blk_params)>0:
                raise ValueError('parameter schema must be {}'.format(tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))


        intentsMap = self.dffx.get_intents_map(agent_id=agent_id, reverse=True)
        blkIntents = list(set(blk_train_phrases['display_name']))

        newIntents = {}
        for instance in blkIntents:
            tps = blk_train_phrases.copy()[blk_train_phrases['display_name']==instance].drop(columns='display_name')
            params = pd.DataFrame()
            if mode == 'advanced':
                params = blk_params.copy()[blk_params['display_name']==instance].drop(columns='display_name')
            newIntent = self.update_intent_from_dataframe(intent_id=intentsMap[instance], train_phrases=tps, params=params, mode=mode)
            newIntents[instance] = newIntent
            if update:
                self.dfcx.update_intent(intent_id=newIntent.name, obj=newIntent)



        return newIntents