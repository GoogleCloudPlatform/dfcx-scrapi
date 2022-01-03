"""Webhook Resource functions."""

# Copyright 2021 Google LLC
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

import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types

from dfcx_scrapi.core.scrapi_base import ScrapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Webhooks(ScrapiBase):
    """Core Class for CX Webhook Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        webhook_id: str = None,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if webhook_id:
            self.webhook_id = webhook_id
            self.client_options = self._set_region(webhook_id)

        if agent_id:
            self.agent_id = agent_id

    def get_webhooks_map(self, agent_id: str = None, reverse=False):
        """Exports Agent Webhook Names and UUIDs into a user friendly dict.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values
        """
        if not agent_id:
            agent_id = self.agent_id

        if reverse:
            webhooks_dict = {
                webhook.display_name: webhook.name
                for webhook in self.list_webhooks(agent_id)
            }

        else:
            webhooks_dict = {
                webhook.name: webhook.display_name
                for webhook in self.list_webhooks(agent_id)
            }

        return webhooks_dict

    def list_webhooks(self, agent_id: str = None):
        """List all Webhooks in the specified CX Agent.

        Args:
          agent_id, the formated CX Agent ID to use

        Returns:
          cx_webhooks, List of webhook objects
        """
        if not agent_id:
            agent_id = self.agent_id

        request = types.webhook.ListWebhooksRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.webhooks.WebhooksClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_webhooks(request)

        cx_webhooks = []
        for page in response.pages:
            for cx_webhook in page.webhooks:
                cx_webhooks.append(cx_webhook)

        return cx_webhooks

    def create_webhook(
        self, agent_id: str = None, obj: types.Webhook = None, **kwargs
    ):
        """Create a single webhook resource on a given CX Agent.

        Args:
          agent_id, the formatted CX Agent ID to create the webhook on
          obj, (Optional) the Webhook object of type
            types.Webhook that you want to create the webhook from

        Returns:
          response, a copy of the successfully created webhook object
        """
        if not agent_id:
            agent_id = self.agent_id

        if obj:
            webhook = obj
            webhook.name = ""
        else:
            webhook = types.webhook.Webhook()

        # set optional kwargs to webhook attributes
        for key, value in kwargs.items():
            setattr(webhook, key, value)

        client_options = self._set_region(agent_id)
        client = services.webhooks.WebhooksClient(
            client_options=client_options, credentials=self.creds)
        response = client.create_webhook(parent=agent_id, webhook=webhook)

        return response
