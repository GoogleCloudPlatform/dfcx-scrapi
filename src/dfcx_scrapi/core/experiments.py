"""CX Experiment Resource functions."""

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

import json
import logging
from typing import Dict
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/dialogflow",
]


class ScrapiExperiments(scrapi_base.ScrapiBase):
    """Wrapper for working with Experiments"""

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
            agent_id=agent_id,
        )

        logging.info("created %s", self.agent_id)

    @scrapi_base.api_call_counter_decorator
    def list_experiments(self, environment_id: str = None):
        """List out experiments.

        Args:
          environment_id: (Optional) The ID for the environment from which
            the list of experiments will be retrieved.

        Returns:
          A list of experiment JSON objects.
        """
        environment_path = f"{self.agent_id}/environments/{environment_id}"
        logging.info("environment_path %s", environment_path)

        request = types.experiment.ListExperimentsRequest()
        request.parent = environment_path
        client_options = self._set_region(environment_path)
        client = services.experiments.ExperimentsClient(
            client_options=client_options, credentials=self.creds
        )
        response = client.list_experiments(request)
        blob = scrapi_base.ScrapiBase.cx_object_to_json(response)

        if len(blob) < 1:
            logging.warning(
                "no experiments found for environment: %s", environment_id
            )
            return None

        experiments: list = blob["experiments"]

        results = [
            {
                "environment_id": environment_id,
                "experiment_id": ex["name"].split("/").pop(),
                "displayName": ex["displayName"],
                "name": ex["name"],
            }
            for ex in experiments
        ]

        logging.info("results %s", json.dumps(results, indent=2))

        return experiments
