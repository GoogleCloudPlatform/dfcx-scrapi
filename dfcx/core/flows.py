import logging
import requests
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2

from typing import Dict, List
# from dfcx.dfcx import DialogflowCX

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
'https://www.googleapis.com/auth/dialogflow']

class Flows:
    def __init__(self, creds_path: str, flow_id: str=None):
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        self.creds.refresh(Request()) # used for REST API calls
        self.token = self.creds.token # used for REST API calls

        if flow_id:
            self.flow_id = flow_id
        
        
    def train_flow(self):
        """trains the specified flow.

        Args:
          flow_id: CX flow ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>/flows/<FLOW ID>
          
        Returns:
          response: A Long Running Operation (LRO) ID that can be used to
            check the status of the export using dfcx.get_lro()
        """


        request = types.flow.TrainFlowRequest()
        request.name  = self.flow_id
        client = services.flows.FlowsClient(
                    credentials=self.creds)
        response = client.train_flow(request)
        return response
