"""Data Stores Resource functions for Vertex Search and Conversation."""

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
from google.longrunning.operations_pb2 import Operation
from google.cloud import discoveryengine_v1alpha
from google.cloud.discoveryengine_v1alpha.types import DataStore

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class DataStores(scrapi_base.ScrapiBase):
    """Core Class for Data Store Resource functions."""
    def __init__(
        self,
        project_id: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.project_id = project_id

    @staticmethod
    def __get_content_config(content_type: str) -> DataStore.ContentConfig:
        """Build the Content Config used for the Data Store."""
        cc_map = {
            "unstructured": 1,
            "structured": 2,
            "website": 3
        }
        cc = DataStore.ContentConfig(cc_map[content_type])

        return cc

    def get_data_stores_map(self, location: str = "global",
                            reverse: bool = False) -> Dict[str,str]:
        """Get a user friendly mapping for Data Store Names and IDs."""
        if reverse:
            data_store_dict = {
                datastore.display_name: datastore.name
                for datastore in self.list_data_stores(location=location)
            }

        else:
            data_store_dict = {
                datastore.name: datastore.display_name
                for datastore in self.list_data_stores(location=location)
            }

        return data_store_dict

    def list_data_stores(
            self, location: str = "global") -> List[DataStore]:
        """List all data stores for a given project and location."""
        parent = self._build_data_store_parent(location)
        client = discoveryengine_v1alpha.DataStoreServiceClient()
        request = discoveryengine_v1alpha.ListDataStoresRequest(parent=parent)
        page_result = client.list_data_stores(request=request)

        datastores = []
        for datastore in page_result:
            datastores.append(datastore)

        return datastores

    def get_data_store(self, data_store_id: str) -> DataStore:
        """Get a single Data Store by specified ID."""
        client = discoveryengine_v1alpha.DataStoreServiceClient()
        request = discoveryengine_v1alpha.GetDataStoreRequest(
            name=data_store_id
            )

        response = client.get_data_store(request)

        return response

    def create_datastore(
            self, display_name: str, solution_type: str = "chat",
            datastore_type: str = "website", advanced_site_search: bool = True,
            location: str = "global") -> Operation:
        """Create a new Data Store type specified by the user.

        Args:
          display_name: The data store display name. This field must be a UTF-8
            encoded string with a length limit of 128 characters. Otherwise, an
            INVALID_ARGUMENT error is returned.
          solution_type: ONEOF [`chat`, `search`, `recommendation`]
          datastore_type: ONEOF [`website`, `structured`, `unstructured`]
          advanced_site_search: A boolean flag indicating whether user wants to
            directly create an advanced data store for site search. If the data
            store is not configured as site search (GENERIC vertical and
            PUBLIC_WEBSITE content_config), this flag will be ignored.
          location: the GCP region to create the Data Store in
        """
        parent = self._build_data_store_parent(location)
        client = discoveryengine_v1alpha.DataStoreServiceClient()
        data_store = discoveryengine_v1alpha.DataStore()
        data_store.display_name = display_name
        data_store.industry_vertical = 1
        data_store.solution_types = [self._get_solution_type(solution_type)]
        data_store.content_config = self.__get_content_config(datastore_type)

        request = discoveryengine_v1alpha.CreateDataStoreRequest(
            parent=parent,
            data_store=data_store,
            data_store_id=data_store.display_name,
            create_advanced_site_search=advanced_site_search
        )

        operation = client.create_data_store(request=request)

        return operation.operation

    def delete_datastore(self, data_store_id: str):
        """Delete the specified Data Store by ID."""
        client_options = self._client_options_discovery_engine(data_store_id)
        client = discoveryengine_v1alpha.DataStoreServiceClient(
            credentials=self.creds, client_options=client_options
        )

        request = discoveryengine_v1alpha.DeleteDataStoreRequest(
            name=data_store_id
        )
        operation = client.delete_data_store(request=request)

        return operation.operation
