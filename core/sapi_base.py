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


class SapiBase:
    global_scopes = ['https://www.googleapis.com/auth/cloud-platform',
                    'https://www.googleapis.com/auth/dialogflow']

    def __init__(self, creds_path: str = None,
                creds_dict: Dict = None,
                creds=None,
                scope=False):

        self.scopes = SapiBase.global_scopes
        if scope:
            self.scopes += scope

        if creds:
            self.creds = creds
        
        elif creds_path:
            self.creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=self.scopes)
        elif creds_dict:
            self.creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.scopes)
        else:
            raise ValueError('creds_type must be of [creds_path, creds_dict]')

        self.creds.refresh(Request())
        self.token = self.creds.token 
        

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
