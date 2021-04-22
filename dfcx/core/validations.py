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

class Validations:
    def __init__(self, creds_path: str, agent_id: str=None):
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        self.creds.refresh(Request()) # used for REST API calls
        self.token = self.creds.token # used for REST API calls

        if agent_id:
            self.agent_id = agent_id
            self.client_options = self._set_region(agent_id)


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
        
    def run_validation_result(self, agent_id: str) -> Dict:
        """Initiates the Validation of the CX Agent or Flow.

        This function will start the Validation feature for the given Agent
        and then return the results as a Dict.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>

        Returns:
          results: Dictionary of Validation results for the entire Agent
            or for the specified Flow.
        """
        location = agent_id.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'

        url = '{0}/{1}/validationResult'.format(base_url, agent_id)
        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()

    
    def get_validation_result(
            self,
            agent_id: str,
            flow_id: str = None) -> Dict:
        """Extract Validation Results from CX Validation feature.

        This function will get the LATEST validation result run for the given
        CX Agent or CX Flow. If there has been no validation run on the Agent
        or Flow, no result will be returned. Use `dfcx.validate` function to
        run Validation on an Agent/Flow.

        Passing in the Agent ID will provide ALL validation results for
        ALL flows.
        Passing in the Flow ID will provide validation results for only
        that Flow ID.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          flow_id: (Optional) CX Flow ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>/flows/<FLOW ID>

        Returns:
          results: Dictionary of Validation results for the entire Agent
            or for the specified Flow.
        """

        if flow_id:
            location = flow_id.split('/')[3]
            if location != 'global':
                base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                    location)
            else:
                base_url = 'https://dialogflow.googleapis.com/v3beta1'

            url = '{0}/{1}/validationResult'.format(base_url, flow_id)
        else:
            location = agent_id.split('/')[3]
            if location != 'global':
                base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                    location)
            else:
                base_url = 'https://dialogflow.googleapis.com/v3beta1'

            url = '{0}/{1}/validationResult'.format(base_url, agent_id)

        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()

