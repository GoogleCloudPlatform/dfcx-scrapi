"""Operations Resource functions."""

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
from typing import Dict

from google.api_core import operations_v1, grpc_helpers

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class Operations(scrapi_base.ScrapiBase):
    """Core class for Operations functions, primarily used to
    extract LRO information on long running jobs for CX.
    """

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope
        )

    @scrapi_base.api_call_counter_decorator
    def get_lro(self, lro: str):
        """Used to retrieve the status of LROs for Dialogflow CX.

        Args:
          lro: The Long Running Operation(LRO) ID in the following format
              'projects/<project-name>/locations/<locat>/operations/
                <operation-uuid>'

        Returns:
          Response status and payload from LRO
        """
        location = lro.split("/")[3]
        if location != "global":
            host = f"{location}-dialogflow.googleapis.com"
        else:
            host = "dialogflow.googleapis.com"

        channel = grpc_helpers.create_channel(
            host,
            credentials=self.creds
        )
        client = operations_v1.OperationsClient(channel)
        response = client.get_operation(lro)

        return response
