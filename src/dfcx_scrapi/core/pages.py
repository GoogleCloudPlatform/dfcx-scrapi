"""Page Resource functions."""

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
from typing import Dict, List
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core.scrapi_base import ScrapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Pages(ScrapiBase):
    """Core Class for CX Page Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        scope=False,
        creds=None,
        page_id: str = None,
        flow_id: str = None,
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

        if flow_id:
            self.flow_id = flow_id

    def get_pages_map(
        self, flow_id: str = None, reverse=False
    ) -> Dict[str, str]:
        """Exports Agent Page UUIDs and Names into a user friendly dict.

        Args:
          - flow_id, the formatted CX Agent Flow ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values. If Optional reverse=True, the
              output will return page_name:ID mapping instead of ID:page_name
        """
        if not flow_id:
            flow_id = self.flow_id

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

    def list_pages(self, flow_id: str = None) -> List[types.Page]:
        """Get a List of all pages for the specified Flow ID.

        Args:
          flow_id, the properly formatted Flow ID string

        Returns:
          cx_pages, A List of CX Page objects for the specific Flow ID
        """
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

    def get_page(self, page_id: str = None) -> types.Page:
        """Get a single CX Page object based on the provided Page ID.

        Args:
          page_id, a properly formatted CX Page ID

        Returns:
          response, a single CX Page Object of types.Page
        """
        if not page_id:
            page_id = self.page_id

        client_options = self._set_region(page_id)
        client = services.pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_page(name=page_id)

        return response

    def create_page(
        self, flow_id: str = None, obj: types.Page = None, **kwargs
    ) -> types.Page:
        """Create a single CX Page object in the specified Flow ID.

        Args:
          flow_id, the CX Flow ID where the Page object will be created
          obj, (Optional) a CX Page object of types.Page

        Returns:
          response, a copy of the successful Page object that was created
        """
        if not flow_id:
            flow_id = self.flow_id

        if obj:
            page = obj
            page.name = ""
        else:
            page = types.page.Page()

        for key, value in kwargs.items():
            setattr(page, key, value)

        client_options = self._set_region(flow_id)
        client = services.pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.create_page(parent=flow_id, page=page)

        return response

    def update_page(
        self, page_id: str = None, obj: types.Page = None, **kwargs
    ) -> types.Page:
        """Update a single CX Page object.

        Args:
          page_id, the CX Page ID to update
          obj, (Optional) a CX Page object of types.Page

        Returns:
          response, a copy of the successful Page object that was created
        """
        if obj:
            page = obj
            page.name = page_id
        else:
            if not page_id:
                page_id = self.page_id
            page = self.get_page(page_id)

        for key, value in kwargs.items():
            setattr(page, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(page_id)
        client = services.pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.update_page(page=page, update_mask=mask)

        return response
