"""CX Environments Resource functions."""

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

from typing import List, Dict, Tuple
import logging
from google.oauth2 import service_account
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import flows
from dfcx_scrapi.core import versions

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Environments(scrapi_base.ScrapiBase):
    """Core Class for CX Environments Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict[str, str] = None,
        creds: service_account.Credentials = None,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
        )

        if agent_id:
            self.agent_id = agent_id

        self._versions = versions.Versions(creds=self.creds)
        self._flows = flows.Flows(creds=self.creds)

    @staticmethod
    def _get_flow_version_id(
        input_tuple: Tuple[str,str],
        flow_versions_list: List[types.Version]):
        """Parse Version ID based on Tuple inputs."""
        for version in flow_versions_list:
            if version.name.split("/")[-1] == str(input_tuple[1]):
                return version.name

        return print("Flow Name and Version combination not found in Agent.")

    def _get_filtered_flow_map(self, agent_id, flow_tuples):
        """Get Flows and Filter based on User Input"""
        flows_map = self._flows.get_flows_map(agent_id, reverse=True)
        input_flows = [flow[0] for flow in flow_tuples]
        filtered_map = {}
        for flow in input_flows:
            if flow in flows_map.keys():
                filtered_map[flow] = flows_map[flow]

        return filtered_map

    def _get_filtered_versions(self, filtered_map):
        """Get filtered versions Dict based on filtered Flows map"""
        filtered_versions = {}
        for flow in filtered_map:
            filtered_versions[flow] = self._versions.list_versions(
                filtered_map[flow])

        return filtered_versions

    def _get_final_versions(self, flow_tuples, filtered_versions):
        """Determine associated Flow Version IDs based on input tuple"""
        final_versions = []
        for version_tuple in flow_tuples:
            version_config = types.environment.Environment.VersionConfig()
            version_config.version = self._get_flow_version_id(
                version_tuple, filtered_versions[version_tuple[0]])

            final_versions.append(version_config)

        return final_versions

    def get_environments_map(
        self,
        agent_id: str = None,
        reverse: bool = False
    ) -> Dict[str, str]:
        """Exports Agent environment display names and UUIDs
        into a user friendly dict.

        Args:
          agent_id: the formatted CX Agent ID to use
          reverse: (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          Dictionary containing Environment UUIDs as keys and environment
            display name as values.
        """
        if not agent_id:
            agent_id = self.agent_id

        if reverse:
            environments_dict = {
                environment.display_name: environment.name
                for environment in self.list_environments(agent_id)
            }
        else:
            environments_dict = {
                environment.name: environment.display_name
                for environment in self.list_environments(agent_id)
            }

        return environments_dict

    @scrapi_base.api_call_counter_decorator
    def list_environments(self, agent_id: str = None):
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

    @scrapi_base.api_call_counter_decorator
    def get_environment(
        self,
        environment_id: str) -> types.environment.Environment:
        """Get Environment object for specified environment ID.

        Args:
          environment_id: Unique environment ID of the target to get. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>

        Returns:
          Environment object.
        """
        request = types.environment.GetEnvironmentRequest(
            name=environment_id)
        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.get_environment(request)

        return response

    def get_environment_by_display_name(
        self,
        display_name: str,
        agent_id: str) -> types.environment.Environment:
        """Get Environment object for specific environment by its display name.

        Args:
          display_name: Human readable display name of the target to get.
          agent_id: The agent for the operation. format:
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

    @scrapi_base.api_call_counter_decorator
    def create_environment(
        self,
        environment: types.environment.Environment,
        agent_id: str = None):
        """Create a new environment for a specified agent.
        Args:
          environment: The environment to create.
            type google.cloud.dialogflowcx_v3beta1.types.Environment
          agent_id: The targeted agent for the operation. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>

        Returns:
          An object representing a long-running operation. (LRO)
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.environment.CreateEnvironmentRequest()
        request.environment = environment
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.environments.EnvironmentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.create_environment(request)

        return response


    def create_environment_by_display_name(
        self,
        display_name: str,
        version_configs: List[Tuple[str, str]],
        description: str = None,
        agent_id: str = None):
        """Create a new environment for a specified agent.
        Args:
          display_name: The display name of the Environment to create
          version_configs: A List of Tuples, containing the Flow Display
            Names and Version IDs to include in the Environment creation.
            Ex:
              [('Default Start Flow', 2), ('Confidence Demo', 3), ('FlowC', 1)]

            Internally, the create_environment method will perform a lookup and
            pull the appropriate Flow Version IDs to assign to the Environment
            being created.
          agent_id: The targeted agent for the operation. format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>

        Returns:
          An object representing a long-running operation (LRO). View the
            result by inspecting response.result()
        """

        if not agent_id:
            agent_id = self.agent_id

        filtered_map = self._get_filtered_flow_map(agent_id, version_configs)
        all_versions = self._get_filtered_versions(filtered_map)
        final_versions = self._get_final_versions(version_configs, all_versions)

        # Build the Environment Object
        env = types.Environment()
        env.display_name = display_name
        env.version_configs = final_versions
        env.description = description

        request = types.environment.CreateEnvironmentRequest(
            environment = env,
            parent = agent_id
        )

        client_options = self._set_region(agent_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.create_environment(request)

        return response


    @scrapi_base.api_call_counter_decorator
    def update_environment(
        self,
        environment_id: str,
        environment_obj: types.Environment = None,
        **kwargs):
        """Update an existing environment for a specified agent.

        Args:
          environment_id: The specified environment to update.
          environment_obj: Optional Environment object of types.Environment
            that can be provided when you are planning to replace the full
            object vs. just partial updates.

        Returns:
          An object representing a long-running operation. (LRO)
        """

        if environment_obj:
            env = environment_obj
        else:
            env = types.Environment()

        env.name = environment_id

        # set environment attributes from kwargs
        for key, value in kwargs.items():
            setattr(env, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            credentials=self.creds, client_options=client_options
        )

        request = types.environment.UpdateEnvironmentRequest()
        request.environment = env
        request.update_mask = mask

        response = client.update_environment(request)

        return response


    @scrapi_base.api_call_counter_decorator
    def delete_environment(self, environment_id: str):
        """Delete a specified environment.

        Args:
          environment_id: unique ID associated with target environment. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>.
        """

        request = types.environment.DeleteEnvironmentRequest()
        request.name = environment_id

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            credentials=self.creds, client_options=client_options
        )

        client.delete_environment(request)


    @scrapi_base.api_call_counter_decorator
    def deploy_flow_to_environment(
        self,
        environment_id: str,
        flow_version: str):
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

        request = types.environment.DeployFlowRequest()
        request.environment = environment_id
        request.flow_version = flow_version

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.deploy_flow(request)

        return response


    @scrapi_base.api_call_counter_decorator
    def lookup_environment_history(
        self,
        environment_id: str) -> List[types.Environment]:
        """Looks up the history of the specified environment.

        Args:
          environment_id: unique ID associated with target environment. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>.

        Returns:
          List of Environment objects with historical timestamps.
        """
        request = types.environment.LookupEnvironmentHistoryRequest(
            name = environment_id
        )

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.lookup_environment_history(request)

        history = []
        for page in response.pages:
            for environment in page.environments:
                history.append(environment)

        return history

    @scrapi_base.api_call_counter_decorator
    def list_continuous_test_results(self, environment_id: str):
        """Fetches a list of continuous test results for a given environment.

        Args:
          environment_id: unique ID associated with target environment. Format:
            projects/<Project ID>/locations/<Location ID>/agents/
            <Agent ID>/environments/<Environment ID>.

        Returns:
          List of types.ContinuousTestResult.
        """

        request = types.environment.ListContinuousTestResultsRequest(
            parent = environment_id
        )

        client_options = self._set_region(environment_id)
        client = services.environments.EnvironmentsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.list_continuous_test_results(request)

        test_results = []
        for page in response.pages:
            for test in page.continuous_test_results:
                test_results.append(test)

        return test_results
