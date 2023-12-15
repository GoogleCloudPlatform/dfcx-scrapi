"""Engines Resource functions for Vertex Search and Conversation."""

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
from google.cloud.discoveryengine_v1alpha.types import Engine

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Engines(scrapi_base.ScrapiBase):
    """Engines Class for Data Stores in Vertex Search and Conversation."""
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

    def __process_data_store_ids(self, data_store_ids: List[str]) -> List[str]:
        """Process the data store IDs to ensure they are the correct format."""
        if not isinstance(data_store_ids, List):
            raise TypeError(f"Expected a List of Strings, got {data_store_ids}")

        processed_ids = []
        for ds_id in data_store_ids:
            processed_ids.append(self._validate_data_store_id(ds_id))

        return processed_ids

    def get_engines_map(
            self, location: str = "global", reverse: bool = False
            ) -> Dict[str, str]:
        """Get a user friendly mapping for Engine Names and IDs."""
        if reverse:
            engine_dict = {
                engine.display_name: engine.name
                for engine in self.list_engines(location=location)
            }

        else:
            engine_dict = {
                engine.name: engine.display_name
                for engine in self.list_engines(location=location)
            }

        return engine_dict

    def build_chat_engine_proto(
            self, display_name: str, business_name: str,
            data_store_ids: List[str], existing_df_agent_id: str = None,
            language_code: str = "en", time_zone: str = "America/Chicago"):
        """Build the Chat Engine proto for creating a new Engine.

        Args:
          display_name: the human readable display name of the Chat Engine
          business_name: the name of the company or business that corresponds
            most closely with the documents in the Data Store(s).
          existing_df_agent_id: the Dialogflow Agent ID to associate with the
            newly created Engine. Only provide this if linking to an existing
            Dialogflow CX Agent.
          language_code: the default language of the agent as a language tag
          time_zone: the time zone of the agent from the time zone database

        Returns:
          The Engine object configured as a ChatEngine.
        """
        data_store_ids = self.__process_data_store_ids(data_store_ids)

        engine = Engine()

        ce_config = Engine.ChatEngineConfig()

        agent_config = Engine.ChatEngineConfig.AgentCreationConfig()
        agent_config.business = business_name
        agent_config.default_language_code = language_code
        agent_config.time_zone = time_zone
        ce_config.agent_creation_config = agent_config

        if existing_df_agent_id:
            ce_config.dialogflow_agent_to_link = existing_df_agent_id

        engine.display_name = display_name
        engine.chat_engine_config = ce_config
        engine.solution_type = self._get_solution_type("chat")
        engine.data_store_ids = data_store_ids

        return engine

    def list_engines(
            self, location: str = "global") -> List[Engine]:
        """List all Engines for a given project and location."""
        parent = self._build_data_store_parent(location)
        client = discoveryengine_v1alpha.EngineServiceClient()
        request = discoveryengine_v1alpha.ListEnginesRequest(parent=parent)
        page_result = client.list_engines(request=request)

        engines = []
        for response in page_result:
            engines.append(response)

        return engines

    def get_engine(self, engine_id: str) -> Engine:
        """Get a single Engine by specified ID."""
        client = discoveryengine_v1alpha.EngineServiceClient()
        request = discoveryengine_v1alpha.GetEngineRequest(name=engine_id)
        response = client.get_engine(request=request)

        return response

    def create_engine(self, engine: Engine,
                      location: str = "global") -> Engine:
        """Create a new Vertex Search Engine based on user inputs.

        Use the DataStores.build_chat_engine_proto to create the proper Engine
        payload to pass in for the `engine` arg.

        Args:
          location, the GCP region to create the Engine in
          engine, a proto object of type discoveryengine_v1alpha.types.Engine
            Note that at this time only "Chat" engines are supported
          solution_type, "chat" is the only value supported at this time.
        """
        parent = self._build_data_store_parent(location)
        client_options = self._client_options_discovery_engine(parent)
        client = discoveryengine_v1alpha.EngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        request = discoveryengine_v1alpha.CreateEngineRequest(
            parent=parent,
            engine=engine,
            engine_id=engine.display_name
        )

        operation = client.create_engine(request=request)
        print("Waiting for operation to complete...")
        response = operation.result()
        print(f"Successfully created Engine: {response.display_name}")

        return response

    def delete_engine(self, engine_id: str) -> Operation:
        """Deletes the specified Engine."""
        client_options = self._client_options_discovery_engine(engine_id)
        client = discoveryengine_v1alpha.EngineServiceClient(
            credentials=self.creds, client_options=client_options
        )

        request = discoveryengine_v1alpha.DeleteEngineRequest(
            name=engine_id
        )
        operation = client.delete_engine(request=request)

        return operation.operation
