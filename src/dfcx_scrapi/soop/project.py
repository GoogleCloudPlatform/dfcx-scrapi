"""[BETA] Object Oriented Agent manipulation with Class inheritence."""

# Copyright 2021 Google LLC
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
from typing import Dict

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.agents import Agents

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Project(ScrapiBase):
    """Top Level class representing the Project level resources
    when working on a Dialogflow CX project. This Class will allow you to
    extract information about your GCP project as a whole in relation to
    your CX agents.
    """
    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        project_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if project_id:
            self.project_id = project_id

        self.agents = Agents(creds=self.creds)

    def list_agents(self, project_id=None):
        """Get list of all agents from all regions for a project.

        Args:
          project_id: (Optional) The GCP project id to list all agents
            from. If no project_id is provided the library will look at
            self.project_id or error.

        Returns:
          all_agents: A List of Dicts that has all agent metadata info.

        """
        region_list = [
            "global",
            "us-central1",
            "us-east1",
            "us-west1",
            "asia-northeast1",
            "australia-southeast1",
            "northamerica-northeast1",
            "europe-west1",
            "europe-west2",
        ]

        if not project_id:
            project_id = self.project_id

        all_agents = []
        for region in region_list:
            location_path = "projects/{}/locations/{}".format(
                project_id, region
            )

            all_agents += self.agents.list_agents(location_path)

        return all_agents

    def backup_all_agents(self, gcs_bucket: str, project_id: str = None):
        """Export all Agent files to GCS bucket.

        Args:
          gcs_bucket: The GCS bucket to backup all files to

        Returns:
          lro_list: List of all LROs to reference backend job status
        """
        if not project_id:
            project_id = self.project_id

        logging.info("==== Fetching all Agent IDs =====")
        all_agents = self.list_agents(project_id=project_id)
        logging.info("Received %s Agent IDs", len(all_agents))

        logging.info("==== Starting Agent Backups ====")

        lro_list = []
        for agent in all_agents:
            logging.info("Backing up Agent: %s", agent.display_name)
            temp_display_name = agent.display_name
            temp_display_name = temp_display_name.strip()
            temp_display_name = temp_display_name.lower()
            temp_display_name = temp_display_name.replace(" ", "_")
            temp_display_name = temp_display_name.replace("/", "_")
            temp_display_name = temp_display_name.replace(":", "_")
            temp_display_name = temp_display_name.replace("-", "_")
            temp_gcs_uri = "gs://{}/{}".format(gcs_bucket, temp_display_name)

            lro_list.append(self.agents.export_agent(agent.name, temp_gcs_uri))

            time.sleep(1)

        logging.info("==== Agent Backup Job Complete ====")

        return lro_list
