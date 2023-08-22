"""CX Transition Route Group Resource functions."""

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
from typing import Dict

import numpy as np
import pandas as pd
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import flows
from dfcx_scrapi.core import intents
from dfcx_scrapi.core import pages
from dfcx_scrapi.core import webhooks
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.builders.transition_route_groups import TransitionRouteGroupBuilder


# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TransitionRouteGroups(scrapi_base.ScrapiBase):
    """Core Class for CX Transition Route Group functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        route_group_id: str = None,
        flow_id: str = None,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.flows = flows.Flows(creds=self.creds)
        self.intents = intents.Intents(creds=self.creds)
        self.pages = pages.Pages(creds=self.creds)
        self.webhooks = webhooks.Webhooks(creds=self.creds)

        if route_group_id:
            self.route_group_id = route_group_id
            self.client_options = self._set_region(route_group_id)

        if flow_id:
            self.flow_id = flow_id

        if agent_id:
            self.agent_id = agent_id

    def _rg_temp_dict_update(self, temp_dict, element):
        """Modify the temp dict and return to dataframe function."""
        element_dict = self.cx_object_to_dict(element)
        key = list(element_dict.keys())[0]

        if key == "payload":
            temp_dict.update({"custom_payload": element_dict[key]})
        elif key == "liveAgentHandoff":
            temp_dict.update(
                {"live_agent_handoff": element_dict[key]["metadata"]}
            )
        elif key == "conversationSuccess":
            temp_dict.update(
                {"conversation_success": element_dict[key]["metadata"]}
            )
        elif key == "playAudio":
            temp_dict.update({"play_audio": element_dict[key]["audioUri"]})
        elif key == "outputAudioText":
            temp_dict.update({"output_audio_text": element_dict[key]["text"]})
        elif key == "text":
            if len(element_dict[key]["text"]) == 1:
                temp_dict.update(
                    {"fulfillment_message": element_dict[key]["text"][0]}
                )
            else:
                temp_dict.update(
                    {"fulfillment_message": element_dict[key]["text"]}
                )
        else:
            temp_dict.update({key: element_dict[key]})

        return temp_dict

    def get_route_groups_map(self, flow_id: str = None, reverse=False):
        """Exports Agent Route Group UUIDs and Names into a user friendly dict.

        Args:
          flow_id: the formatted CX Agent Flow ID to use
          reverse: (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          Dictionary containing Route Group UUIDs as keys and display names
          as values. If Optional reverse=True, the output will return
          route group name:ID mapping instead of ID:route group name
        """
        if not flow_id:
            flow_id = self.flow_id

        if reverse:
            pages_dict = {
                page.display_name: page.name
                for page in self.list_transition_route_groups(flow_id)
            }

        else:
            pages_dict = {
                page.name: page.display_name
                for page in self.list_transition_route_groups(flow_id)
            }

        return pages_dict

    def list_transition_route_groups(self, flow_id: str = None):
        """Exports List of all Route Groups in the specified CX Flow ID.

        Args:
          flow_id: The formatted CX Flow ID to list the route groups from

        Returns:
          List of Route Group objects
        """
        if not flow_id:
            flow_id = self.flow_id

        request = (
            types.transition_route_group.ListTransitionRouteGroupsRequest()
        )
        request.parent = flow_id

        client_options = self._set_region(flow_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_transition_route_groups(request)

        cx_route_groups = []
        for page in response.pages:
            for cx_route_group in page.transition_route_groups:
                cx_route_groups.append(cx_route_group)

        return cx_route_groups

    def get_transition_route_group(self, route_group_id):
        """Get a single Transition Route Group object.

        Args:
          route_group_id: the formatted CX Route Group ID to retrieve.

        Returns:
          A single Route Group object
        """
        request = types.transition_route_group.GetTransitionRouteGroupRequest()
        request.name = route_group_id
        client_options = self._set_region(route_group_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_transition_route_group(request)

        return response

    def create_transition_route_group(
        self,
        flow_id: str = None,
        obj: types.TransitionRouteGroup = None,
        **kwargs,
    ):
        """Create a single Transition Route Group resource.

        Args:
          flow_id: the formatted CX Flow ID to create the route group in
          obj: (Optional) the Transition Route Group object of type
            types.TransitionRouteGroup that you want the new route group
            to be built from.

        Returns:
          A copy of the successfully created Route Group object
        """
        if not flow_id:
            flow_id = self.flow_id

        if obj:
            trg = obj
            trg.name = ""
        else:
            trg = types.transition_route_group.TransitionRouteGroup()

        for key, value in kwargs.items():
            setattr(trg, key, value)

        client_options = self._set_region(flow_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.create_transition_route_group(
            parent=flow_id, transition_route_group=trg
        )

        return response

    def update_transition_route_group(
        self,
        route_group_id: str = None,
        obj: types.TransitionRouteGroup = None,
        language_code: str = None,
        **kwargs,
    ):
        """Update a single Route Group resource.

        Args:
          route_group_id: the formatted CX Route Group ID to update.
          obj: (Optional) the Transition Route Group object of type
            types.TransitionRouteGroup that you want to update.
          language_code: (Optional) the language in which the agent should
            update the TransitionRouteGroup

        Returns:
          A copy of the successfully updated Route Group object
        """
        if obj:
            route_group = obj
            route_group.name = route_group_id
        else:
            route_group = self.get_transition_route_group(route_group_id)

        for key, value in kwargs.items():
            setattr(route_group, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(route_group_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            credentials=self.creds, client_options=client_options
        )

        request = (
            types.transition_route_group.UpdateTransitionRouteGroupRequest()
        )  # pylint: disable=C0301

        request.transition_route_group = route_group
        request.update_mask = mask

        if language_code:
            request.language_code = language_code

        response = client.update_transition_route_group(request)

        return response

    def route_groups_to_df(
        self,
        agent_id: str = None,
        mode: str = "basic",
        rate_limit: float = 0.5
    ) -> pd.DataFrame:
        """Extracts the Transition Route Groups from a given Agent and
         returns key information about the Route Groups in a Pandas Dataframe

        DFCX Route Groups exist as an Agent level resource, however they are
        categorized by the Flow they are associated with. This method will
        extract all Flows for the given agent, then use the Flow IDs to
        extract all Route Groups per Flow. Once all Route Groups have been
        extracted, the method will convert the DFCX object to a Pandas
        Dataframe and return this to the user.

        Args:
          agent_id (str):
            agent to pull transition routes from.
          mode (str):
            Whether to return 'basic' DataFrame or 'advanced' one.
            Refer to `data.dataframe_schemas.json` for schemas.
          rate_limit (float):
            Time in seconds to wait between each API call.
            Use this to control hitting Quota limits on your project.

        Returns:
          A pandas Dataframe
        """
        # Error checking for `mode`
        if mode not in ["basic", "advanced"]:
            raise ValueError("Mode types: [basic, advanced]")

        if not agent_id:
            agent_id = self.agent_id

        # Get all the TransitionRouteGroups
        flows_map = self.flows.get_flows_map(agent_id)
        all_rgs = []
        for flow in flows_map:
            all_rgs.extend(self.list_transition_route_groups(flow))
            time.sleep(rate_limit)

        main_df = pd.DataFrame()
        for obj in all_rgs:
            trgb = TransitionRouteGroupBuilder(obj)
            trgb_df = trgb.to_dataframe(mode=mode)
            main_df = pd.concat([main_df, trgb_df], ignore_index=True)

        if main_df.empty:
            return main_df

        # Get the maps
        intents_map = self.intents.get_intents_map(agent_id)
        all_pages_map = self._AllPagesCustomDict()
        for flow in flows_map:
            all_pages_map.update(self.pages.get_pages_map(flow))
            time.sleep(rate_limit)


        main_df["intent"] = main_df["intent"].map(intents_map)
        main_df["target_name"] = main_df["target_id"].map(all_pages_map)
        main_df["flow_name"] = main_df["flow_id"].map(flows_map)
        if mode == "advanced":
            webhooks_map = self.webhooks.get_webhooks_map(agent_id)
            main_df["webhook"] = main_df["webhook"].map(webhooks_map)

        return main_df
