"""CX Experiment Resource functions."""
# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import json
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

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/dialogflow",
]


class SapiExperiments(ScrapiBase):
    """Wrapper for working with Experiments"""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_path: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
            agent_path=agent_path,
        )

        logging.info("created %s", self.agent_path)

    def list_experiments(self, environment_id=None):
        """list out experiments"""
        environment_path = f"{self.agent_path}/environments/{environment_id}"
        logging.info("environment_path %s", environment_path)

        request = types.experiment.ListExperimentsRequest()
        request.parent = environment_path
        client_options = self._set_region(environment_id)
        client = services.experiments.ExperimentsClient(
            client_options=client_options, credentials=self.creds
        )
        response = client.list_experiments(request)
        blob = ScrapiBase.cx_object_to_json(response)

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
