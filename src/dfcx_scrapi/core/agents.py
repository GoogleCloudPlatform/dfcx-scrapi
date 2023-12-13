"""Agent Resource functions."""

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
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import environments

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Agents(scrapi_base.ScrapiBase):
    """Core Class for CX Agent Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if agent_id:
            self.agent_id = agent_id
            self.client_options = self._set_region(agent_id)

    @scrapi_base.api_call_counter_decorator
    def _list_agents_client_request(self, location_id) -> List[
        types.agent.Agent
    ]:
        """Builds the List Agents Request object.

        Args:
          location_id: The GCP Location ID in the following format:
            `projects/<project_id>/locations/<location>`

        Returns:
          List of types.agent.Agent"""

        request = types.agent.ListAgentsRequest()
        request.parent = location_id

        client_options = self._set_region(location_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.list_agents(request)

        agents = []
        for page in response.pages:
            for agent in page.agents:
                agents.append(agent)

        return agents

    def list_agents(
        self,
        project_id: str,
        location_id: str = None) -> List[types.Agent]:
        """Get list of all CX agents in a given GCP Region or Project.

        This method allows you to provide a GCP Project ID to retrieve all of
        the CX agents across ALL available GCP region. If the optional location
        ID is provided, the method will only pull the agents for that region.

        Args:
          project_id: The GCP Project ID. Ex: `my-cool-gcp-project`
          location_id: The GCP Location ID. Ex: `global`, `us-central1`, etc.

        Returns:
          List of Agent objects
        """

        if not location_id:
            region_list = [
                "global",
                "us-central1",
                "us-east1",
                "us-west1",
                "asia-northeast1",
                "asia-south1",
                "australia-southeast1",
                "northamerica-northeast1",
                "europe-west1",
                "europe-west2",
            ]

            agents = []
            for region in region_list:
                location_path = f"projects/{project_id}/locations/{region}"
                agents += self._list_agents_client_request(location_path)

        else:
            location_path = f"projects/{project_id}/locations/{location_id}"
            agents = self._list_agents_client_request(location_path)

        return agents

    @scrapi_base.api_call_counter_decorator
    def get_agent(self, agent_id: str) -> types.Agent:
        """Retrieves a single CX Agent resource object.

        Args:
          agent_id: The formatted CX Agent ID

        Returns:
          A single CX Agent resource object
        """

        request = types.agent.GetAgentRequest()
        request.name = agent_id

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_agent(request)

        return response

    def get_agent_by_display_name(
        self,
        project_id: str,
        display_name: str,
        location_id: str = None,
        region: str = None
    ) -> types.Agent:
        """Get CX agent in a given GCP project by its human readable
            display name.

        Args:
          project_id: The GCP Project ID as string
          display_name: human-readable display name of CX agent as string
          location_id: Optional. The GCP Project/Location ID, as string
              and in this format:
              `projects/<GCP PROJECT ID>/locations/<LOCATION ID>`
              Improves execution time and resolves conflicts caused
              when multiple agents on different regions have identical
              display names.
          region: Optional. The agent's region ID as string.
              Improves execution time and resolves conflicts caused
              when multiple agents on different regions have identical
              display names.
              Syntax for region ID can be found here:
              https://cloud.google.com/dialogflow/cx/docs/concept/region#avail

        Returns:
          CX agent resource object. If no agent is found, returns None.
        """

        if location_id:
            agent_list = self._list_agents_client_request(location_id)

        elif region:
            agent_list = self._list_agents_client_request(
                f"projects/{project_id}/locations/{region}"
                )
        else:
            agent_list = self.list_agents(project_id=project_id)

        possible_agent = None
        matched_agent = None

        for agent in agent_list:
            if agent.display_name == display_name and not matched_agent:
                matched_agent = agent
            elif agent.display_name == display_name and matched_agent:
                possible_agent = agent
            elif agent.display_name.lower() == display_name.lower():
                possible_agent = agent

        if possible_agent and not matched_agent:
            logging.warning(
                "display_name is case-sensitive. Did you mean \"%s\"?",
                possible_agent.display_name
            )
        elif possible_agent and matched_agent:
            logging.warning(
                '''Found multiple agents with the display name \"%s\".
                 Include location_id or region parameter to resolve cross-region
                 ambiguity.''',
                possible_agent.display_name
            )
            matched_agent = None

        return matched_agent

    @scrapi_base.api_call_counter_decorator
    def create_agent(
        self,
        project_id: str,
        display_name: str = None,
        gcp_region: str = "global",
        obj: types.Agent = None,
        **kwargs,
    ):
        """Create a Dialogflow CX Agent with given display name.

        By default the CX Agent will be created in the project that the user
        is currently authenticated to.
        If the user provides an existing Agent object, a new CX Agent will be
        created based on this object and any other input/kwargs will be
        discarded.

        Args:
          project_id: GCP project id where the CX agent will be created
          display_name: Human readable display name for the CX agent
          gcp_region: GCP region to create CX agent. Defaults to 'global'
          obj: (Optional) Agent object to create new agent from
            Refer to `builders.agents.AgentBuilder` to build one.

        Returns:
          The newly created CX Agent resource object.
        """

        parent = f"projects/{project_id}/locations/{gcp_region}"

        if obj:
            agent_obj = obj
            agent_obj.name = ""

        else:
            if not display_name:
                raise ValueError(
                    "At least display_name or obj should be specified."
                )
            agent_obj = types.Agent(
                display_name=display_name,
                default_language_code="en",
                time_zone="America/Chicago"
            )

            # set optional args as agent attributes
            for key, value in kwargs.items():
                setattr(agent_obj, key, value)

        client_options = self._set_region(parent)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.create_agent(parent=parent, agent=agent_obj)

        return response


    @scrapi_base.api_call_counter_decorator
    def validate_agent(
        self,
        agent_id: str,
        language_code: str = "en",
        timeout: float = None) -> Dict:
        """Initiates the Validation of the CX Agent or Flow.

        This function will start the Validation feature for the given Agent
        and then return the results as a Dict.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          timeout: (Optional) The timeout for this request

        Returns:
          Dictionary of Validation results for the entire Agent.
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.agent.ValidateAgentRequest()
        request.name = agent_id
        request.language_code = language_code

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.validate_agent(request, timeout=timeout)

        val_dict = self.cx_object_to_dict(response)

        return val_dict


    @scrapi_base.api_call_counter_decorator
    def get_validation_result(
        self,
        agent_id: str = None,
        timeout: float = None) -> Dict:
        """Extract Validation Results from CX Validation feature.

        This function will get the LATEST validation result run for the given
        CX Agent or CX Flow. If there has been no validation run on the Agent
        or Flow, no result will be returned. Use `dfcx.validate` function to
        run Validation on an Agent/Flow.

        Passing in the Agent ID will provide ALL validation results for
        ALL flows.
        Passing in the Flow ID will provide validation results for only
        that Flow ID.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          timeout: (Optional) The timeout for this request

        Returns:
          Dictionary of Validation results for the entire Agent.
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.agent.GetAgentValidationResultRequest()
        request.name = agent_id + "/validationResult"

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_agent_validation_result(
            request, timeout=timeout
        )

        val_results_dict = self.cx_object_to_dict(response)

        return val_results_dict

    @scrapi_base.api_call_counter_decorator
    def get_generative_settings(
        self, agent_id: str = None, language_code: str = "en"
        ) -> types.generative_settings.GenerativeSettings:
        """Get the current Generative Settings for the Agent."""
        if not agent_id:
            agent_id = self.agent_id

        request = types.agent.GetGenerativeSettingsRequest()
        request.name = f"{agent_id}/generativeSettings"
        request.language_code = language_code

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_generative_settings(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def update_generative_settings(
        self,
        agent_id: str = None,
        language_code: str = "en",
        obj: types.generative_settings.GenerativeSettings = None,
        **kwargs) -> types.generative_settings.GenerativeSettings:
        """Update the existing Generative Settings.

        Args:
          agent_id: Agent ID string in the following format
              projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          obj: (Optional) The Generative Settings object in proper format.
            This can also be extracted by using the get_generative_settings()
            method or built directly with the Generative Settings Builder class.
          kwargs: You can find a list of Generative Settings attributes here:
              https://cloud.google.com/python/docs/reference/dialogflow-cx/
               latest/google.cloud.dialogflowcx_v3beta1.types.GenerativeSettings
        Returns:
          The updated Generative Settings resource object.
        """
        if obj:
            gen_settings = obj
        else:
            gen_settings = self.get_generative_settings(agent_id)

        gen_settings.language_code = language_code

        for key, value in kwargs.items():
            setattr(gen_settings, key, value)

        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(gen_settings.name)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.update_generative_settings(
            generative_settings=gen_settings, update_mask=mask
        )

        return response


    @scrapi_base.api_call_counter_decorator
    def export_agent(
        self,
        agent_id: str,
        gcs_bucket_uri: str,
        environment_display_name: str = None,
        data_format: str = "BLOB",
        git_branch: str = None,
        git_commit_message: str = None,
        include_bq_export_settings: bool = False
    ) -> str:
        """Exports the specified CX agent to Google Cloud Storage bucket.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          gcs_bucket_uri: The Google Cloud Storage bucket/filepath to export the
            agent to in the following format:
              `gs://<bucket-name>/<object-name>`
          environment_display_name: CX Agent environment display name
            as string. If not set, DRAFT environment is assumed.
          data_format: Optional. The data format of the exported agent. If not
            specified, ``BLOB`` is assumed.
          git_branch: Optional. The Git branch to commit the exported agent to.
          git_commit_message: Optional. The Git Commit message to send. Only
            applicable if using `git_branch` arg.
          include_bigquery_export_settings: Will exclude or included the BQ
            settings on export.

        Returns:
          A Long Running Operation (LRO) ID that can be used to
            check the status of the export using
              dfcx_scrapi.core.operations->get_lro()
        """
        blob_format = types.agent.ExportAgentRequest.DataFormat(1)
        json_format = types.agent.ExportAgentRequest.DataFormat(4)

        request = types.agent.ExportAgentRequest()
        request.name = agent_id
        request.agent_uri = gcs_bucket_uri
        request.include_bigquery_export_settings = include_bq_export_settings

        if data_format in ["JSON", "ZIP", "JSON_PACKAGE"]:
            request.data_format = json_format
        else:
            request.data_format = blob_format

        if git_branch:
            git_settings = types.agent.ExportAgentRequest.GitDestination()
            git_settings.tracking_branch = git_branch
            git_settings.commit_message = git_commit_message
            request.git_destination = git_settings

        if environment_display_name:
            self._environments = environments.Environments(creds=self.creds)
            possible_environment = self._environments.get_environments_map(
                agent_id=agent_id, reverse=True
            ).get(environment_display_name)
            if possible_environment:
                request.environment = possible_environment
            else:
                raise ValueError(
                    "Invalid environment_display_name."
                    f" {environment_display_name} does not exist!"
                )

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.export_agent(request)

        return response.operation.name


    @scrapi_base.api_call_counter_decorator
    def restore_agent(
        self,
        agent_id: str,
        gcs_bucket_uri: str,
        restore_option: int = None
    ) -> str:
        """Restores a CX agent from a gcs_bucket location.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          gcs_bucket_uri: The Google Cloud Storage bucket/filepath to restore
            the agent from in the following format:
              `gs://<bucket-name>/<object-name>`
          restore_option: Optional.
              if not specified, then restore_option = 0 is assumed
              Below are the options for restoring an agent (int):
                  0:unspecified
                  1:always respect the settings from the exported agent file
                  2:fallback to default settings if not supported

        Returns:
          A Long Running Operation (LRO) ID that can be used to
            check the status of the import using
              dfcx_scrapi.core.operations->get_lro()
        """

        request = types.RestoreAgentRequest()
        request.name = agent_id
        request.agent_uri = gcs_bucket_uri

        if restore_option:
            request.restore_option = types.RestoreAgentRequest.RestoreOption(
                restore_option
            )

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.restore_agent(request)

        return response.operation.name

    @scrapi_base.api_call_counter_decorator
    def update_agent(
        self, agent_id: str, obj: types.Agent = None, **kwargs
    ) -> types.Agent:
        """Updates a single Agent object based on provided kwargs.

        Args:
          agent_id: CX Agent ID string in the following format
              projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          obj: (Optional) The CX Agent object in proper format. This can also
              be extracted by using the get_agent() method.
          kwargs: You may find a list of agent attributes here:
              https://cloud.google.com/python/docs/reference/dialogflow-cx/
                  latest/google.cloud.dialogflowcx_v3beta1.types.Agent
        Returns:
          The updated CX Agent resource object.
        """

        if obj:
            agent = obj
            agent.name = agent_id
        else:
            agent = self.get_agent(agent_id)

        # set agent attributes to args
        for key, value in kwargs.items():
            setattr(agent, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.update_agent(agent=agent, update_mask=mask)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_agent(
        self, agent_id: str = None, obj: types.Agent = None) -> str:
        """Deletes the specified Dialogflow CX Agent.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          obj: (Optional) a CX Agent object of types.Agent

        Returns:
          String "Agent '(agent_id)' successfully deleted."
        """
        if not agent_id:
            agent_id = self.agent_id

        if obj:
            agent_id = obj.name

        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options)
        client.delete_agent(name=agent_id)

        return "Agent '{agent_id}' successfully deleted."
