"""CX Versions Resource functions."""

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
from google.oauth2 import service_account
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Versions(scrapi_base.ScrapiBase):
    """Core Class for CX Versions Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict[str,str] = None,
        creds: service_account.Credentials = None,
        flow_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
        )

        if flow_id:
            self.flow_id = flow_id

    @scrapi_base.api_call_counter_decorator
    def list_versions(self, flow_id:str):
        """List all Versions for a given Flow.

        Args:
          flow_id: Required. The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>
              /flows/<Flow ID>

        Returns:
          List of Version objects.
        """
        if not flow_id:
            flow_id = self.flow_id

        request = types.version.ListVersionsRequest()
        request.parent = flow_id

        client_options = self._set_region(flow_id)
        client = services.versions.VersionsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.list_versions(request)

        versions = []
        for page in response.pages:
            for version in page.versions:
                versions.append(version)

        return versions

    @scrapi_base.api_call_counter_decorator
    def get_version(
        self,
        version_id:str=None,
        display_name:str=None,
        flow_id:str=None):
        """Get Version object for specific version.

        Requires either Version's ID or Version's display name.
        If both are provided, display_name is considered first.

        Args:
          version_id: Unique Version ID of the target to get. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/flows/<Flow ID>/versions/<Version ID>
          display_name: Human readable display name of the Version to get.
          flow_id: The targeted flow for the operation. format:
          projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
            flows/<Flow ID>

        Returns:
          Version object.
        """

        if not display_name and not version_id:
            logging.warning("versions.get_version requires version_id or"
            " display_name.")
            return None

        if display_name:
            response = self.get_version_by_display_name(display_name, flow_id)

        else:
            request = types.version.GetVersionRequest(name=version_id)
            client = services.versions.VersionsClient(
                client_options=self._set_region(version_id),
                credentials=self.creds
            )

            response = client.get_version(request)

        return response

    def get_version_by_display_name(self, display_name:str, flow_id:str):
        """Get Version object for specific version by its display name.

        Args:
          display_name: Human readable display name of the target to get.
          flow_id: The targeted flow for the operation. format:
          projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
            flows/<Flow ID>

        Returns:
          Version object.
        """
        versions_list = self.list_versions(flow_id)
        for version_obj in versions_list:
            if version_obj.display_name == display_name:
                return version_obj

        return None

    @scrapi_base.api_call_counter_decorator
    def load_version(
        self,
        version:types.version.Version,
        allow_override:bool = False,
        flow_id:str = None):
        """Switch a flow to the specified version.

        Args:
          version: Version object of the desired target version.
          allow_override: allow_override_agent_resources is false,
                conflicted agent-level resources will not be overridden
                (i.e. intents, entities, webhooks)
          flow_id: The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              flows/<Flow ID>

        Returns:
          An object representing a long-running operation (LRO).
        """

        if not flow_id:
            flow_id = self.flow_id

        request = types.version.LoadVersionRequest(
            name=version.name,
            allow_override_agent_resources=allow_override
        )

        client_options = self._set_region(flow_id)
        client = services.versions.VersionsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.load_version(request)
        return response

    @scrapi_base.api_call_counter_decorator
    def create_version(
        self,
        flow_id:str,
        display_name:str,
        description:str=None):
        """Create a Version for the specified Flow ID.

        Args:
          flow_id: The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              flows/<Flow ID>
          display_name: Human readable display name of the Version created.
          description: Additional description details for the Version created.

        Returns:
          An object representing a long-running operation (LRO).
        """

        request = types.version.CreateVersionRequest()

        client_options = self._set_region(flow_id)
        client = services.versions.VersionsClient(
            client_options=client_options, credentials=self.creds
        )

        version = types.Version()
        version.display_name = display_name
        version.description = description

        request.parent = flow_id
        request.version = version

        response = client.create_version(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_version(self, version_id:str):
        """Delete a specified Version.

        Args:
          version_name: Unique Version ID of the target to delete. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/flows/<Flow ID>/versions/<Version ID>
        """
        request = types.version.DeleteVersionRequest(name=version_id)

        client = services.versions.VersionsClient(
            client_options=self._set_region(version_id),
            credentials=self.creds
        )

        return client.delete_version(request)

    @scrapi_base.api_call_counter_decorator
    def compare_versions(
        self,
        base_version_id:str,
        target_version_id:str,
        flow_id:str = None):
        """Compares the specified base version with target version.

        Args:
          base_version_id: ID of the base flow version
            to compare with the target version. format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/flows/<Flow ID>/versions/<Version ID>.
          target_version_id: ID of the target flow version
            to compare with the base version. format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/flows/<Flow ID>/versions/<Version ID>.
          flow_id: Required. The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/
            agents/<Agent ID>/flows/<Flow ID>

        Returns:
          types.CompareVersionsRequest Object.
        """
        if not flow_id:
            flow_id = self.flow_id

        request = types.version.CompareVersionsRequest(
            base_version=base_version_id,
            target_version=target_version_id
        )

        client_options = self._set_region(flow_id)
        client = services.versions.VersionsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.compare_versions(request)

        return response
