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





def authorize(creds_info, creds_type: str = 'path', scope=False):
    SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
                    'https://www.googleapis.com/auth/dialogflow']
    if scope:
        SCOPES = SCOPES + scope
    
    if creds_type == 'path':
        creds = service_account.Credentials.from_service_account_file(
            creds_info, scopes=SCOPES)
    elif creds_type == 'json':
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=SCOPES)
    else:
        raise ValueError('creds_type must be of [path, json]')
    creds.refresh(Request())
    token = creds.token 
    return creds, token


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



def pbuf_to_dict(pbuf):
    '''extractor of json from a protobuf'''
    blobstr = json_format.MessageToJson(pbuf) # i think this returns JSON as a string
    blob = json.loads(blobstr)
    return blob



def response_to_json(response):
    '''response objects have a magical _pb field attached'''
    # return SapiBase.pbuf_to_dict(response._pb)
    return SapiBase.pbuf_to_dict(response._pb)



def response_to_dict(response):
    '''response objects have a magical _pb field attached'''
    return SapiBase.pbuf_to_dict(response._pb)



def extract_payload(msg):
    '''convert to json so we can get at the object'''
    blob = SapiBase.response_to_dict(msg)
    return blob.get('payload') # deref for nesting



