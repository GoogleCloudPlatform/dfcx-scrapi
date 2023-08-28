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

import logging
import datetime
import pandas as pd
import gspread

from tabulate import tabulate

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

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class EvalTesting(scrapi_base.ScrapiBase):
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

        self._a = agents.Agents(creds=self.creds)
        self._i = intents.Intents(creds=self.creds)
        self._f = flows.Flows(creds=self.creds)
        self._p = pages.Pages(creds=self.creds)
        self._dc = conversation.DialogflowConversation(
            creds_path=creds_path, agent_id=agent_id
        )
        self._dffx = dataframe_functions.DataframeFunctions(creds=self.creds)

    @staticmethod
    def _create_schema(df):
        """Reusable DataFrame schema method."""
        df = df[
            [
                "flow_display_name",
                "page_display_name",
                "utterance",
                "expected_intent",
                "expected_parameters",
                "agent_display_name",
                "data_source",
                "sheet_source",
            ]
        ]

        return df

    def _clean_dataframe(self, df):
        """Various Dataframe cleaning functions."""

        df.columns = df.columns.str.lower()
        df = df.replace("Start Page", "START_PAGE")
        df.rename(
                columns={
                    "source": "data_source",
                },
                inplace=True,
            )

        df = self._add_agent_display_name_column(df)
        df = self._create_schema(df)

        return df

    def _add_agent_display_name_column(self, df):
        """Add the Agent Display name to the output dataframe."""

        df["agent_display_name"] = self._a.get_agent(self.agent_id).display_name

        return df

    def _build_sheets_client(self):
        client = gspread.authorize(self.creds)

        return client

    def format_preprocessed_conversation_logs(
        self,
        input_format: str = "gsheet",
        gsheet_name: str = None,
        gsheet_tab: str = None,
        file_path: str = None,
    ) -> pd.DataFrame:
        """Transforms preprocssed data to dataframe for eval testing.

        The input for this method should be a Google Sheet that contains the
        following columns:
            flow_display_name: The name of the Dialogflow CX Flow
            utterance: The user utterance to test
            page_display_name: The display name of the Dialogflow CX page that
              the eval test should start on. If not provided, START_PAGE is
              assumed.
            expected_intent: The Intent Display Name that is expected to trigger
              for the given eval test.
            expected_parameters: Optional parameters expected to be collected
              for the given eval test.
            source: Optional source of the eval dataa.

        Args:
            input_format: The input format of the file. ONEOF: `csv`, `gsheet`
            gsheet_name: Title of the Google Sheet where the data lives
            gsheet_tab: Title of the Tab on the Sheet where the data lives
            file_path: Optional file path if `csv` format is used
            start_page_flow: In the case of a special page like START_PAGE, when no
              additional flow information is provided, the script will default to
              this Flow Display Name. Default value is Default Start Flow.

        Returns:
            A formatted DataFrame ready to be used for multithreaded testing
        """
        if input_format == "csv":
            if not file_path:
                raise ValueError(
                    "Must provide file_path with `csv` format."
                )
            df = pd.read_csv(
                file_path,
                usecols=[
                    "flow_display_name",
                    "utterance",
                    "page_display_name",
                    "expected_intent",
                    "expected_parameters",
                    "source"
                ],
            )

        elif input_format == "gsheet":
            if not gsheet_name and not gsheet_tab:
                raise ValueError(
                    "Must provide `gsheet_name` and `gsheet_tab` with `gsheet` "
                        "format."
                )

            df = self._dffx.sheets_to_dataframe(gsheet_name, gsheet_tab)

            df["sheet_source"] = gsheet_tab
            df = self._clean_dataframe(df)

        return df

    def get_flow_display_name_mapping(
        self,
        df: pd.DataFrame,
        agent_id: str,
        start_page_flow: str = "Default Start Flow",
    ) -> pd.DataFrame:
        """Retrieve Page/Flow Display Name Map.

        If a Flow Display Name is not provided, this method will attempt to
        infer the correct Flow Display Name basd on the provided Page Display
        Name. If a Flow Display Name is already provided, the method will honor
        this user input.
        """

        flows_map = self._f.get_flows_map(agent_id)

        all_pages = {}
        all_pages[
            "START_PAGE"
        ] = start_page_flow  # Case where source_page is the first turn
        for flow in flows_map:
            temp_pages = list(self._p.get_pages_map(flow, reverse=True).keys())
            for page in temp_pages:
                all_pages[page] = flows_map[flow]

        # Fill blank flow names with the inferred one from the list of pages
        # Otherwise use the user specified flow name
        # NOTE: If multiple pages with the same name exist across different
        # flows and Flow Display Name is not provided, the inferred Flow could
        # be incorrect as the map will pick the first Flow encountered.
        df["flow_display_name"] = df.apply(
            lambda row: row["flow_display_name"]
            if all([
                row["flow_display_name"] != "",
                row["flow_display_name"] is not None
                ])
            else all_pages[row["page_display_name"]],
            axis=1,
        )

        return df

    def run_tests(
        self, df: pd.DataFrame, chunk_size: int = 300, rate_limit: float = 20
    ) -> pd.DataFrame:
        """Tests a set of utterances for intent detection against a CX Agent.

        This function uses Python Threading to run tests in parallel to
        expedite intent detection testing for Dialogflow CX agents. The default
        quota for Text requests/min is 1200. Ref:
          https://cloud.google.com/dialogflow/quotas#table
        """

        results = self._dc.run_intent_detection(
            test_set=df, chunk_size=chunk_size, rate_limit=rate_limit
        )

        if "agent_display_name" in df.columns:
            temp_column = results.pop("agent_display_name")
            results.insert(len(results.columns), "agent_display_name", temp_column)

        if "data_source" in df.columns:
            temp_column = results.pop("data_source")
            results.insert(len(results.columns), "data_source", temp_column)

        if "sheet_source" in df.columns:
            temp_column = results.pop("sheet_source")
            results.insert(len(results.columns), "sheet_source", temp_column)

        # When a NO_MATCH occurs, the detected_intent field will be blank
        # this replaces with NO_MATCH string, which will allow for easier stats
        # calculation downstream
        results.detected_intent.replace({'': 'NO_MATCH'}, inplace=True)

        return results

    def generate_report(
        self,
        results: pd.DataFrame,
        report_timestamp: datetime.datetime,
    ):
        """Generates a printable report and dataframe.

        Args:
            results: Input dataframe of testing results from run_tests method.

        Returns:
            A dataframe with report summary stats.
        """
        # Calc fields
        failed_df = results[results.detected_intent != results.expected_intent]
        no_match_count = (
            results[results.detected_intent == "NO_MATCH"]
            .groupby("detected_intent")
            .size()
            .sum()
        )
        no_match_df = results[results.detected_intent == "NO_MATCH"]
        no_match_rate = no_match_count / results.shape[0]
        pass_count = (
            results[results.detected_intent == results.expected_intent]
            .groupby("detected_intent")
            .size()
            .sum()
        )
        pass_rate = pass_count / results.shape[0]
        timestamp = report_timestamp
        test_agent = results.agent_display_name.unique()[0]
        flow_display_name = results.flow_display_name.unique()[0]
        data_source = results.sheet_source.unique()[0]

        # Get Failure list of Utterance / Page pairs
        failure_list = []
        for _, row in failed_df.iterrows():
            failure_list.append(
                [
                    row["utterance"],
                    row["flow_display_name"],
                    row["page_display_name"],
                    row["expected_intent"],
                    row["detected_intent"],
                    row["expected_parameters"],
                    row["parameters_set"],
                ]
            )

        # Generate Dataframe format
        df_report = pd.DataFrame(
            columns=[
                "test_run_timestamp",
                "total_tests",
                "pass_count",
                "pass_rate",
                "no_match_count",
                "no_match_rate",
                "test_agent",
                "flow_display_name",
                "data_source",
            ],
            data=[
                [
                    timestamp,
                    results.shape[0],
                    pass_count,
                    pass_rate,
                    no_match_count,
                    no_match_rate,
                    test_agent,
                    flow_display_name,
                    data_source,
                ]
            ],
        )

        # Printable Report Format
        print("---------- RESULTS ----------")
        print(f"Test Agent: {test_agent}")
        print(f"Total Tests: {results.shape[0]}")
        print(f"Pass Count: {pass_count}")
        print(f"Pass Rate: {pass_rate:.2%}")
        print(f"No Match Count: {no_match_count}")
        print(f"No Match Rate: {no_match_rate:.2%}")
        print(f"Test Run Timestamp: {timestamp}")
        print(f"Test Set Data Source: {data_source}")
        print("\n")

        return df_report

    def write_report_summary_to_log(
        self, df: pd.DataFrame, sheet_name: str, sheet_tab: str
    ):
        """Writes the output report summary to Google Sheets."""

        client = self._build_sheets_client()
        gsheet = client.open(sheet_name)
        sheet = gsheet.worksheet(sheet_tab)

        df["test_run_timestamp"] = df.test_run_timestamp.astype("str")

        sheet.append_row(
            df.values.flatten().tolist(), value_input_option="USER_ENTERED"
        )

    def write_test_results_to_sheets(
        self, results: pd.DataFrame, sheet_name: str, sheet_tab: str
    ):
        """Writes the output result details to Google Sheets."""

        client = self._build_sheets_client()
        gsheet = client.open(sheet_name)
        sheet = gsheet.worksheet(sheet_tab)

        sheet.clear()

        self._dffx.dataframe_to_sheets(sheet_name, sheet_tab, results)

    def append_test_results_to_sheets(
        self, results: pd.DataFrame, sheet_name: str, sheet_tab: str
    ):
        """Adds results to an existing Google Sheet collection."""

        client = self._build_sheets_client()
        gsheet = client.open(sheet_name)
        sheet = gsheet.worksheet(sheet_tab)

        # Fixes an error that sometimes happens when trying to write parameters
        # to the sheet because they are formatted as objects
        result_list = results.values.tolist()
        result_list = [list(map(str, row)) for row in result_list]

        sheet.append_rows(result_list, value_input_option="USER_ENTERED")

    def run_evals(self, google_sheet_name: str, google_sheet_tab: str,
                  google_sheet_output_tab: str, google_sheet_summary_tab: str,
                  eval_run_display_name: str = "Evals", append=False):
        """Run the full Eval dataset."""
        logsx = "-" * 10

        logging.info(f"{logsx} STARTING {eval_run_display_name} {logsx}")

        report_timestamp = datetime.datetime.now()

        df = self.format_preprocessed_conversation_logs(
            "gsheet", google_sheet_name, google_sheet_tab
        )
        df = self.get_flow_display_name_mapping(df, self.agent_id)
        df_results = self.run_tests(df)
        df_report = self.generate_report(df_results, report_timestamp)

        self.write_report_summary_to_log(
            df_report, google_sheet_name, google_sheet_summary_tab
        )

        if append:
            self.append_test_results_to_sheets(
                df_results, google_sheet_name, google_sheet_output_tab
            )

        else:
            self.write_test_results_to_sheets(
                df_results, google_sheet_name, google_sheet_output_tab
            )
        logging.info(f"{logsx} {eval_run_display_name} COMPLETE {logsx}")

        return df_results
