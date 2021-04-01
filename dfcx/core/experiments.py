'''wrapper for Experiments'''

import logging
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from typing import Dict, List
# from dfcx.dfcx import DialogflowCX

from google.cloud.dialogflowcx_v3.services.experiments import ExperimentsClient
import google.cloud.dialogflowcx_v3beta1.types as types

from .sapi_base import SapiBase


# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
'https://www.googleapis.com/auth/dialogflow']

class SapiExperiments(SapiBase):
    '''Wrapper for working with Experiments'''

    def __init__(self, creds_path, agent_path=None):
        '''constructor'''
        super().__init__(creds_path, agent_path)
        logging.info('created %s', self.agent_path)


    def list(self, environment_id=None):
        '''list out experiments'''
        ex_client = ExperimentsClient(
            credentials=self.creds,
            client_options=self.client_options)
        
        # projects/verizon-custom-ccai-external/locations/global/agents/f727a856-bbba-45ce-9d91-4e437cd448ba/environments/ec44091d-0171-4729-9c8b-5eca321dc8bc
        environment_path = f'{self.agent_path}/environments/{environment_id}'
        logging.info('environment_path %s', environment_path)
        request = types.ListExperimentsRequest(
            parent=environment_path
        )
        result = ex_client.list_experiments(request=request)
        logging.log('list %s', result)
