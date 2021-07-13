"""A collection of Methods to support the Change History feature in DFCX."""
# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
from typing import Dict

import numpy as np
import pandas as pd
import requests

from dfcx_sapi.core.sapi_base import SapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class ChangeHistory(SapiBase):
    """Tools class that contains methods to support Change History feature."""
    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds = None,
        scope = False,
        agent_id = None
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope
        )

        if agent_id:
            self.agent_id = agent_id

    def get_change_history(self, agent_id: str = None):
        """Extract the Change History log for a single DFCX Agent.

        Args:
          agent_id, the formatted CX Agent ID

        Returns:
          logs, a List of logs from the Agent ID
        """
        if not agent_id:
            agent_id = self.agent_id

        location = agent_id.split("/")[3]
        if location != "global":
            base_url = "https://{}-dialogflow.googleapis.com/v3alpha1".format(
                location
            )
        else:
            base_url = "https://dialogflow.googleapis.com/v3alpha1"

        url = "{0}/{1}/changelogs".format(base_url, agent_id)

        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        res = results.json()

        logs = []
        for log in res["changelogs"]:
            logs.append(log)

        next_token = res.get("nextPageToken",None)

        while next_token is not None:
            results = requests.get(
                url, headers=headers, params={"page_token": next_token}
            )
            res = results.json()
            for log in res["changelogs"]:
                logs.append(log)

            if "nextPageToken" in res:
                next_token = res["nextPageToken"]
            else:
                next_token = None
                print("All done!")

        return logs

    def change_history_to_dataframe(self, agent_id):
        """Format the output of get_change_history into a Pandas Dataframe.

        Args:
          agent_id, the formatted CX Agent ID

        Returns:
          final_dataframe, the final dataframe output of the formatted logs
        """
        change_logs = self.get_change_history(agent_id)
        final_dataframe = pd.DataFrame.from_records(data=change_logs)

        final_dataframe["createTime"] = pd.to_datetime(
            final_dataframe["createTime"], infer_datetime_format=True
        )  # coerce datetime from CX
        final_dataframe["userType"] = np.where(
            final_dataframe.userEmail.str.contains("@google.com"),
            "Internal", "External")  # determine int/ext user

        # TODO: functions to determine which Flow this resource belongs to

        return final_dataframe
