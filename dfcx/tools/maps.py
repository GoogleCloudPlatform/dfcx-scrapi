import copy
import json
import logging
import os
import sys
import pandas as pd
import pathlib
import requests
import subprocess
import time
from collections import defaultdict
from typing import Dict, List
from .dfcx import DialogflowCX

import google.cloud.dialogflowcx_v3beta1.types as types

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class Tools:
    def __init__(self, creds, agent_id=None):

        with open(creds) as json_file:
            data = json.load(json_file)
        project_id = data['project_id']

        self.project_id = 'projects/{}/locations/global'.format(project_id)

        if agent_id:
            self.dfcx = DialogflowCX(creds, agent_id)
            self.agent_id = self.project_id + agent_id

        else:
            self.dfcx = DialogflowCX(creds)


# TODO: (pmarlow@) move this to @staticmethod outside of main function.
# perhaps move to the main dfcx.py file as a @staticmethod ?


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
                          for flow in self.dfcx.list_flows(agent_id)}

        else:
            flows_dict = {flow.name: flow.display_name
                          for flow in self.dfcx.list_flows(agent_id)}

        return flows_dict

    def get_intents_map(self, agent_id, reverse=False):
        """ Exports Agent Intent Names and UUIDs into a user friendly dict.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - intents_map, Dictionary containing Intent UUIDs as keys and
              intent.display_name as values
          """

        if reverse:
            intents_dict = {intent.display_name: intent.name
                            for intent in self.dfcx.list_intents(agent_id)}

        else:
            intents_dict = {intent.name: intent.display_name
                            for intent in self.dfcx.list_intents(agent_id)}

        return intents_dict

    def get_entities_map(self, agent_id, reverse=False):
        """ Exports Agent Entityt Names and UUIDs into a user friendly dict.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - intents_map, Dictionary containing Entity UUIDs as keys and
              intent.display_name as values
          """

        if reverse:
            entities_dict = {entity.display_name: entity.name
                             for entity in self.dfcx.list_entity_types(agent_id)}

        else:
            entities_dict = {entity.name: entity.display_name
                             for entity in self.dfcx.list_entity_types(agent_id)}

        return entities_dict

    def get_webhooks_map(self, agent_id, reverse=False):
        """ Exports Agent Webhook Names and UUIDs into a user friendly dict.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values
          """

        if reverse:
            webhooks_dict = {webhook.display_name: webhook.name
                             for webhook in self.dfcx.list_webhooks(agent_id)}

        else:
            webhooks_dict = {webhook.name: webhook.display_name
                             for webhook in self.dfcx.list_webhooks(agent_id)}

        return webhooks_dict

    def get_pages_map(self, flow_id, reverse=False):
        """ Exports Agent Page UUIDs and Names into a user friendly dict.

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
                          for page in self.dfcx.list_pages(flow_id)}

        else:
            pages_dict = {page.name: page.display_name
                          for page in self.dfcx.list_pages(flow_id)}

        return pages_dict

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
                          for page in self.dfcx.list_transition_route_groups(flow_id)}

        else:
            pages_dict = {page.name: page.display_name
                          for page in self.dfcx.list_transition_route_groups(flow_id)}

        return pages_dict
