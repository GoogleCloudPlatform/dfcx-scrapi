"""Vertex AI Conversation scraper class."""

# Copyright 2024 Google LLC
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
import json
import re
from typing import Any, Union

import gspread
import pandas as pd
from google.oauth2 import service_account
from tqdm.auto import tqdm

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.scrapi_base import ScrapiBase, retry_api_call
from dfcx_scrapi.core.sessions import Sessions
from dfcx_scrapi.tools.agent_response import AgentResponse

MAX_RETRIES = 5
INPUT_SCHEMA_REQUIRED_COLUMNS = [
    "conversation_id",
    "turn_index",
    "query",
    "expected_answer",
    "expected_uri",
    "user_metadata",
    "parameters"
]

def load_spreadsheet(
        sheet_url: str, worksheet_name: str, credentials: Any
        ) -> pd.DataFrame:
    """Loads the content of a spreadsheet into pandas DataFrame."""
    sheets_client = gspread.authorize(credentials)
    sheet = sheets_client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)

    return pd.DataFrame(worksheet.get_all_records())

class DataStoreScraper(ScrapiBase):
    """Vertex AI Conversation scraper class."""

    def _extract_url_part(cls, url, pattern):
        pattern_match = pattern.search(url)
        if not pattern_match:
            raise ValueError(f"Invalid url: {url}")

        return pattern_match.group(1)

    @classmethod
    def from_url(
        cls,
        agent_url: str,
        creds: service_account.Credentials = None,
        language_code: str = "en"):
        match = re.search(
            r'projects/[^/]+/locations/[^/]+/agents/[^/]+', agent_url
            )
        if match:
            agent_id = match.group(0)
        else:
            raise ValueError(f"Invalid url: {agent_url}")

        return cls(
            agent_id=agent_id,
            language_code=language_code,
            creds=creds,
        )

    def __init__(
        self,
        agent_id: str,
        language_code: str = "en",
        creds_path: str = None,
        creds_dict: dict[str, str] = None,
        creds=None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
        )

        self.agent_id = agent_id
        self.language_code = language_code

        self.sessions = Sessions(agent_id=self.agent_id)
        self.agents = Agents(creds=self.creds)

    @classmethod
    def _extract_url_part(cls, url, pattern):
        pattern_match = pattern.search(url)
        if not pattern_match:
            raise ValueError(f"Invalid url: {url}")
        return pattern_match.group(1)

    def validate_queryset(self, queryset: pd.DataFrame) -> None:
        "Validates the queryset and raises exception in case of invalid input."
        # validate input schema
        try:
            queryset[INPUT_SCHEMA_REQUIRED_COLUMNS]
        except KeyError as err:
            raise UserWarning(
                "Ensure your input data contains the following columns:"
                f" {INPUT_SCHEMA_REQUIRED_COLUMNS}"
            ) from err

        # validate if conversationd_id and turn_id is unique identifier
        if not (
            queryset["conversation_id"].astype(str)
            + "_"
            + queryset["turn_index"].astype(str)
        ).is_unique:
            raise UserWarning(
                "Ensure that 'conversation_id' and 'turn_index' are unique "
                "identifiers"
            )

        # validate turn_index
        try:
            queryset["turn_index"].astype(int)
        except ValueError as err:
            raise UserWarning(
                "Ensure that 'turn_index' is set as integer"
            ) from err

        if not queryset["turn_index"].astype(int).gt(0).all():
            raise UserWarning("Ensure that 'turn_index' is in [1, inf)")

    def setup_queryset(self, queryset: pd.DataFrame) -> pd.DataFrame:
        """Various Dataframe validation and cleaning functions."""
        queryset = queryset.rename(
            {column: column.lower() for column in queryset.columns}
        )

        self.validate_queryset(queryset)

        queryset["turn_index"] = queryset["turn_index"].astype(int)
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

        # adding timestamp and agent display name so they can be used as a multi
        # index
        queryset["scrape_timestamp"] = timestamp.isoformat()
        agent_display_name = self.agents.get_agent(self.agent_id).display_name
        queryset["agent_display_name"] = agent_display_name

        queryset = self._create_session_ids(queryset)

        # if the conversation_id can be converted to int then sorting can be
        # done numerically instead of alphabetically
        try:
            queryset["conversation_id"] = queryset["conversation_id"].astype(
                int
            )
        except ValueError:
            pass

        queryset = queryset.sort_values(
            by=["conversation_id", "turn_index"], ascending=True
        )

        return queryset

    def _create_session_ids(self, queryset: pd.DataFrame) -> pd.DataFrame:
        """Creates a unique session id for each conversation_id."""
        sessions = []
        for conversation_id in queryset["conversation_id"].unique():
            sessions.append(
                {
                    "conversation_id": conversation_id,
                    "session_id": self.sessions.build_session_id(self.agent_id),
                }
            )
        sessions_df = pd.DataFrame(sessions)
        return queryset.merge(sessions_df, on="conversation_id", how="left")

    @retry_api_call([i**2 for i in range(MAX_RETRIES)])
    def scrape_detect_intent(
        self,
        query: str,
        session_id: Union[str, None] = None,
        user_metadata: Union[str, None] = None,
        parameters: Union[str, None] = None
    ) -> AgentResponse:
        if session_id is None:
            session_id = self.sessions.build_session_id(self.agent_id)

        if user_metadata:
            try:
                if isinstance(user_metadata, str):
                    user_metadata = json.loads(user_metadata)
            except ValueError as err:
                raise UserWarning("Invalid user metadata") from err

        if parameters:
            try:
                if isinstance(parameters, str):
                    parameters = json.loads(parameters)
            except ValueError as err:
                raise UserWarning("Invalid parameters") from err

        response = self.sessions.detect_intent(
            agent_id=self.agent_id,
            session_id=session_id,
            text=query,
            language_code=self.language_code,
            end_user_metadata=user_metadata,
            populate_data_store_connection_signals=True,
            parameters=parameters
        )

        ar = AgentResponse()
        ar.from_query_result(response._pb)

        return ar

    def run(
        self, queryset: pd.DataFrame, flatten_response: bool = True
    ) -> pd.DataFrame:
        "Runs through each query and concatenates responses to the queryset."
        queryset = self.setup_queryset(queryset)
        progress_bar = tqdm(desc="Scraping queries", total=len(queryset))

        def scrape(row):
            result = self.scrape_detect_intent(
                query=row["query"],
                session_id=row["session_id"],
                user_metadata=row["user_metadata"],
                parameters=row["parameters"]
            )
            progress_bar.update()

            return result

        queryset["query_result"] = queryset.apply(scrape, axis=1)

        return queryset
