"""Site Search Service functions for Vertex Search and Conversation."""

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
from google.cloud.discoveryengine_v1alpha.types import TargetSite

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Sites(scrapi_base.ScrapiBase):
    """Site Search Class for Data Stores in Vertex Search and Conversation."""
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
    def __get_site_type(include_site: bool) -> TargetSite.Type:
        """Get the Site Type mapping."""
        site_type_map = {True: 1, False: 2}

        return site_type_map[include_site]

    def __build_site_search_parent(self, data_store_id: str) -> str:
        """Build the Parent ID needed for Site Search API calls."""
        parts = self._parse_resource_path("data_store", data_store_id)
        location = parts.get("location")
        data_store_id_short = parts.get("data_store")

        return (f"{self._build_data_store_parent(location)}/dataStores/"
                f"{data_store_id_short}/siteSearchEngine")

    def get_sites_map(
            self, data_store_id: str, reverse: bool = False) -> Dict[str, str]:
        """Get a user friendly mapping for Site Names and IDs."""
        if reverse:
            site_dict = {
                site.generated_uri_pattern: site.name
                for site in self.list_sites(data_store_id=data_store_id)
            }

        else:
            site_dict = {
                site.name: site.generated_uri_pattern
                for site in self.list_sites(data_store_id=data_store_id)
            }

        return site_dict

    def list_sites(self, data_store_id: str) -> List[TargetSite]:
        """List all URL patterns for a given Data Store ID."""
        client_options = self._client_options_discovery_engine(data_store_id)
        client = discoveryengine_v1alpha.SiteSearchEngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        parent = self.__build_site_search_parent(data_store_id)
        request = discoveryengine_v1alpha.ListTargetSitesRequest(
            parent=parent,
            page_size=1000
        )

        page_result = client.list_target_sites(request=request)

        sites = []
        for response in page_result:
            sites.append(response)

        return sites

    def get_site(self, site_id: str) -> TargetSite:
        """Get a single Site by specified ID."""
        client_options = self._client_options_discovery_engine(site_id)
        client = discoveryengine_v1alpha.SiteSearchEngineServiceClient(
            credentials=self.creds, client_options=client_options
        )
        request = discoveryengine_v1alpha.GetTargetSiteRequest(name=site_id)
        response = client.get_target_site(request=request)

        return response

    def create_site(self, data_store_id: str, uri_pattern: str,
                    include_site: bool = True, exact_match: bool = False
                    ) -> Operation:
        """Create a new Target Site in the specified Data Store.

        Args:
          data_store_id: the fully qualified Data Store ID
          uri_pattern: The user provided URI pattern from which the
            generated_uri_pattern is generated.
          include_site: If set to True, the uri pattern will be Included. If set
            to False, the site pattern will be Excluded.
          exact_match: If set to false, a uri_pattern is generated to include
            all pages whose address contains the provided_uri_pattern. If set to
            true, an uri_pattern is generated to try to be an exact match of the
            provided_uri_pattern or just the specific page if the
            provided_uri_pattern is a specific one. provided_uri_pattern is
            always normalized to generate the URI pattern to be used by the
            search engine.
        """
        client_options = self._client_options_discovery_engine(data_store_id)
        client = discoveryengine_v1alpha.SiteSearchEngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        target_site = discoveryengine_v1alpha.TargetSite()
        target_site.provided_uri_pattern = uri_pattern
        target_site.type_ = self.__get_site_type(include_site)
        target_site.exact_match = exact_match

        parent = self.__build_site_search_parent(data_store_id)
        request = discoveryengine_v1alpha.CreateTargetSiteRequest(
            parent=parent,
            target_site=target_site
            )

        operation = client.create_target_site(request=request)

        return operation

    def delete_site(self, site_id: str) -> Operation:
        """Deletes a TargetSite in a Data Store by the specified ID."""
        client_options = self._client_options_discovery_engine(site_id)
        client = discoveryengine_v1alpha.SiteSearchEngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        request = discoveryengine_v1alpha.DeleteTargetSiteRequest(name=site_id)
        operation = client.delete_target_site(request=request)

        return operation

    def enable_advanced_site_search(self, data_store_id: str) -> Operation:
        """Enables Advanced Site Search for the provided Data Store ID."""
        client_options = self._client_options_discovery_engine(data_store_id)
        client = discoveryengine_v1alpha.SiteSearchEngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        parent = self.__build_site_search_parent(data_store_id)
        request = discoveryengine_v1alpha.EnableAdvancedSiteSearchRequest(
            site_search_engine=parent
            )

        operation = client.enable_advanced_site_search(request=request)

        return operation

    def disable_advanced_site_search(self, data_store_id: str) -> Operation:
        """Disable Advanced Site Search for the provided Data Store ID."""
        client_options = self._client_options_discovery_engine(data_store_id)
        client = discoveryengine_v1alpha.SiteSearchEngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        parent = self.__build_site_search_parent(data_store_id)
        request = discoveryengine_v1alpha.DisableAdvancedSiteSearchRequest(
            site_search_engine=parent
            )

        operation = client.disable_advanced_site_search(request=request)

        return operation

    def recrawl_uris(self, data_store_id: str, uris: List[str]) -> Operation:
        """Recrawl the specified set of URIs for the Data Store."""
        client_options = self._client_options_discovery_engine(data_store_id)
        client = discoveryengine_v1alpha.SiteSearchEngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        parent = self.__build_site_search_parent(data_store_id)
        request = discoveryengine_v1alpha.RecrawlUrisRequest(
            site_search_engine=parent, uris=uris
            )

        operation = client.recrawl_uris(request=request)

        return operation

    def get_site_index_status(self, site_id: str) -> str:
        """Get the Site Indexing Status f0r the provided Site ID."""
        site = self.get_site(site_id)

        return site.indexing_status

    def get_site_verification_status(self, site_id: str) -> str:
        """Get the Site Verification Status for the provided Site ID."""
        site = self.get_site(site_id)
        state = site.site_verification_info.site_verification_state

        verify_map = {
            1: "VERIFIED: Site ownership verified",
            2: ("UNVERIFIED: Site ownership pending verification or"
                " verification failed"),
            3: ("EXEMPTED: Site exempt from verification, e.g. a public website"
                " that opens to all.")
        }

        return verify_map[state.value]
