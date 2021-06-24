# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from dfcx_sapi.core.sapi_base import SapiBase
from typing import Dict, List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Operations(SapiBase):
    def __init__(
        self, creds_path: str = None, creds_dict: Dict = None, scope=False
    ):
        super().__init__(
            creds_path=creds_path, creds_dict=creds_dict, scope=scope
        )

    def get_lro(self, lro: str) -> Dict[str, str]:
        """Used to retrieve the status of LROs for Dialogflow CX.

        Args:
          lro: The Long Running Operation(LRO) ID in the following format
              'projects/<project-name>/locations/<locat>/operations/<operation-uuid>'

        Returns:
          response: Response status and payload from LRO

        """

        location = lro.split("/")[3]
        if location != "global":
            base_url = "https://{}-dialogflow.googleapis.com/v3beta1".format(
                location
            )
        else:
            base_url = "https://dialogflow.googleapis.com/v3beta1"

        url = "{0}/{1}".format(base_url, lro)
        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()
