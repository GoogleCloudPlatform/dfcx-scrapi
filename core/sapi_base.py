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
'''
base for other SAPI classes
'''

import logging
import json
import requests

from google.oauth2 import service_account
from google.auth.transport.requests import Request

from google.protobuf import json_format  # type: ignore

from typing import Dict, List

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
'https://www.googleapis.com/auth/dialogflow']

class SapiBase:
    '''Common base class for different SAPI objects'''

    def __init__(self, creds_path, agent_path):
        logging.info('create sapi_base \ncreds_path:%s \nagent_path: %s', creds_path, agent_path)
        # TODO - decide on creds or creds_path 
        # currently a lot of other classes still expect the raw path
        # and then handle creds internally eg Intents
        self.creds_path = creds_path
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES )
        self.agent_path = agent_path
        self.creds.refresh(Request()) # used for REST API calls
        self.token = self.creds.token # used for REST API calls
        self.client_options = self._set_region(agent_path)


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
            return None # explicit None return when not required


    @staticmethod
    def pbuf_to_dict(pbuf):
        '''extractor of json from a protobuf'''
        blobstr = json_format.MessageToJson(pbuf) # i think this returns JSON as a string
        blob = json.loads(blobstr)
        return blob


    @staticmethod
    def response_to_json(response):
        '''response objects have a magical _pb field attached'''
        # return SapiBase.pbuf_to_dict(response._pb)
        return SapiBase.pbuf_to_dict(response._pb)


    @staticmethod
    def response_to_dict(response):
        '''response objects have a magical _pb field attached'''
        return SapiBase.pbuf_to_dict(response._pb)


    @staticmethod
    def extract_payload(msg):
        '''convert to json so we can get at the object'''
        blob = SapiBase.response_to_dict(msg)
        return blob.get('payload') # deref for nesting



    # def get_lro(self, lro: str) -> Dict[str,str]:
    #     """Used to retrieve the status of LROs for Dialogflow CX.

    #     Args:
    #       lro: The Long Running Operation(LRO) ID in the following format
    #           'projects/<project-name>/locations/<locat>/operations/<operation-uuid>'

    #     Returns:
    #       response: Response status and payload from LRO

    #     """

    #     location = lro.split('/')[3]
    #     if location != 'global':
    #         base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
    #             location)
    #     else:
    #         base_url = 'https://dialogflow.googleapis.com/v3beta1'

    #     url = '{0}/{1}'.format(base_url, lro)
    #     headers = {"Authorization": "Bearer {}".format(self.token)}

    #     # Make REST call
    #     results = requests.get(url, headers=headers)
    #     results.raise_for_status()

    #     return results.json()