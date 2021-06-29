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
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Pages(SapiBase):
    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        scope=False,
        creds=None,
        page_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if page_id:
            self.page_id = page_id
            self.client_options = self._set_region(page_id)

    def get_pages_map(self, flow_id, reverse=False):
        """Exports Agent Page UUIDs and Names into a user friendly dict.

        Args:
          - flow_id, the formatted CX Agent Flow ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values. If Optional reverse=True, the
              output will return page_name:ID mapping instead of ID:page_name
        """

        if reverse:
            pages_dict = {
                page.display_name: page.name
                for page in self.list_pages(flow_id)
            }

        else:
            pages_dict = {
                page.name: page.display_name
                for page in self.list_pages(flow_id)
            }

        return pages_dict

    def list_pages(self, flow_id):
        request = types.page.ListPagesRequest()
        request.parent = flow_id

        client_options = self._set_region(flow_id)
        client = services.pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_pages(request)

        cx_pages = []
        for page in response.pages:
            for cx_page in page.pages:
                cx_pages.append(cx_page)

        return cx_pages

    def get_page(self, page_id):
        client_options = self._set_region(page_id)
        client = services.pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_page(name=page_id)

        return response

    def create_page(self, flow_id, obj=None, **kwargs):
        # if page object is given, set page to it
        if obj:
            page = obj
            page.name = ""
        else:
            page = types.page.Page()

        # set optional arguments to page attributes
        for key, value in kwargs.items():
            setattr(page, key, value)

        client_options = self._set_region(flow_id)
        client = services.pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.create_page(parent=flow_id, page=page)
        return response

    def update_page(self, page_id, obj=None, **kwargs):
        # If page object is given set page to it
        if obj:
            # Set page variable to page object
            page = obj
            # Set name attribute to the name of the updated page
            page.name = page_id
        else:
            page = self.get_page(page_id)

        # Set page attributes to arguments
        for key, value in kwargs.items():
            setattr(page, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(page_id)
        client = services.pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        # Call client function with page and mask as arguments
        response = client.update_page(page=page, update_mask=mask)
        return response
