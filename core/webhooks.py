# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
import requests
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2

from dfcx_sapi.core.sapi_base import SapiBase
from typing import Dict, List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class Webhooks(SapiBase): 
    def __init__(self, creds_path: str = None,
                creds_dict: Dict = None,
                creds = None,
                scope=False,
                webhook_id: str = None):
        super().__init__(creds_path=creds_path,
                         creds_dict=creds_dict,
                         creds=creds,
                         scope=scope)
        
        if webhook_id:
            self.webhook_id = webhook_id
            self.client_options = self._set_region(webhook_id)


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
                             for webhook in self.list_webhooks(agent_id)}

        else:
            webhooks_dict = {webhook.name: webhook.display_name
                             for webhook in self.list_webhooks(agent_id)}

        return webhooks_dict

    def list_webhooks(self, agent_id):
        request = types.webhook.ListWebhooksRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.webhooks.WebhooksClient(
            credentials=self.creds,
            client_options=client_options)
        response = client.list_webhooks(request)

        cx_webhooks = []
        for page in response.pages:
            for cx_webhook in page.webhooks:
                cx_webhooks.append(cx_webhook)

        return cx_webhooks

    def create_webhook(self, agent_id, obj=None, **kwargs):
        # if webhook object is given, set webhook to it
        if obj:
            webhook = obj
            webhook.name = ''
        else:
            webhook = types.webhook.Webhook()

        # set optional kwargs to webhook attributes
        for key, value in kwargs.items():
            setattr(webhook, key, value)

        client_options = self._set_region(agent_id)
        client = services.webhooks.WebhooksClient(
            client_options=client_options)
        response = client.create_webhook(parent=agent_id, webhook=webhook)

        return response
