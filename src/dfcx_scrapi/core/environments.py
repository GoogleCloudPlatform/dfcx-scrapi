"""CX Environments Resource functions."""

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
import google.protobuf.field_mask_pb2 as fm_pb
from dfcx_scrapi.core.scrapi_base import ScrapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Environments(ScrapiBase):
    """Core Class for CX Environments Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
        )

        if agent_id:
            self.agent_id = agent_id

    def list_environments(self, agent_id:str=None):
        """List all Versions for a given Flow"""

        if not agent_id:
            agent_id = self.agent_id

        request = types.environment.ListEnvironmentsRequest()

        request.parent = agent_id
        client_options = self._set_region(agent_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.list_environments(request)

        environments = []
        for page in response.pages:
            for environment in page.environments:
                environments.append(environment)

        return environments

    def get_environment(
        self,
        environment_id:str=None,
        display_name:str=None,
        agent_id:str=None
    ) -> types.environment.Environment:
        """Get Environment object for specified environment.
        Requires either environment's ID or display name.
        If both are provided, display_name is considered first.

        Args:
          environment_id: Unique environment ID of the target to get. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>

          display_name: target environment's human-legible display name.

          agent_id: The targeted agent for the operation. Defaults to self.agent_id. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>

        Returns:
            Environment object.
        """

        if not display_name and not environment_id:
            logging.warning("get_environment() requires environment_id or display_name.")
            return None

        if not agent_id:
            agent_id = self.agent_id

        if display_name:
            response = self.get_environment_by_display_name(display_name)

        else:
            request = types.environment.GetEnvironmentRequest(name=environment_id)
            client_options = self._set_region(agent_id)
            client = services.environments.EnvironmentsClient(
                client_options=client_options, credentials=self.creds
            )

            response = client.get_environment(request)

        return response

    def get_environment_by_display_name(
        self,
        display_name:str,
        agent_id:str=None
    ) -> types.environment.Environment:
        """Get Environment object for specific environment by its display name.
        This technically duplicates get_environment(), but one uses the other,
        and I see no reason to keep it as private.

        Args:
          display_name: Human readable display name of the target to get.

          agent_id: The agent for the operation. Defaults to self.agent_id. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>

        Returns:
            Environment object.
        """
        if not agent_id:
            agent_id = self.agent_id

        result = None
        environment_list = self.list_environments(agent_id)
        for environment_obj in environment_list:
            if environment_obj.display_name == display_name:
                result = environment_obj

        return result


    def create_environment(
        self,
        environment:types.environment.Environment,
        agent_id:str=None):
        """Create a new environment for a specified agent.
        Args:
          environment: Required. The environment to create.
            type google.cloud.dialogflowcx_v3beta1.types.Environment

          agent_id: The targeted agent for the operation. Defaults to self.agent_id. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>

        Returns:
          An object representing a long-running operation. (LRO)
        """

        if not agent_id:
            agent_id = self.agent_id


        request = types.environment.CreateEnvironmentRequest(
            environment = environment,
            parent = agent_id
        )

        client_options = self._set_region(agent_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.create_environment(request)

        return response


    def update_environment(
        self,
        environment:types.environment.Environment,
        update_mask:fm_pb.FieldMask,
        agent_id:str=None):
        """Update an existing environment for a specified agent.

        Args:
          environment: Required. The environment to update.
            type google.cloud.dialogflowcx_v3beta1.types.Environment

          update_mask: Required. FieldMask object indicating which
            fields are to be changed.

          agent_id: The targeted agent for the operation. Defaults to self.agent_id. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>

        Returns:
          An object representing a long-running operation. (LRO)
        """

        if not agent_id:
            agent_id = self.agent_id


        request = types.environment.UpdateEnvironmentRequest(
            environment = environment,
            update_mask = update_mask
        )

        client_options = self._set_region(agent_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.update_environment(request)

        return response


    def delete_environment(self, environment_id:str):
        """Delete a specified environment.

        Args:
          environment_id: unique ID associated with target environment. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>.
        """

        request = types.environment.DeleteEnvironmentRequest(
            name = environment_id
        )

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        client.delete_environment(request)


    def deploy_flow_to_environment(
        self,
        environment_id:str,
        flow_version:str):
        """Deploys a flow to the specified environment.

         Args:
          environment_id: unique ID associated with target environment. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>.
          flow_version: Required. The flow version to deploy. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/ flows/<Flow ID>/versions/<Version ID>

        Returns:
          An object representing a long-running operation. (LRO)
        """

        request = types.environment.DeployFlowRequest(
            environment = environment_id,
            flow_version = flow_version
        )

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.deploy_flow(request)
        return response


    def lookup_environment_history(self, environment_id:str):
        """Looks up the history of the specified environment.

        Args:
          environment_id: unique ID associated with target environment. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>.

        Returns:
          environments.pagers.LookupEnvironmentHistoryPager:
            Iterating over this object will yield results and
            resolve additional pages automatically.
        """
        request = types.environment.LookupEnvironmentHistoryRequest(
            name = environment_id
        )

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.lookup_environment_history(request)

        return response

    def list_continuous_test_results(self, environment_id:str):
        """Fetches a list of continuous test results for a given environment.

        Args:
          environment_id: unique ID associated with target environment. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>.

        Returns:
          environments.pagers.ListContinuousTestResultsPager:
            Iterating over this object will yield results and
            resolve additional pages automatically.
        """

        request = types.environment.ListContinuousTestResultsRequest(
            parent = environment_id
        )

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.list_continuous_test_results(request)

        return response
