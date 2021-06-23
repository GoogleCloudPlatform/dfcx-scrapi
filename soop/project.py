# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
import time
from dfcx_sapi.core.sapi_base import SapiBase
from dfcx_sapi.core.agents import Agents

from typing import Dict

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

class Project(SapiBase):
    def __init__(self, creds_path: str = None,
                creds_dict: Dict = None,
                creds=None,
                scope=False,
                project_id: str = None):
        super().__init__(creds_path=creds_path,
                         creds_dict=creds_dict,
                         creds=creds,
                         scope=scope)

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
            'global', 'us-central1', 'us-east1', 'us-west1', 'asia-northeast1',
            'australia-southeast1', 'northamerica-northeast1', 'europe-west1',
            'europe-west2',
        ]

        if project_id:
            self.project_id = project_id

        all_agents = []
        for region in region_list:
            location_path = 'projects/{}/locations/{}'.format(
                self.project_id,
                region
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

        logging.info('='*10 + ' Fetching all Agent IDs ' + '='*10)
        all_agents = self.list_agents()
        logging.info('Received %s Agent IDs' % len(all_agents))

        logging.info('='*10 + ' Strating Agent Backups ' + '='*10)

        lro_list = []
        for agent in all_agents:
            logging.info('Backing up Agent: %s' % agent.display_name)
            temp_display_name = agent.display_name
            temp_display_name = temp_display_name.strip()
            temp_display_name = temp_display_name.lower()
            temp_display_name = temp_display_name.replace(' ','_')
            temp_display_name = temp_display_name.replace('/','_')
            temp_display_name = temp_display_name.replace(':','_')
            temp_display_name = temp_display_name.replace('-','_')
            temp_gcs_uri = 'gs://{}/{}'.format(gcs_bucket, temp_display_name)

            lro_list.append(self.agents.export_agent(agent.name, temp_gcs_uri))

            time.sleep(1)

        logging.info('='*10 + ' Agent Backup Job Complete ' + '='*10)

        return lro_list