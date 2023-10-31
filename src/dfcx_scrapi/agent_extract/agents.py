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

import logging
import time
import os
import shutil
from typing import Dict

from dfcx_scrapi.core import agents
from dfcx_scrapi.core import operations
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.agent_extract import graph
from dfcx_scrapi.agent_extract import flows
from dfcx_scrapi.agent_extract import intents
from dfcx_scrapi.agent_extract import entity_types
from dfcx_scrapi.agent_extract import test_cases
from dfcx_scrapi.agent_extract import webhooks
from dfcx_scrapi.agent_extract import gcs_utils
from dfcx_scrapi.agent_extract import types

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class Agents(scrapi_base.ScrapiBase):
    """Agent Metadata methods and functions."""
    def __init__(
        self,
        agent_id: str,
        lang_code: str = "en",
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
        self.lang_code = lang_code
        self._core_agents = agents.Agents(creds=creds)
        self.gcs = gcs_utils.GcsUtils()
        self.flows = flows.Flows()
        self.intents = intents.Intents()
        self.etypes = entity_types.EntityTypes()
        self.webhooks = webhooks.Webhooks()
        self.tcs = test_cases.TestCases()
        self.ops = operations.Operations()

    @staticmethod
    def prep_local_dir(agent_local_path: str):
        """Prepare the local directory for agent zip file."""
        if os.path.isdir(agent_local_path):
            logging.info("Cleaning up old directory...")
            shutil.rmtree(agent_local_path)
            logging.info(f"Making temp directory: {agent_local_path}")
            os.mkdir(agent_local_path)
        else:
            os.mkdir(agent_local_path)

    def await_lro(self, lro: str):
        """Wait for long running operation to complete."""
        try:
            i = 0
            while not self.ops.get_lro(lro).done:
                time.sleep(1)
                i += 1
                if i == 20:
                    break

        except UserWarning:
            print("LRO Failed.")

        return True

    def export_agent(self, agent_id: str, gcs_bucket_uri: str,
                      environment_display_name: str = None):
        """Handle the agent export, LRO and logging."""
        export_start = time.time()
        logging.info("Exporting agent...")
        lro = self._core_agents.export_agent(
            agent_id=agent_id,gcs_bucket_uri=gcs_bucket_uri, data_format="JSON",
            environment_display_name=environment_display_name)


        self.await_lro(lro)
        logging.info("Export Complete.")
        logging.debug(f"EXPORT: {time.time() - export_start}")

    def download_and_extract(self, agent_local_path: str, gcs_bucket_uri: str):
        """Handle download from GCS and extracting ZIP file."""
        if not os.path.exists(agent_local_path):
            os.makedirs(agent_local_path)

        download_start = time.time()
        logging.info("Downloading agent file from GCS Bucket...")
        agent_file = self.gcs.download_gcs(
            gcs_path=gcs_bucket_uri, local_path=agent_local_path)
        logging.info("Download complete.")
        logging.debug(f"DOWNLOAD: {time.time() - download_start}")

        self.gcs.unzip(agent_file, agent_local_path)


    def process_agent(self, agent_id: str, gcs_bucket_uri: str,
                      environment_display_name: str = None):
        """Process the specified Agent for offline data gathering."""
        agent_local_path = "/tmp/agent"
        self.prep_local_dir(agent_local_path)
        self.export_agent(agent_id, gcs_bucket_uri, environment_display_name)
        self.download_and_extract(agent_local_path, gcs_bucket_uri)

        logging.info("Processing Agent...")
        data = types.AgentData()
        data.graph = graph.Graph()
        data.lang_code = self.lang_code
        data.agent_id = agent_id
        data = self.flows.process_flows_directory(agent_local_path, data)
        data = self.intents.process_intents_directory(agent_local_path, data)
        data = self.etypes.process_entity_types_directory(
            agent_local_path, data)
        data = self.webhooks.process_webhooks_directory(agent_local_path, data)
        data = self.tcs.process_test_cases_directory(agent_local_path, data)
        logging.info("Processing Complete.")

        return data
