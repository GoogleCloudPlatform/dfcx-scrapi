import logging
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from typing import Dict, List

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
'https://www.googleapis.com/auth/dialogflow']

class SapiBase:
    '''Common base class for different SAPI objects'''

    def __init__(self, creds_path, agent_path):
        logging.info('create sapi_base \ncreds_path:%s \nagent_path: %s', creds_path, agent_path)
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


    def get_lro(self, lro: str) -> Dict[str,str]:
        """Used to retrieve the status of LROs for Dialogflow CX.

        Args:
          lro: The Long Running Operation(LRO) ID in the following format
              'projects/<project-name>/locations/<locat>/operations/<operation-uuid>'

        Returns:
          response: Response status and payload from LRO
              
        """

        location = lro.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'

        url = '{0}/{1}'.format(base_url, lro)
        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()