"""Agent processing methods and functions."""

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

import time
import os
from typing import Dict

from dfcx_scrapi.core import agents
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.agent_extract import flows
from dfcx_scrapi.agent_extract import intents
from dfcx_scrapi.agent_extract import entity_types
from dfcx_scrapi.agent_extract import test_cases
from dfcx_scrapi.agent_extract import webhooks
from dfcx_scrapi.agent_extract import gcs_utils
from dfcx_scrapi.agent_extract import types

class Agents(scrapi_base.ScrapiBase):
    """Agent Metadata methods and functions."""
    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )
        self.agent_id = agent_id
        self._core_agents = agents.Agents(creds=creds)
        self.gcs = gcs_utils.GcsUtils()
        self.flows = flows.Flows()
        self.intents = intents.Intents()
        self.etypes = entity_types.EntityTypes()
        self.webhooks = webhooks.Webhooks()
        self.tcs = test_cases.TestCases()

    def process_agent(self, agent_id: str, gcs_bucket_uri: str,
                      environment_display_name: str = None):
        """Process the specified Agent for offline data gathering."""
        agent_local_path = "tmp/agent"
        _ = self._core_agents.export_agent(
            agent_id=agent_id,gcs_bucket_uri=gcs_bucket_uri, data_format="JSON",
            environment_display_name=environment_display_name)

        if not os.path.exists(agent_local_path):
            os.makedirs(agent_local_path)

        time.sleep(2)
        agent_file = self.gcs.download_gcs(
            gcs_path=gcs_bucket_uri, local_path=agent_local_path)

        self.gcs.unzip(agent_file, agent_local_path)

        data = types.AgentData()
        data.agent_id = agent_id
        data = self.flows.process_flows_directory(agent_local_path, data)
        data = self.intents.process_intents_directory(agent_local_path, data)
        data = self.etypes.process_entity_types_directory(
            agent_local_path, data)
        data = self.webhooks.process_webhooks_directory(agent_local_path, data)
        data = self.tcs.process_test_cases_directory(agent_local_path, data)

        return data
