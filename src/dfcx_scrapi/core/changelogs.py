"""A collection of Methods to support the Change History feature in DFCX."""

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

import datetime
import logging

from typing import Dict

import pandas as pd

from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Changelogs(scrapi_base.ScrapiBase):
    """Tools class that contains methods to support Change History feature."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id=None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if agent_id:
            self.agent_id = agent_id

    @staticmethod
    def _validate_create_time(create_time: str):
        """Validates that create_time is in the ISO 8601 datetime format."""
        try:
            datetime.datetime.strptime(create_time, "YYYY-MM-DDThh:mm:ss.sZ")
        except ValueError as err:
            print("Create Time should be of format: 'YYYY-MM-DDThh:mm:ss.sZ'")
            raise ValueError from err
        else:
            return True

    @staticmethod
    def _validate_epoch_time(create_time_epoch_seconds: str):
        """Validates that create_time_epoch_seconds is a Unix Timestamp."""
        try:
            datetime.datetime.fromtimestamp(int(create_time_epoch_seconds))
        except ValueError as err:
            print("Create Time should be valid Unix Timestamp")
            raise ValueError from err
        else:
            return True

    @scrapi_base.api_call_counter_decorator
    def list_changelogs(self, agent_id: str = None, **kwargs):
        """Lists all Change History logs for a CX Agent.

        This method supports log filtering via **kwargs input. The filters
        currently supported are: user_email, resource, display_name, type,
        action, and create_time.
        See https://github.com/googleapis/python-dialogflow-cx/blob/main/
        google/cloud/dialogflowcx_v3beta1/types/changelog.py#L40 for
        pointers on filter examples

        Args:
          agent_id: the formatted CX Agent ID

        Returns:
          List of Change History logs
        """
        request = types.changelog.ListChangelogsRequest()
        request.parent = agent_id

        if kwargs.items():
            filter_list = []
            for key, value in kwargs.items():
                if key == "user_email":
                    filter_list.append(f'user_email = "{value}"')
                elif key == "resource":
                    filter_list.append(f'resource = "{value}"')
                elif key == "display_name":
                    filter_list.append(f'display_name = "{value}"')
                elif key == "type":
                    filter_list.append(f'type = "{value}"')
                elif key == "action":
                    filter_list.append(f'action = "{value}"')
                elif key == "create_time":
                    pass
                    # BUG (pmarlow): Time filters not being accepted properly
                    # TODO (pmarlow): implement input validation
                    # filter_list.append(f"create_time {value}")
                elif key == "create_time_epoch_seconds":
                    pass
                    # BUG (pmarlow): Time filters not being accepted properly
                    # TODO (pmarlow): implement input validation
                    # filter_list.append(
                    # f"\"create_time_epoch_seconds {value}\"")

            if len(filter_list) < 1:
                pass

            elif len(filter_list) == 1:
                filter_str = filter_list[0]
                request.filter = filter_str

            else:
                filter_str = filter_list[0]
                for item in filter_list[1:]:
                    filter_str += f" AND {item}"
                request.filter = filter_str

        client_options = self._set_region(agent_id)
        client = services.changelogs.ChangelogsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.list_changelogs(request)

        changelogs = []
        for page in response.pages:
            for log in page.changelogs:
                changelogs.append(log)

        return changelogs

    @scrapi_base.api_call_counter_decorator
    def get_changelog(self, changelog_id: str):
        """Get a single changelog resource object.

        Args:
          changelog_id: The ID of the changelog to get. Format: `projects/
            <Project ID>/locations/<Location ID>/agents/<Agent ID>/changelogs/
            <Changelog ID>`

        Returns:
          A single changelog object
        """
        request = types.changelog.GetChangelogRequest()
        request.name = changelog_id

        client_options = self._set_region(changelog_id)
        client = services.changelogs.ChangelogsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_changelog(request)

        return response

    def changelogs_to_dataframe(
        self, agent_id: str, email_pattern: str = "@google.com"
    ):
        """Format the output of list_changelogs into a Pandas Dataframe.

        Args:
          agent_id: the formatted CX Agent ID
          email_pattern: Provides a match filter that will determine the value
            of the 'user_type' column. Defaults to '@google.com'.

        Returns:
          The final dataframe output of the formatted logs
        """
        changelogs = self.list_changelogs(agent_id)

        if not changelogs:
            return print("No Change History Results for this Agent.")

        df = pd.DataFrame()

        for log in changelogs:
            if email_pattern in log.user_email:
                user_type = "Internal"
            elif log.type_ == "backups":
                user_type = "System"
            else:
                user_type = "External"

            log_data = pd.DataFrame(
                columns=[
                    "create_time",
                    "display_name",
                    "resource_type",
                    "action",
                    "user_email",
                    "user_type",
                    "resource_id",
                    "changelog_id",
                ],
                data=[
                    [
                        log.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                        log.display_name,
                        log.type_.title()[:-1],
                        log.action,
                        log.user_email,
                        user_type,
                        log.resource,
                        log.name,
                    ]
                ],
            )

            df = pd.concat([df, log_data], ignore_index=True)

        df = df.reset_index(drop=True)

        return df
