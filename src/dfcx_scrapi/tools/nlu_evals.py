"""A set of Utility methods to check resources stats on DFCX Agents."""

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

from typing import Dict
from dataclasses import dataclass

import logging
import datetime
import pandas as pd
import gspread

from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import agents
from dfcx_scrapi.core import flows
from dfcx_scrapi.core import pages
from dfcx_scrapi.core import intents
from dfcx_scrapi.core import conversation
from dfcx_scrapi.tools import dataframe_functions

pd.options.display.max_colwidth = 200

GLOBAL_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
INPUT_SCHEMA_COLUMNS = [
        "flow_display_name",
        "page_display_name",
        "utterance",
        "expected_intent",
        "expected_parameters",
        "description",
    ]

OUTPUT_SCHEMA_COLUMNS = [
    "flow_display_name",
    "page_display_name",
    "utterance",
    "expected_intent",
    "expected_parameters",
    "target_page",
    "match_type",
    "confidence",
    "parameters_set",
    "detected_intent",
    "agent_display_name",
    "description",
    "input_source"
    ]

SUMMARY_SCHEMA_COLUMNS = [
    "test_run_timestamp",
    "total_tests",
    "pass_count",
    "pass_rate",
    "no_match_count",
    "no_match_rate",
    "test_agent",
    "data_source"
    ]

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@dataclass
class Stats:
    """Dataclass for the summary stats."""
    no_match_count: int = 0
    no_match_rate: float = 0.0
    pass_count: int = 0
    pass_rate: float = 0.0
    test_agent: str = None
    data_source: str = None


