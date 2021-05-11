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
import logging
import requests
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2

from typing import Dict, List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/dialogflow']


class Flows:
    def __init__(self, creds_path: str, flow_id: str = None):
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        self.creds.refresh(Request())  # used for REST API calls
        self.token = self.creds.token  # used for REST API calls
        self.agent_id = None

        if flow_id:
            self.flow_id = flow_id

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

    def get_flows_map(self, agent_id, reverse=False):
        """ Exports Agent Flow Names and UUIDs into a user friendly dict.

        Args:
            - agent_id, the formatted CX Agent ID to use
            - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
            - flows_map, Dictionary containing flow UUIDs as keys and
                flow.display_name as values
        """

        if reverse:
            flows_dict = {flow.display_name: flow.name
                          for flow in self.list_flows(agent_id=agent_id)}

        else:
            flows_dict = {flow.name: flow.display_name
                          for flow in self.list_flows(agent_id=agent_id)}

        return flows_dict

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
        request.name = self.flow_id
        client = services.flows.FlowsClient(
            credentials=self.creds)
        response = client.train_flow(request)
        return response

    def list_flows(self, agent_id=None):
        agent_id = agent_id or self.agent_id  # default value
        request = types.flow.ListFlowsRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.flows.FlowsClient(
            credentials=self.creds,
            client_options=client_options)
        response = client.list_flows(request)

        flows = []
        for page in response.pages:
            for flow in page.flows:
                flows.append(flow)

        return flows

    def get_flow(self, flow_id):
        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(credentials=self.creds,
                                            client_options=client_options)
        response = client.get_flow(name=flow_id)

        return response

    def update_flow(self, flow_id, obj=None, **kwargs):
        if obj:
            flow = obj
            flow.name = flow_id
        else:
            flow = self.get_flow(flow_id)

        # set flow attributes to args
        for key, value in kwargs.items():
            setattr(flow, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(credentials=self.creds,
                                            client_options=client_options)
        response = client.update_flow(flow=flow, update_mask=mask)

        return response

    def update_nlu_settings(self, flow_id, **kwargs):
        """updates flow to new NLU setting.
        Args:
            flow_id: flow id to update nlu settings for.
            model_type: (Optional) [0:unspecified, 1:MODEL_TYPE_STANDARD, 2:Custom, 3:Advanced]
            classification_threshold: (Optional) threshold for the flow
            model_training_mode: (Optional) [0:unspecified, 1:automatic, 2:'manual]
        """

        flow = self.get_flow(flow_id)
        currentSettings = flow.nlu_settings
        for key, value in kwargs.items():
            setattr(currentSettings, key, value)
        self.update_flow(flow_id=flow_id,
                         nlu_settings=currentSettings)

    def export_flow(self,
                    flow_id: str,
                    gcs_path: str,
                    data_format: str = 'BLOB',
                    ref_flows: bool = True) -> Dict[str,
                                                    str]:
        """ Exports DFCX Flow(s) into GCS bucket.

        Args:
          flow_id, the formatted CX Flow ID to export
          gcs_path, the full GCS Bucket and File name path
          data_format, (Optional) One of 'BLOB' or 'JSON'. Defaults to 'BLOB'.
          ref_flows, (Optional) Bool to include referenced flows connected to primary flow

        Returns:
          lro, Dict with value containing a Long Running Operation UUID that can be
              used to retrieve status of LRO from dfcx.get_lro
        """

        location = flow_id.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'
        url = '{0}/{1}:export'.format(base_url, flow_id)

        body = {
            'flow_uri': '{}'.format(gcs_path),
            'data_format': data_format,
            'include_referenced_flows': ref_flows}

        headers = {
            'Authorization': 'Bearer {}'.format(self.token),
            'Content-Type': 'application/json; charset=utf-8'}

        # Make REST call
        r = requests.post(url, json=body, headers=headers)
        r.raise_for_status()

        lro = r.json()

        return lro

    def import_flow(self, destination_agent_id: str, gcs_path: str,
                    import_option: str = 'FALLBACK') -> Dict[str, str]:
        """ Imports a DFCX Flow from GCS bucket to CX Agent.

        Args:
          agent_id, the DFCX formatted Agent ID
          gcs_path, the full GCS Bucket and File name path
          import_option, one of 'FALLBACK' or 'KEEP'. Defaults to 'FALLBACK'

        Returns:
          lro, Dict with value containing a Long Running Operation UUID that can be
              used to retrieve status of LRO from dfcx.get_lro
        """

        location = destination_agent_id.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'
        url = '{0}/{1}/flows:import'.format(base_url, destination_agent_id)

        body = {
            'flow_uri': '{}'.format(gcs_path),
            'import_option': '{}'.format(import_option)}

        headers = {
            'Authorization': 'Bearer {}'.format(self.token),
            'Content-Type': 'application/json; charset=utf-8'}

        # Make REST call
        r = requests.post(url, json=body, headers=headers)
        r.raise_for_status()

        lro = r.json()

        return lro

    def delete_flow(self, flow_id: str, force: bool = False):
        """
        Args:
          flow_id: flow to delete
          force: False means a flow will not be deleted if a route to the flow exists, True means the flow will be deleted and all
        """
        request = types.DeleteFlowRequest()
        request.name = flow_id
        request.force = force
        client = services.flows.FlowsClient()
        client.delete_flow(request)
