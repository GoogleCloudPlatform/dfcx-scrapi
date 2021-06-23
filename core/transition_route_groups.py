# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
import pandas as pd
import requests
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2

from dfcx_sapi.core.flows import Flows
from dfcx_sapi.core.intents import Intents
from dfcx_sapi.core.sapi_base import SapiBase
from dfcx_sapi.core.webhooks import Webhooks
from typing import Dict, List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class TransitionRouteGroups(SapiBase):
    def __init__(self, creds_path: str = None,
                creds_dict: Dict = None,
                creds=None,
                scope=False,
                route_group_id: str = None):
        super().__init__(creds_path=creds_path,
                         creds_dict=creds_dict,
                         creds=creds,
                         scope=scope)


        self.flows = Flows(creds=self.creds)
        self.intents = Intents(creds=self.creds)
        self.webhooks = Webhooks(creds=self.creds)

        if route_group_id:
            self.route_group_id = route_group_id
            self.client_options = self._set_region(route_group_id)


    def get_route_groups_map(self, flow_id, reverse=False):
        """ Exports Agent Route Group UUIDs and Names into a user friendly dict.

        Args:
          - flow_id, the formatted CX Agent Flow ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values. If Optional reverse=True, the
              output will return page_name:ID mapping instead of ID:page_name
          """

        if reverse:
            pages_dict = {page.display_name: page.name
                          for page in self.list_transition_route_groups(flow_id)}

        else:
            pages_dict = {page.name: page.display_name
                          for page in self.list_transition_route_groups(flow_id)}

        return pages_dict

    def list_transition_route_groups(self, flow_id):
        request = types.transition_route_group.ListTransitionRouteGroupsRequest()
        request.parent = flow_id

        client_options = self._set_region(flow_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            credentials=self.creds,
            client_options=client_options)
        response = client.list_transition_route_groups(request)

        cx_route_groups = []
        for page in response.pages:
            for cx_route_group in page.transition_route_groups:
                cx_route_groups.append(cx_route_group)

        return cx_route_groups

    def get_transition_route_group(self, name):
        request = types.transition_route_group.GetTransitionRouteGroupRequest()
        request.name = name
        client_options = self._set_region(name)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            client_options=client_options)
        response = client.get_transition_route_group(request)

        return response

    def create_transition_route_group(self, flow_id, obj, **kwargs):
        #         request = types.transition_route_group.CreateTransitionRouteGroupRequest()

        # if rg object is given, set rg to it
        if obj:
            trg = obj
            trg.name = ''
        else:
            trg = types.transition_route_group.TransitionRouteGroup()

        # set optional args to rg attributes
        for key, value in kwargs.items():
            setattr(trg, key, value)

        client_options = self._set_region(flow_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            client_options=client_options)
        response = client.create_transition_route_group(
            parent=flow_id, transition_route_group=trg)

        return response

    def update_transition_route_group(self, rg_id, obj=None, **kwargs):
        # If route group object is given set route group to it
        if obj:
            # Set rg variable to rg object
            rg = obj
            # Set name attribute to the name of the updated page
            rg.name = rg_id
        else:
            rg = self.get_transition_route_group(rg_id)

        # Set rg attributes to arguments
        for key, value in kwargs.items():
            setattr(rg, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(rg_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            client_options=client_options)
        response = client.update_transition_route_group(
            transition_route_group=rg, update_mask=mask)

        return response

    def route_groups_to_dataframe(self, agent_id):
        """ This method extracts the Transition Route Groups from a given DFCX Agent
        and returns key information about the Route Groups in a Pandas Dataframe

        DFCX Route Groups exist as an Agent level resource, however they are
        categorized by the Flow they are associated with. This method will
        extract all Flows for the given agent, then use the Flow IDs to
        extract all Route Groups per Flow. Once all Route Groups have been
        extracted, the method will convert the DFCX object to a Pandas
        Dataframe and return this to the user.

        Args:
          - agent_id, the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>

        Returns:
          - df, a Pandas Dataframe
        """

        # The following dicts and lists are setup to use to map "user friendly"
        # data labels before writing the Route Group object to a dataframe.
        flows_dict = {
            flow.display_name: flow.name for flow in self.flows.list_flows(agent_id)}

        intent_dict = {intent.name.split('/')[-1]: intent.display_name
                       for intent in self.intents.list_intents(agent_id)}

        webhooks_dict = {webhook.name.split('/')[-1]: webhook.display_name
                         for webhook in self.webhooks.list_webhooks(agent_id)}

        route_groups_dict = {
            flow: self.list_transition_route_groups(
                flows_dict[flow]) for flow in flows_dict}

        rows_list = []
        for flow in route_groups_dict:
            for route_group in route_groups_dict[flow]:
                for route in route_group.transition_routes:
                    temp_dict = {}

                    temp_dict.update({'flow': flow})
                    temp_dict.update(
                        {'route_group_name': route_group.display_name})
                    temp_dict.update(
                        {'intent': intent_dict[route.intent.split('/')[-1]]})

                    if route.trigger_fulfillment.webhook:
                        temp_dict.update(
                            {'webhook': webhooks_dict[route.trigger_fulfillment.webhook.split('/')[-1]]})

                    temp_dict.update(
                        {'webhook_tag': route.trigger_fulfillment.tag})

                    if len(route.trigger_fulfillment.messages) > 0:
                        if len(
                                route.trigger_fulfillment.messages[0].text.text) > 0:
                            temp_dict.update(
                                {'fulfillment_message': route.trigger_fulfillment.messages[0].text.text[0]})

                    rows_list.append(temp_dict)

        df = pd.DataFrame(rows_list)

        return df