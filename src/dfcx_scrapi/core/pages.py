"""Page Resource functions."""

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
from typing import Dict, List
from google.cloud.dialogflowcx_v3beta1.services import pages
from google.cloud.dialogflowcx_v3beta1.types import page as gcdc_page
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Pages(scrapi_base.ScrapiBase):
    """Core Class for CX Page Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        scope=None,
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

        self.page_id = page_id
        self.flow_id = flow_id

    @staticmethod
    def _add_generic_pages_to_map(flow_id, pages_map, reverse):
        """Add the generic page names to each Page map.

        Dialogflow CX contains a few `special` pages names that are reserved
        and do not have UUID4 format IDs. This will take the existing page
        map and insert them in for downstream lookups.

        Args:
          flow_id: The Flow ID that contains the Pages in the pages_map
          pages_map: The existing pages_map Dict from `get_pages_map` that
            we will add the new special pages to.
          reverse: Boolean flag to swap key:value -> value:key
        """
        page_names = ["START_PAGE", "END_FLOW", "END_SESSION"]

        if reverse:
            for page in page_names:
                pages_map[page] = f"{flow_id}/pages/{page}"
        else:
            for page in page_names:
                pages_map[f"{flow_id}/pages/{page}"] = page

        return pages_map

    def get_pages_map(
        self, flow_id: str = None, reverse=False
    ) -> Dict[str, str]:
        """Exports Agent Page UUIDs and Names into a user friendly dict.

        Args:
          flow_id: the formatted CX Agent Flow ID to use
          reverse: (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          Dictionary containing Page UUIDs as keys and display names as values.
          If Optional reverse=True, the output will return page_name:ID mapping
          instead of ID:page_name
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

        pages_dict = self._add_generic_pages_to_map(
            flow_id, pages_dict, reverse
        )

        return pages_dict

    @scrapi_base.api_call_counter_decorator
    def list_pages(
        self,
        flow_id: str = None,
        language_code: str = "en") -> List[gcdc_page.Page]:
        """Get a List of all pages for the specified Flow ID.

        Args:
          flow_id: the properly formatted Flow ID string
          language_code: Specifies the language of the Pages listed. While the
            majority of contents of a Page is language agnostic, the contents
            in the "Agent Says" and similar parts of a Page are affected by
            language code.

        Returns:
          A List of CX Page objects for the specific Flow ID
        """
        request = gcdc_page.ListPagesRequest()
        request.parent = flow_id
        request.language_code = language_code

        client_options = self._set_region(flow_id)
        client = pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_pages(request)

        cx_pages = []
        for page in response.pages:
            for cx_page in page.pages:
                cx_pages.append(cx_page)

        return cx_pages

    @scrapi_base.api_call_counter_decorator
    def get_page(self, page_id: str = None) -> gcdc_page.Page:
        """Get a single CX Page object based on the provided Page ID.

        Args:
          page_id: a properly formatted CX Page ID

        Returns:
          A single CX Page Object
        """
        if not page_id:
            page_id = self.page_id

        client_options = self._set_region(page_id)
        client = pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_page(name=page_id)

        return response

    @scrapi_base.api_call_counter_decorator
    def create_page(
        self, flow_id: str = None, obj: gcdc_page.Page = None, **kwargs
    ) -> gcdc_page.Page:
        """Create a single CX Page object in the specified Flow ID.

        Args:
          flow_id: the CX Flow ID where the Page object will be created
          obj: (Optional) a CX Page object of gcdc_page.Page

        Returns:
          A copy of the successful Page object that was created
        """
        if not flow_id:
            flow_id = self.flow_id

        if obj:
            page = obj
            page.name = ""
        else:
            page = gcdc_page.Page()

        for key, value in kwargs.items():
            setattr(page, key, value)

        client_options = self._set_region(flow_id)
        client = pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.create_page(parent=flow_id, page=page)

        return response

    @scrapi_base.api_call_counter_decorator
    def update_page(
        self, page_id: str = None, obj: gcdc_page.Page = None, **kwargs
    ) -> gcdc_page.Page:
        """Update a single CX Page object.

        Args:
          page_id: the CX Page ID to update
          obj: (Optional) a CX Page object of gcdc_page.Page

        Returns:
          A copy of the successful Page object that was created
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
        client = pages.PagesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.update_page(page=page, update_mask=mask)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_page(
        self, page_id: str = None,
        obj: gcdc_page.Page = None, force: bool = False
    ):
        """Deletes the specified Page.

        Args:
          page_id: The formatted CX Page ID to delete.
          obj: (Optional) a CX Page object of gcdc_page.Page
          force: (Optional) This field has no effect for pages with no incoming
            transitions. If set to True, Dialogflow will remove the page,
            as well as any transitions to the page.
        """
        if not page_id:
            page_id = self.page_id

        if obj:
            page_id = obj.name

        client_options = self._set_region(page_id)
        client = pages.PagesClient(
            credentials=self.creds, client_options=client_options)
        req = gcdc_page.DeletePageRequest(name=page_id, force=force)
        client.delete_page(request=req)
