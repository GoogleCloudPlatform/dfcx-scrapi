"""
Copyright 2021 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from collections import defaultdict
import logging
import numpy as np
import pandas as pd

import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from .sapi_base import authorize

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/dialogflow']


class Intents:
    '''Class to deal with intents

    Args:
    creds_path: file path to credentials
    intent_id: global intent id to work with'''
    def __init__(self, creds_info, creds_type: str = 'path', intent_id: str = None):
        self.creds, self.token = authorize(creds_info, creds_type)

        if intent_id:
            self.intent_id = intent_id
            self.client_options = self._set_region(self.intent_id)

    @staticmethod
    def _set_region(item_id):
        """different regions have different API endpoints

        Args:
            item_id: agent/flow/page - any type of long path id like
                `projects/<GCP PROJECT ID>/locations/<LOCATION ID>

        Returns:
            client_options: use when instantiating other library client objects
        """
        try:
            location = item_id.split('/')[3]
        except IndexError as err:
            logging.error('IndexError - path too short? %s', item_id)
            raise err

        if location != 'global':
            api_endpoint = '{}-dialogflow.googleapis.com:443'.format(location)
            client_options = {'api_endpoint': api_endpoint}
            return client_options

        else:
            return None  # explicit None return when not required

    @staticmethod
    def intent_proto_to_dataframe(obj, mode='basic'):
        """ intents to dataframe

        Args:
          obj, intent protobuf object
          mode: (Optional) basic returns display name and training phrase as plain text.
          Advanced returns training phrase and parameters df broken out by parts.
        """
        if mode == 'basic':
            intent_dict = defaultdict(list)
            if 'training_phrases' in obj:
                for train_phrase in obj.training_phrases:
                    item_list = []
                    if len(train_phrase.parts) > 1:
                        for item in train_phrase.parts:
                            item_list.append(item.text)
                        intent_dict[obj.display_name].append(''.join(item_list))
                    else:
                        intent_dict[obj.display_name].append(
                            train_phrase.parts[0].text)
            else:
                intent_dict[obj.display_name].append('')

            data_frame = pd.DataFrame.from_dict(intent_dict, orient='index').transpose()
            data_frame = data_frame.stack().to_frame().reset_index(
                level=1)
            data_frame = data_frame.rename(
                columns={
                    'level_1': 'intent',
                    0: 'tp'}).reset_index(
                drop=True)
            data_frame = data_frame.sort_values(['intent', 'tp'])
            return data_frame


        elif mode =='advanced':

            train_phrases = obj.training_phrases
            params = obj.parameters
            if len(train_phrases)>0:
                tp_df = pd.DataFrame()
                tp_id = 0
                for train_phrase in train_phrases:
                    part_id = 0
                    for part in train_phrase.parts:
                        tp_df = tp_df.append(pd.DataFrame(columns=
                        ['display_name', 'name','tp_id', 'part_id',
                        'text', 'parameter_id', 'repeat_count', 'id'],
                                                          data = [[obj.display_name,
                                                          obj.name, tp_id,
                                                          part_id, part.text,
                                                          part.parameter_id,
                                                          train_phrase.repeat_count,
                                                          train_phrase.id]]))
                        part_id+=1
                    tp_id+=1


                phrases = tp_df.copy()
                phrase_lst = phrases.groupby(
                    ['tp_id'])['text'].apply(
                        lambda x: ''.join(x)).reset_index().rename(
                    columns={'text':'phrase'})

                phrases = pd.merge(phrases, phrase_lst, on=['tp_id'],how='outer')


                if len(params) > 0:
                    param_df = pd.DataFrame()
                    for param in params:
                        param_df = param_df.append(pd.DataFrame(
                            columns = ['display_name', 'id', 'entity_type'],
                                                               data=[[obj.display_name,
                                                               param.id, param.entity_type]]))
                    return {'phrases': phrases, 'parameters': param_df}

                else:
                    return {'phrases': phrases,
                    'parameters': pd.DataFrame(columns =
                    ['display_name', 'id', 'entity_type'])}

            else:
                return {'phrases': pd.DataFrame(columns=
                ['display_name', 'name','tp_id', 'part_id',
                 'text', 'parameter_id', 'repeat_count', 'id',
                  'phrase'],
                            data =
                            [[obj.display_name, obj.name,
                             np.nan, np.nan, np.nan, np.nan,
                              np.nan, np.nan, np.nan]]),
                        'parameters': pd.DataFrame(columns =
                        ['display_name', 'id', 'entity_type'])}



        else:
            raise ValueError('Mode types: [basic, advanced]')


    def _set_api_options(self, id_item):
        '''bundle API parameters'''
        client_options = self._set_region(id_item)
        return {
            'client_options': client_options,
            'credentials': self.creds}


    def get_intents_map(self, agent_id, reverse=False):
        """ Exports Agent Intent Names and UUIDs into a user friendly dict.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - intents_map, Dictionary containing Intent UUIDs as keys and
              intent.display_name as values
          """

        if reverse:
            intents_dict = {intent.display_name: intent.name
                            for intent in self.list_intents(agent_id)}

        else:
            intents_dict = {intent.name: intent.display_name
                            for intent in self.list_intents(agent_id)}

        return intents_dict

    def list_intents(self, agent_id):
        '''provide a list of intents

        Args:
          agent_id, the CX agent id to pull the intents from
        '''
        request = types.intent.ListIntentsRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.intents.IntentsClient(
            credentials=self.creds,
            client_options=client_options)
        response = client.list_intents(request)

        intents = []
        # pager through the response, not CX 'pages'
        for page in response.pages:
            for intent in page.intents:
                intents.append(intent)

        return intents

    def get_intent(self, intent_id):
        client_options = self._set_region(intent_id)
        client = services.intents.IntentsClient(
            credentials=self.creds, client_options=client_options)
        response = client.get_intent(name=intent_id)

        return response

    def create_intent(self, agent_id, obj=None, **kwargs):
        # If intent_obj is given, set intent variable to it
        if obj:
            intent = obj
            intent.name = ''
        else:
            intent = types.intent.Intent()

        # Set optional arguments as intent attributes
        for key, value in kwargs.items():
            if key == 'training_phrases':
                assert isinstance(kwargs[key], list)
                training_phrases = []
                for arg in kwargs[key]:
                    if isinstance(arg, dict):
                        train_phrase = types.intent.Intent.TrainingPhrase()
                        parts = []
                        for part_i in arg['parts']:
                            if isinstance(part_i, dict):
                                part = types.intent.Intent.TrainingPhrase.Part()
                                part.text = part_i['text']
                                part.parameter_id = part_i.get('parameter_id')
                                parts.append(part)
                            else:
                                print("Wrong object in parts list")
                                return
                        train_phrase.parts = parts
                        train_phrase.repeat_count = arg.get("repeat_count")
                        training_phrases.append(train_phrase)
                    else:
                        print("Wrong object in training phrases list")
                        return
                setattr(intent, key, training_phrases)
            setattr(intent, key, value)

        client_options = self._set_region(agent_id)
        client = services.intents.IntentsClient(
            client_options=client_options, credentials=self.creds)
        response = client.create_intent(parent=agent_id, intent=intent)

        return response

    def update_intent(self, intent_id, obj=None):
        """ Updates a single Intent object based on provided args.
        Args:
          intent_id, the destination Intent ID. Must be formatted properly
              for Intent IDs in CX.
          obj, The CX Intent object in proper format. This can also
              be extracted by using the get_intent() method.
        """
        if obj:
            intent = obj
            intent.name = intent_id
        else:
            intent = self.get_intent(intent_id)

#         logging.info('dfcx_lib update intent %s', intent_id)

        client_options = self._set_region(intent_id)
        client = services.intents.IntentsClient(
            client_options=client_options,
            credentials=self.creds)
        response = client.update_intent(intent=intent)

        return response

    def delete_intent(self, intent_id, obj=None):
        """ deletes an intent

        Args:
          intent_id, intent to delete
        """
        if obj:
            intent_id = obj.name
        else:
            client_options = self._set_region(intent_id)
            client = services.intents.IntentsClient(
                client_options=client_options)
            client.delete_intent(name=intent_id)




    def bulk_intent_to_df(self, agent_id, mode='basic'):
        """ intents to dataframe

        Args:
          agent_id, agent to pull list of intents
          mode: (Optional) basic returns display name and training phrase as plain text.
          Advanced returns training phrase and parameters df broken out by parts.
        """
        intents = self.list_intents(agent_id)
        if mode == 'basic':
            main_frame = pd.DataFrame()
            for obj in intents:
                data_frame = self.intent_proto_to_dataframe(obj, mode=mode)
                main_frame = main_frame.append(data_frame)
            main_frame = main_frame.sort_values(['intent', 'tp'])
            return main_frame

        elif mode =='advanced':
            master_phrases = pd.DataFrame()
            master_parameters = pd.DataFrame()
            for obj in intents:
                output = self.intent_proto_to_dataframe(obj, mode='advanced')
                master_phrases = master_phrases.append(output['phrases'])
                master_parameters = master_parameters.append(output['parameters'])
            return {'phrases': master_phrases, 'parameters': master_parameters}

        else:
            raise ValueError('Mode types: [basic, advanced]')
        