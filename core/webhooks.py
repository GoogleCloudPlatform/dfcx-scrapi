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


class Webhooks:
    def __init__(self, creds_path: str, webhook_id: str = None):
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        self.creds.refresh(Request())  # used for REST API calls
        self.token = self.creds.token  # used for REST API calls

        if webhook_id:
            self.webhook_id = webhook_id
            self.client_options = self._set_region(webhook_id)

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
