"""Flow Resource functions."""

# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Dict
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core.scrapi_base import ScrapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Flows(ScrapiBase):
    """Core Class for CX Flow Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        flow_id: str = None,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if flow_id:
            self.flow_id = flow_id

        self.agent_id = agent_id

    def get_flows_map(self, agent_id: str = None, reverse=False):
        """Exports Agent Flow Names and UUIDs into a user friendly dict.

        Args:
            - agent_id, the formatted CX Agent ID to use
            - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
            - flows_dict, Dictionary containing flow UUIDs as keys and
                flow.display_name as values
        """
        if not agent_id:
            agent_id = self.agent_id

        if reverse:
            flows_dict = {
                flow.display_name: flow.name
                for flow in self.list_flows(agent_id=agent_id)
            }

        else:
            flows_dict = {
                flow.name: flow.display_name
                for flow in self.list_flows(agent_id=agent_id)
            }

        return flows_dict

    def train_flow(self, flow_id: str = None):
        """trains the specified flow.

        Args:
          flow_id: CX flow ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>/
              flows/<FLOW ID>

        Returns:
          response: A Long Running Operation (LRO) ID that can be used to
            check the status of the export using
              dfcx_scrapi.core.operations->get_lro()
        """
        if not flow_id:
            flow_id = self.flow_id

        request = types.flow.TrainFlowRequest()
        request.name = flow_id

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options)

        response = client.train_flow(request)

        return response

    def list_flows(self, agent_id: str = None):
        """Get a List of all Flows in the current Agent.

        Args:
          agent_id, CX Agent ID string in the proper format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>

        Returns:
          flows, a List of Flow objects
        """
        if not agent_id:
            agent_id = self.agent_id

        request = types.flow.ListFlowsRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_flows(request)

        flows = []
        for page in response.pages:
            for flow in page.flows:
                flows.append(flow)

        return flows

    def get_flow(self, flow_id: str = None):
        """Get a single CX Flow object.

        Args:
          flow_id, CX Flow ID in the proper format

        Returns:
          response, a single CX Flow object"""
        if not flow_id:
            flow_id = self.flow_id

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_flow(name=flow_id)

        return response

    def update_flow(
        self, flow_id: str = None, obj: types.Flow = None, **kwargs
    ):
        """Update a single specific CX Flow object.

        Args:
          flow_id, CX Flow ID in the proper format
          obj, (Optional) a single CX Flow object of types.Flow

        Returns:
          response, a copy of the updated Flow object
        """

        if obj:
            flow = obj
            flow.name = flow_id
        else:
            if not flow_id:
                flow_id = self.flow_id
            flow = self.get_flow(flow_id)

        # set flow attributes to args
        for key, value in kwargs.items():
            setattr(flow, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.update_flow(flow=flow, update_mask=mask)

        return response

    def update_nlu_settings(self, flow_id, **kwargs):
        """updates flow to new NLU setting.
        Args:
            flow_id: flow id to update nlu settings for.
            model_type: (Optional) [0:unspecified, 1:MODEL_TYPE_STANDARD,
              2:Custom, 3:Advanced]
            classification_threshold: (Optional) threshold for the flow
            model_training_mode: (Optional) [0:unspecified, 1:automatic,
              2:'manual]
        """

        flow = self.get_flow(flow_id)
        current_settings = flow.nlu_settings
        for key, value in kwargs.items():
            setattr(current_settings, key, value)
        self.update_flow(flow_id=flow_id, nlu_settings=current_settings)

    def export_flow(
        self,
        flow_id: str,
        gcs_path: str,
        ref_flows: bool = True) -> Dict[str, str]:
        """Exports DFCX Flow(s) into GCS bucket.

        Args:
          flow_id, the formatted CX Flow ID to export
          gcs_path, The `Google Cloud Storage URI to export the flow to. The
            format of this URI must be ``gs://<bucket-name>/<object-name>``. If
            left unspecified, the serialized flow is returned inline.
          ref_flows, Whether to export flows referenced by the specified flow.

        Returns:
          lro.result, If successful the LRO result will return the Google Cloud
            Storage URI from the Export Flow request. Otherwise, it will return
            the corresponding error.
        """
        request = types.flow.ExportFlowRequest()
        request.name = flow_id
        request.include_referenced_flows = ref_flows

        if gcs_path:
            request.flow_uri = gcs_path

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.export_flow(request)

        return response.result()

    def import_flow(
        self,
        agent_id: str,
        gcs_path: str,
        import_option: str = "KEEP") -> Dict[str, str]:
        """Imports a DFCX Flow from GCS bucket to CX Agent.

        Args:
          agent_id, the CX Agent ID to import the flow into.
          gcs_path, The `Google Cloud Storage URI to import flow from. The
            format of this URI must be ``gs://<bucket-name>/<object-name>``.
          import_option, one of 'FALLBACK' or 'KEEP'. Defaults to 'KEEP'

        Returns:
          lro.result, If successful the LRO result will return the Flow ID of
            the newly imported Flow. Otherwise, it will return the
            corresponding error.
        """
        request = types.flow.ImportFlowRequest()
        request.parent = agent_id
        request.flow_uri = gcs_path
        request.import_option = import_option

        client_options = self._set_region(agent_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.import_flow(request)

        return response

    def delete_flow(self, flow_id: str = None, force: bool = False) -> None:
        """Deletes a single CX Flow Object resources.

        Args:
          flow_id: flow to delete
          force: False means a flow will not be deleted if a route to the flow
            exists, True means the flow will be deleted and all
        """
        if not flow_id:
            flow_id = self.flow_id

        request = types.DeleteFlowRequest()
        request.name = flow_id
        request.force = force

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )

        client.delete_flow(request)
