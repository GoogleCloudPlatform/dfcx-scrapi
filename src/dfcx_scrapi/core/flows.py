"""Flow Resource functions."""

# Copyright 2023 Google LLC
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
import time
from typing import Dict, List
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import pages

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class Flows(scrapi_base.ScrapiBase):
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
        self.pages = pages.Pages(creds=self.creds)

    # TODO: Migrate to Flow Builder class when ready
    @staticmethod
    def _build_nlu_settings(
        model_type: str = "STANDARD",
        classification_threshold: float = 0.3,
        model_training_mode: str = "MANUAL",
    ):
        """Builds the NLU Settings object to be used with Flow objects.

        Args:
          model_type: ONEOF `STANDARD`, `ADVANCED`, `CUSTOM`. Defaults to
            `STANDARD`.
          classification_threshold: To filter out false positive results and
            still get variety in matched natural language inputs for your
            agent, you can tune the machine learning classification threshold.
            If the returned score value is less than the threshold value, then
            a no-match event will be triggered. The score values range from 0.0
            (completely uncertain) to 1.0 (completely certain). If set to 0.0,
            the default of 0.3 is used.
          model_training_mode: ONEOF `AUTOMATIC`, `MANUAL`. Defaults to
            `MANUAL`
        """
        model_type_map = {"STANDARD": 1, "CUSTOM": 2, "ADVANCED": 3}

        model_training_map = {"AUTOMATIC": 1, "MANUAL": 2}

        nlu_settings = types.NluSettings()
        nlu_settings.classification_threshold = classification_threshold

        if model_type in model_type_map:
            nlu_settings.model_type = model_type_map[model_type]
        else:
            raise KeyError(
                f"`{model_type}` is invalid. `model_type` must be "
                "one of `STANDARD`, `ADVANCED`, `CUSTOM`."
            )

        if model_training_mode in model_training_map:
            nlu_settings.model_training_mode = model_training_map[
                model_training_mode
            ]
        else:
            raise KeyError(
                f"`{model_training_mode}` is invalid. "
                "`model_training_mode` must be one of `AUTOMATIC`, `MANUAL`."
            )

        return nlu_settings

    def get_flows_map(self, agent_id: str = None, reverse=False):
        """Exports Agent Flow Names and UUIDs into a user friendly dict.

        Args:
          agent_id: the formatted CX Agent ID to use
          reverse: (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          Dictionary containing flow UUIDs as keys and display names as values
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

    def get_flow_page_map(
            self, agent_id: str, rate_limit: float = 1.0
            ) -> Dict[str, Dict[str, str]]:
        """Exports a user friendly dict containing Flows, Pages, and IDs
        This method builds on top of `get_flows_map` and builds out a nested
        dictionary containing all of the Page Display Names and UUIDs contained
        within each Flow. Output Format:
          {
            <FLOW_DISPLAY_NAME>: {
                'id': <FLOW_UUID>
                'pages': { <PAGE_DISPLAY_NAME> : <PAGE_UUID> }
            }
          }

        Args:
          agent_id: the formatted CX Agent ID to use

        Returns:
          Dictionary containing Flow Names/UUIDs and Page Names/UUIDs
        """
        flow_page_map = {}

        flows_map = self.get_flows_map(agent_id, reverse=True)

        for flow in flows_map:
            pages_map = self.pages.get_pages_map(
                flows_map[flow], reverse=True)
            flow_page_map[flow] = {"id": flows_map[flow], "pages": pages_map}
            time.sleep(rate_limit)

        return flow_page_map

    @scrapi_base.api_call_counter_decorator
    def train_flow(self, flow_id: str) -> str:
        """Trains the specified flow.

        Args:
          flow_id: CX flow ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>/
              flows/<FLOW ID>

        Returns:
          A Long Running Operation (LRO) ID that can be used to
            check the status of the export using
              dfcx_scrapi.core.operations->get_lro()
        """

        request = types.flow.TrainFlowRequest()
        request.name = flow_id

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.train_flow(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def list_flows(self, agent_id: str = None) -> List[types.Flow]:
        """Get a List of all Flows in the current Agent.

        Args:
          agent_id: CX Agent ID string in the proper format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>

        Returns:
          List of Flow objects
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

    def get_flow_by_display_name(
        self, display_name: str, agent_id: str
    ) -> types.Flow:
        """Get a single CX Flow object based on its display name.

        Args:
          display_name: The display name of the desired Flow.
          agent_id: CX Agent ID in which the flow exists.

        Returns:
          A single CX Flow object
        """

        flows_map = self.get_flows_map(agent_id=agent_id, reverse=True)

        if display_name in flows_map:
            flow_id = flows_map[display_name]
        else:
            raise ValueError(
                f'Flow "{display_name}" '
                f"does not exist in the specified agent."
            )

        flow = self.get_flow(flow_id=flow_id)

        return flow

    @scrapi_base.api_call_counter_decorator
    def get_flow(self, flow_id: str) -> types.Flow:
        """Get a single CX Flow object.

        Args:
          flow_id: CX Flow ID in the proper format

        Returns:
          A single CX Flow object
        """

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_flow(name=flow_id)

        return response

    @scrapi_base.api_call_counter_decorator
    def create_flow(
        self,
        agent_id: str,
        display_name: str = None,
        language_code: str = "en",
        obj: types.Flow = None,
        **kwargs,
    ):
        """Create a Dialogflow CX Flow with given display name.

        If the user provides an existing Flow object, a new CX Flow will be
        created based on this object and any other input/kwargs will be
        discarded.

        Args:
          agent_id: DFCX Agent id where the Flow will be created
          display_name: Human readable display name for the CX Flow
          obj: (Optional) Flow object to create in proto format

        Returns:
          The newly created CX Flow resource object.
        """
        request = types.flow.CreateFlowRequest()
        request.parent = agent_id
        request.language_code = language_code

        if obj:
            flow_obj = obj
            request.flow = flow_obj

        else:
            flow_obj = types.Flow()
            flow_obj.display_name = display_name

            # set optional args as agent attributes
            for key, value in kwargs.items():
                setattr(flow_obj, key, value)

            request.flow = flow_obj

        client_options = self._set_region(agent_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.create_flow(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def update_flow(
        self, flow_id: str, obj: types.Flow = None, **kwargs
    ) -> types.Flow:
        """Update a single specific CX Flow object.

        Args:
          flow_id: CX Flow ID in the proper format
          obj: (Optional) a single CX Flow object of types.Flow

        Returns:
          A copy of the updated Flow object
        """

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
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.update_flow(flow=flow, update_mask=mask)

        return response

    def update_nlu_settings(self, flow_id: str, **kwargs):
        """Updates flow to new NLU setting.

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

    @scrapi_base.api_call_counter_decorator
    def export_flow(
        self, flow_id: str, gcs_path: str, ref_flows: bool = True
    ) -> Dict[str, str]:
        """Exports DFCX Flow(s) into GCS bucket.

        Args:
          flow_id: the formatted CX Flow ID to export
          gcs_path: The `Google Cloud Storage URI to export the flow to. The
            format of this URI must be ``gs://<bucket-name>/<object-name>``. If
            left unspecified, the serialized flow is returned inline.
          ref_flows: Whether to export flows referenced by the specified flow.

        Returns:
          A Long Running Operation result. If successful the LRO result will
            return the Google Cloud Storage URI from the Export Flow request.
            Otherwise, it will return the corresponding error.
        """
        request = types.flow.ExportFlowRequest()
        request.name = flow_id
        request.include_referenced_flows = ref_flows
        request.flow_uri = gcs_path

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.export_flow(request)

        return response.result()

    @scrapi_base.api_call_counter_decorator
    def export_flow_inline(self, flow_id: str, ref_flows: bool = True) -> bytes:
        """Export a Flow, returning uncompressed raw byte content for flow.

        Args:
          flow_id: the formatted CX Flow ID to export
          ref_flows: Whether to export flows referenced by the specified flow.

        Returns:
          Bytes representing the content of the flow.
        """
        request = types.flow.ExportFlowRequest()
        request.name = flow_id
        request.include_referenced_flows = ref_flows

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.export_flow(request)

        return (response.result()).flow_content

    @scrapi_base.api_call_counter_decorator
    def import_flow(
        self,
        agent_id: str,
        gcs_path: str = None,
        flow_content: bytes = None,
        import_option: str = "KEEP",
    ) -> Dict[str, str]:
        """Imports a DFCX Flow to CX Agent. Flow can be imported from a
        GCS bucket or from raw bytes.

        Args:
          agent_id: the CX Agent ID to import the flow into.
          gcs_path: the `Google Cloud Storage URI to import flow from.
            the format of this URI must be ``gs://<bucket-name>/<object-name>``.
          flow_content: uncompressed raw byte content for flow.
          import_option: one of 'FALLBACK' or 'KEEP'. Defaults to 'KEEP'

        Returns:
          A Long Running Operation result. If successful the LRO result will
            return the Flow ID of the newly imported Flow.
            Otherwise, it will return the corresponding error.
        """

        if gcs_path and flow_content:
            raise ValueError(
                "gcs_path or flow_content required (But not both!)."
            )

        if not gcs_path and not flow_content:
            raise ValueError(
                "gcs_path or flow_content required (But not both!)."
            )

        request = types.flow.ImportFlowRequest()
        request.parent = agent_id
        request.flow_uri = gcs_path
        request.flow_content = flow_content
        request.import_option = import_option

        client_options = self._set_region(agent_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.import_flow(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_flow(
        self, flow_id: str = None, obj: types.Flow = None, force: bool = False
    ):
        """Deletes a single CX Flow Object resource.

        Args:
          flow_id: The formatted CX Flow ID to delete.
          obj: (Optional) a CX Flow object of types.Flow
          force: (Optional) False means a flow will not be deleted if a route
            to the flow exists, True means the flow will be deleted as well as
            all the transition routes leading to the flow.
        """
        if not flow_id:
            flow_id = self.flow_id

        if obj:
            flow_id = obj.name

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(
            credentials=self.creds, client_options=client_options)
        req = types.DeleteFlowRequest(name=flow_id, force=force)
        client.delete_flow(request=req)
