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
import pandas as pd
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import flows
from dfcx_scrapi.core import intents
from dfcx_scrapi.core import pages
from dfcx_scrapi.core import webhooks
from dfcx_scrapi.core import scrapi_base


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

        self._get_agent_level_data_only = False

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

    @scrapi_base.api_call_counter_decorator
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

    @scrapi_base.api_call_counter_decorator
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

    @scrapi_base.api_call_counter_decorator
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

    @scrapi_base.api_call_counter_decorator
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

    @scrapi_base.api_call_counter_decorator
    def delete_transition_route_group(
        self, route_group_id: str = None,
        obj: types.TransitionRouteGroup = None, force: bool = False
    ):
        """Deletes the specified Route Group.

        Args:
          route_group_id: The formatted CX Route Group ID to delete.
          obj: (Optional) a CX Webhook object of types.TransitionRouteGroup
          force: (Optional) This field has no effect for transition route group
            that no page is using. If set to True, Dialogflow will remove
            the transition route group, as well as any transitions to the page.
        """
        if not route_group_id:
            route_group_id = self.route_group_id
        if obj:
            route_group_id = obj.name

        client_options = self._set_region(route_group_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            credentials=self.creds, client_options=client_options)
        req = types.DeleteTransitionRouteGroupRequest(
            name=route_group_id, force=force)
        client.delete_transition_route_group(request=req)


    def route_groups_to_dataframe(
        self, agent_id: str = None, rate_limit: float = 0.5
    ):
        """Extracts the Flow Transition Route Groups from a given Agent and
         returns key information about the Route Groups in a Pandas Dataframe

        DFCX Route Groups exist as an Agent level resource, however they can
        categorized by the Flow they are associated with. This method will
        extract all Flows for the given agent, then use the Flow IDs to
        extract all Route Groups per Flow. Once all Route Groups have been
        extracted, the method will convert the DFCX object to a Pandas
        Dataframe and return this to the user.

        Args:
          agent_id: the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
          rate_limit: Time in seconds to wait between each API call. Use this
            to control hitting Quota limits on your project.

        Returns:
          a Pandas Dataframe with columns: flow, route_group_name, target_page,
          intent, condition, webhook, webhook_tag, custom_payload,
          live_agent_handoff, conversation_success, play_audio,
          output_audio_text, fulfillment_message
        """
        if not agent_id:
            agent_id = self.agent_id

        flows_map = self.flows.get_flows_map(agent_id)
        intents_map = self.intents.get_intents_map(agent_id)
        webhooks_map = self.webhooks.get_webhooks_map(agent_id)
        all_pages_map = {}
        all_rgs = []

        if self._get_agent_level_data_only:
            all_rgs.extend(self.list_transition_route_groups(agent_id))
        else:
            for flow in flows_map:
                all_pages_map.update(self.pages.get_pages_map(flow))
                all_rgs.extend(self.list_transition_route_groups(flow))
                time.sleep(rate_limit)

        rows_list = []
        for route_group in all_rgs:
            if not self._get_agent_level_data_only:
                flow = "/".join(route_group.name.split("/")[0:8])
            for route in route_group.transition_routes:
                temp_dict = {}

                if not self._get_agent_level_data_only:
                    temp_dict.update({"flow": flows_map[flow]})
                temp_dict.update({"route_group_name": route_group.display_name})

                if route.target_page:
                    t_p = all_pages_map.get(route.target_page)
                    if not t_p:
                        t_p = str(route.target_page).rsplit("/", maxsplit=1)[-1]

                    temp_dict.update({"target_page": t_p})

                if route.intent:
                    temp_dict.update({"intent": intents_map[route.intent]})

                if route.condition:
                    temp_dict.update({"condition": route.condition})

                if route.trigger_fulfillment.webhook:
                    temp_dict.update(
                        {
                            "webhook": webhooks_map[
                                route.trigger_fulfillment.webhook
                            ]
                        }
                    )

                    temp_dict.update(
                        {"webhook_tag": route.trigger_fulfillment.tag}
                    )

                if route.trigger_fulfillment.messages:
                    for element in route.trigger_fulfillment.messages:
                        temp_dict = self._rg_temp_dict_update(
                            temp_dict, element
                        )

                rows_list.append(temp_dict)
        final_dataframe = pd.DataFrame(
            rows_list,
            columns=[
                "flow", "route_group_name", "target_page", "intent",
                "condition", "webhook", "webhook_tag", "custom_payload",
                "live_agent_handoff","conversation_success", "play_audio",
                "output_audio_text", "fulfillment_message"]
        )

        return final_dataframe

    def agent_route_groups_to_dataframe(
            self, agent_id: str = None, rate_limit: float = 0.5
    ):
        """Extracts the Transition Route Groups from a given Agent and
        returns key information about the Route Groups in a Pandas Dataframe

        This method will extract all Agent Level Route Groups and convert
        the DFCX object to a Pandas Dataframe and return this to the user.

        Args:
        agent_id: the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
        rate_limit: Time in seconds to wait between each API call. Use this
            to control hitting Quota limits on your project.

        Returns:
        a Pandas Dataframe with columns: route_group_name, target_page,
        intent, condition, webhook, webhook_tag, custom_payload,
        live_agent_handoff, conversation_success, play_audio,
        output_audio_text, fulfillment_message
        """
        self._get_agent_level_data_only = True
        final_dataframe = self.route_groups_to_dataframe(agent_id, rate_limit)
        self._get_agent_level_data_only = False
        return final_dataframe
