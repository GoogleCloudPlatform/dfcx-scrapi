"""Webhook Resource functions."""

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
from typing import Dict

from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2
from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Webhooks(scrapi_base.ScrapiBase):
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

    def get_webhooks_map(
        self,
        agent_id: str = None,
        reverse=False):
        """Exports Agent Webhook Names and UUIDs into a user friendly dict.

        Args:
          agent_id: the formatted CX Agent ID to use
          reverse: (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          Dictionary containing Webhook UUIDs as keys and
          webhook display names as values
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


    @scrapi_base.api_call_counter_decorator
    def list_webhooks(self, agent_id: str = None):
        """List all Webhooks in the specified CX Agent.

        Args:
          agent_id: the formated CX Agent ID to use

        Returns:
          List of webhook objects
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

    @scrapi_base.api_call_counter_decorator
    def create_webhook(
        self,
        agent_id: str,
        obj: types.Webhook = None,
        **kwargs):
        """Create a single webhook resource on a given CX Agent.

        Args:
          agent_id: the formatted CX Agent ID to create the webhook on
          obj: (Optional) the Webhook object of type
            types.Webhook that you want to create the webhook from

        Returns:
          The successfully created webhook object
        """
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


    @scrapi_base.api_call_counter_decorator
    def get_webhook(self, webhook_id:str):
        """Retrieves the specified webhook.

        Args:
          webhook_id: The ID of the webhook. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/webhooks/<Webhook

        Returns:
          The Webhook object.
        """
        request = types.webhook.GetWebhookRequest()
        request.name = webhook_id

        client_options = self._set_region(webhook_id)
        client = services.webhooks.WebhooksClient(
            client_options=client_options, credentials=self.creds)

        response = client.get_webhook(request)

        return response

    def get_webhook_by_display_name(
        self,
        webhook_display_name:str,
        agent_id:str = None):
        """Retrieves the specified webhook.

        Args:
          webhook_webhook_name: The display name of the webhook.
         agent_id: Optional. The formatted CX Agent ID.

        Returns:
          The Webhook object of the specified webhook.
        """

        if not agent_id:
            agent_id = self.agent_id

        webhook_map = self.get_webhooks_map(agent_id=agent_id,reverse=True)

        if webhook_display_name in webhook_map:
            webhook_obj = self.get_webhook(webhook_map[webhook_display_name])

        else:
            raise ValueError(
                f"Webhook \"{webhook_display_name}\" does not exist in the \
                    specified Agent."
                )

        return webhook_obj


    @scrapi_base.api_call_counter_decorator
    def update_webhook(
        self,
        webhook_id:str,
        webhook_obj:types.Webhook = None,
        **kwargs):
        """Update the values of an existing webhook.

        Args:
          webhook_id: The ID of the webhook. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/webhooks/<Webhook ID>
          webhook_obj: Optional Webhook object of types.Webhook
            that can be provided when you are planning to replace the full
            object vs. just partial updates.

        Returns:
          The Webhook object with specified changes.
        """
        if not webhook_obj:
            webhook_obj = types.Webhook()

        webhook_obj.name = webhook_id

        # set environment attributes from kwargs
        for key, value in kwargs.items():
            setattr(webhook_obj, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(webhook_id)
        client = services.webhooks.WebhooksClient(
            client_options=client_options, credentials=self.creds)

        request = types.webhook.UpdateWebhookRequest()
        request.webhook = webhook_obj
        request.update_mask = mask

        response = client.update_webhook(request)

        return response


    @scrapi_base.api_call_counter_decorator
    def delete_webhook(
        self, webhook_id: str = None,
        obj: types.Webhook = None, force: bool = False
    ):
        """Deletes a single Webhookd resource object.

        Args:
          webhook_id: intent to delete
          obj: (Optional) a CX Webhook object of types.Webhook
          force: (Optional) This field has no effect for webhook not being
            used. For webhooks that are used by pages/flows/transition route
            groups:
            -  If ``force`` is set to false, an error will be returned
               with message indicating the referenced resources.
            -  If ``force`` is set to true, Dialogflow will remove the
               webhook, as well as any references to the webhook and tags in
               fulfillments that point to this webhook will be removed.
        """
        if not webhook_id:
            webhook_id = self.webhook_id

        if obj:
            webhook_id = obj.name

        client_options = self._set_region(webhook_id)
        client = services.webhooks.WebhooksClient(
            client_options=client_options, credentials=self.creds)
        req = types.DeleteWebhookRequest(name=webhook_id, force=force)
        client.delete_webhook(request=req)