class NluEvals(scrapi_base.ScrapiBase):
    """NLU Evaluation Class for Dialogflow CX Testing."""
    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict[str, str] = None,
        creds=None,
    ):

        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=GLOBAL_SCOPE
        )

        self.agent_id = agent_id
        self._sheets_client = self._build_sheets_client()

        self._a = agents.Agents(creds=self.creds)
        self._i = intents.Intents(creds=self.creds)
        self._f = flows.Flows(creds=self.creds)
        self._p = pages.Pages(creds=self.creds)
        self._dc = conversation.DialogflowConversation(
            creds_path=creds_path, agent_id=agent_id
        )
        self._dffx = dataframe_functions.DataframeFunctions(creds=self.creds)

    def _build_sheets_client(self):
        client = gspread.authorize(self.creds)

        return client

    def _calculate_stats(self, df: pd.DataFrame):
        """Calculate all the stats needed for the summary report."""
        stats = Stats()
        stats.no_match_count = (
            df[df.detected_intent == "NO_MATCH"]
            .groupby("detected_intent")
            .size()
            .sum()
        )
        stats.no_match_rate = stats.no_match_count / df.shape[0]
        stats.pass_count = (
            df[df.detected_intent == df.expected_intent]
            .groupby("detected_intent")
            .size()
            .sum()
        )
        stats.pass_rate = stats.pass_count / df.shape[0]
        stats.test_agent = df.agent_display_name.unique()[0]
        stats.data_source = df.input_source.unique()[0]

        return stats

    def _write_report_summary_to_sheets(
        self, df: pd.DataFrame, sheet_name: str, sheet_tab: str
    ):
        """Writes the output report summary to Google Sheets."""

        gsheet = self._sheets_client.open(sheet_name)
        sheet = gsheet.worksheet(sheet_tab)

        df["test_run_timestamp"] = df.test_run_timestamp.astype("str")

        sheet.append_row(
            df.values.flatten().tolist(), value_input_option="USER_ENTERED"
        )

    def _append_test_results_to_sheets(
        self, results: pd.DataFrame, sheet_name: str, sheet_tab: str
    ):
        """Adds results to an existing Google Sheet collection."""

        gsheet = self._sheets_client.open(sheet_name)
        sheet = gsheet.worksheet(sheet_tab)

        # Fixes an error that sometimes happens when trying to write parameters
        # to the sheet because they are formatted as objects
        result_list = results.values.tolist()
        result_list = [list(map(str, row)) for row in result_list]

        sheet.append_rows(result_list, value_input_option="USER_ENTERED")

    def _write_test_results_to_sheets(
        self, results: pd.DataFrame, sheet_name: str, sheet_tab: str
    ):
        """Writes the output result details to Google Sheets."""

        gsheet = self._sheets_client.open(sheet_name)
        sheet = gsheet.worksheet(sheet_tab)

        sheet.clear()

        self._dffx.dataframe_to_sheets(sheet_name, sheet_tab, results)

    def _clean_dataframe(self, df):
        """Various Dataframe cleaning functions."""
        df.columns = df.columns.str.lower()
        df = df.replace("Start Page", "START_PAGE")
        df.rename(
                columns={
                    "source": "description",
                },
                inplace=True,
            )

        # Validate input schema
        try:
            df = df[INPUT_SCHEMA_COLUMNS]
        except KeyError as err:
            raise UserWarning("Ensure your input data contains the following "\
                              f"columns: {INPUT_SCHEMA_COLUMNS}") from err

        df["agent_display_name"] = self._a.get_agent(self.agent_id).display_name

        return df

    def process_input_csv(self, input_file_path: str):
        """Process the input data in CSV format."""
        df = pd.read_csv(input_file_path)
        df = df.fillna("")
        df = self._clean_dataframe(df)
        df["input_source"] = input_file_path

        return df

    def process_input_google_sheet(self, gsheet_name: str, gsheet_tab: str):
        """Process the input data in Google Sheets format."""
        df = self._dffx.sheets_to_dataframe(gsheet_name, gsheet_tab)
        df = self._clean_dataframe(df)
        df["input_source"] = gsheet_tab

        return df

    def run_evals(self, df: pd.DataFrame, chunk_size: int = 300,
                  rate_limit: float = 10.0,
                  eval_run_display_name: str = "Evals"):
        """Run the full Eval dataset."""
        logsx = "-" * 10

        logging.info(f"{logsx} STARTING {eval_run_display_name} {logsx}")
        results = self._dc.run_intent_detection(
            test_set=df, chunk_size=chunk_size, rate_limit=rate_limit
        )

        # Reorder Columns
        results = results.reindex(columns=OUTPUT_SCHEMA_COLUMNS)

        # When a NO_MATCH occurs, the detected_intent field will be blank
        # this replaces with NO_MATCH string, which will allow for easier stats
        # calculation downstream
        results.detected_intent.replace({"": "NO_MATCH"}, inplace=True)

        logging.info(f"{logsx} {eval_run_display_name} COMPLETE {logsx}")

        return results

    def generate_report(self, df: pd.DataFrame,
                        report_timestamp: datetime.datetime
                        ):
        """Generates a summary stats report for most recent NLU Eval tests."""
        # Calc fields
        stats = self._calculate_stats(df)

        # Generate Dataframe format
        df_report = pd.DataFrame(
            columns=SUMMARY_SCHEMA_COLUMNS,
            data=[
                [
                    report_timestamp,
                    df.shape[0],
                    stats.pass_count,
                    stats.pass_rate,
                    stats.no_match_count,
                    stats.no_match_rate,
                    stats.test_agent,
                    stats.data_source,
                ]
            ],
        )

        return df_report

    def write_summary_to_file(self, df: pd.DataFrame, output_file: str):
        """Write summary output to a local CSV file."""
        report_timestamp = datetime.datetime.now()
        df_report = self.generate_report(df, report_timestamp)
        df_report.to_csv(output_file, index=False)

    def write_results_to_file(self, df: pd.DataFrame, output_file: str):
        df.to_csv(output_file, index=False)

    def write_results_to_sheets(self, df: pd.DataFrame, google_sheet_name: str,
                                full_output_tab: str,
                                summary_tab: str,
                                append=False):
        """Write summary and detailed output to Google Sheets."""
        report_timestamp = datetime.datetime.now()
        df_report = self.generate_report(df, report_timestamp)

        self._write_report_summary_to_sheets(
            df_report, google_sheet_name, summary_tab
        )

        if append:
            self._append_test_results_to_sheets(
                df, google_sheet_name, full_output_tab
            )

        else:
            self._write_test_results_to_sheets(
                df, google_sheet_name, full_output_tab
            )
