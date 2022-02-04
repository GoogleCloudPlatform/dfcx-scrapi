"""CX Versions Resource functions."""

# Copyright 2022 Google LLC
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


class Versions(ScrapiBase):
    """Core Class for CX Versions Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        flow_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
        )

        if flow_id:
            self.flow_id = flow_id

    def list_versions(self, flow_id:str):
        """List all Versions for a given Flow.

        Args:
          flow_id: Required. The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>
              /flows/<Flow ID>

        returns:
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

    def get_version(self, version_name:str=None, display_name:str=None, flow_id:str=None):
        """Get Version object for specific version.

        Requires either version's ID or version's display name.
        If both are provided, display_name is considered first.

        Args:
          version_name: Unique Version ID of the target to get. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/flows/<Flow ID>/versions/<Version ID>

          display_name: Version's human-legible display name of the target to get.

          flow_id: The targeted flow for the operation. Defaults to self.flow_id. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>

        Returns:
            Version object.
        """

        if not display_name and not version_name:
            logging.warning("versions.get_version requires param name or display_name.")
            return None

        if not flow_id:
            flow_id = self.flow_id

        if display_name:
            response = self.get_version_by_display_name(display_name)

        else:
            request = types.version.GetVersionRequest(name=version_name)
            client = services.versions.VersionsClient(
                client_options=self._set_region(flow_id),
                credentials=self.creds
            )

            response = client.get_version(request)

        return response


    def get_version_by_display_name(self, display_name, flow_id:str=None):
        """Get Version object for specific version by its display name.

        Args:
          display_name: Human readable display name of the target to get.

          flow_id: The targeted flow for the operation. Defaults to self.flow_id. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>

        Returns:
            Version object.
        """
        if not flow_id:
            flow_id = self.flow_id

        versions_list = self.list_versions(flow_id)
        for version_obj in versions_list:
            if version_obj.display_name == display_name:
                return version_obj

        return None

    def load_version(
        self,
        version:types.version.Version,
        allow_override:bool = False,
        flow_id:str = None
    ):
        """
        Switch a flow to the specified version.

        Args:
          version: Required. Version object of the desired target version.

          allow_override: allow_override_agent_resources is false,
                conflicted agent-level resources will not be overridden
                (i.e. intents, entities, webhooks)

          flow_id: Required. The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>

        Returns:
            An object representing a long-running operation (LRO)
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


    def create_version(self, version:types.version.Version, flow_id:str = None):
        """
        Switch a flow to the specified version.

        Args:
          version: Required. Version object of the desired target version.

          allow_override: allow_override_agent_resources is false, conflicted agent-level
          resources will not be overridden (i.e. intents, entities, webhooks)

          flow_id: Required. The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>

        Returns:
            An object representing a long-running operation (LRO)
        """
        if not flow_id:
            flow_id = self.flow_id

        request = types.version.CreateVersionRequest(
            version=version,
            parent=flow_id
        )

        client_options = self._set_region(flow_id)
        client = services.versions.VersionsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.create_version(request)
        return response

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

    def compare_versions(self, base_version:str, target_version:str, flow_id:str = None):
        """
        Compares the specified base version with target version.

        Args:
          version: Required. Version object of the desired target version.

          base_version: Required. Name of the base flow version
            to compare with the target version. format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/flows/<Flow ID>/versions/<Version ID>.

          target_version: Required. Name of the target flow version
            to compare with the base version. format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/flows/<Flow ID>/versions/<Version ID>.

          flow_id: Required. The targeted flow for the operation. Format:
            projects/<Project ID>/locations/<Location ID>/
            agents/<Agent ID>/flows/<Flow ID>

        Returns:
            dialogflowcx_v3beta1.types.CompareVersionsRequest Object
        """
        if not flow_id:
            flow_id = self.flow_id

        request = types.version.CompareVersionsRequest(
            base_version=base_version,
            target_version=target_version
        )

        client_options = self._set_region(flow_id)
        client = services.versions.VersionsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.compare_versions(request)
        return response
