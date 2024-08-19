"""Evaluation tooling for Generative features in Agent Builder and DFCX."""

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

from datetime import datetime
import logging

from ast import literal_eval
import numpy as np
import pandas as pd
from tqdm import tqdm
from typing import Dict, List, Any

from google.oauth2 import service_account

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.sessions import Sessions
from dfcx_scrapi.core.tools import Tools
from dfcx_scrapi.core.playbooks import Playbooks
from dfcx_scrapi.tools.dataframe_functions import DataframeFunctions
from dfcx_scrapi.tools.agent_response import AgentResponse
from dfcx_scrapi.tools.metrics import build_metrics

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Evaluations(ScrapiBase):
    """Evaluation tooling for Generative features in Agent Builder and DFCX."""

    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict[str, str] = None,
        creds: service_account.Credentials = None,
        sheet_name: str = None,
        metrics: List[str] = ["response_similarity"],
        debug: bool = False,
        generation_model: str = "gemini-1.5-flash-001",
        embedding_model: str = "text-embedding-004",
        playbooks_map: Dict[str, Any] = None,
        tools_map: Dict[str, Any] = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
        )

        if debug:
            logging.basicConfig(level=logging.DEBUG, force=True)
        if not debug:
            logging.basicConfig(level=logging.INFO, force=True)

        self.agent_id = agent_id
        self.sheet_name = sheet_name
        self.session_id = None
        self.metrics = metrics
        self.init_vertex(self.agent_id)

        self.s = Sessions(agent_id=self.agent_id, tools_map=tools_map)
        self.p = Playbooks(agent_id=self.agent_id, playbooks_map=playbooks_map)
        self.t = Tools(agent_id=self.agent_id, tools_map=tools_map)
        self.dffx = DataframeFunctions(
            creds_path=creds_path, creds_dict=creds_dict, creds=creds
        )
        self.ar = AgentResponse()

        self.generation_model = self.model_setup(generation_model)
        self.embedding_model = self.model_setup(embedding_model)

        self.required_columns = [
            "eval_id",
            "action_id",
            "action_input",
            "action_input_parameters",
            "tool_action",
        ]

        self.metrics = build_metrics(metrics, self.embedding_model)


    @staticmethod
    def prep_incoming_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Prepares incoming dataframe for evals"""

        for col in ["agent_utterance", "agent_response"]:
            assert col in df.columns.to_list(), (
                f"Dataset is missing column `{col}`. Please update dataset "
                f"columns."
            )

        return df


    @staticmethod
    def get_matching_list_idx(a, b):
        """Helper method to find index pairs in the dataset.

        Compare lists and find the idx from list a where each element in b fits.
        This is used to determine exactly where the utterance or tool pairs
        exist in a given dataframe. The pairs are then used to determine where
        to write the results after the online inference is complete and the
        evals have been computed.
        """
        if not b:
            return [(a[0], [])]  # if b is empty, return

        result = []
        i, j = 0, 0

        current_b = []
        while i < len(a) and j < len(b):
            if a[i] < b[j]:
                current_a = a[i]
                if len(current_b) > 0:
                    result.append((a[i - 1], current_b))
                    current_b = []
                i += 1
            elif a[i] > b[j]:
                current_b.append(b[j])
                j += 1

        # if we're at end of list a, and still have list b
        # extend the remainder of b
        if i == len(a):
            current_b.extend(b[j:])
            result.append((current_a, current_b))

        # if we're at the end of list b, then append our current positions
        if j == len(b):
            result.append((current_a, current_b))

        return result

    @staticmethod
    def pair_utterances(df: pd.DataFrame) -> pd.DataFrame:
        "Identifies pairings of user_utterance and agent_utterance by eval_id."
        df["utterance_pair"] = pd.Series(dtype="string")
        grouped = df.groupby("eval_id")

        for _, group in grouped:
            user = group[
                group["action_type"] == "User Utterance"
            ].index.tolist()
            agent = group[
                group["action_type"] == "Agent Response"
            ].index.tolist()
            pairs = list(
                zip(user, agent)
            )

            # Create pairs of user/agent row indices
            for pair in pairs:
                df.loc[pair[0], "utterance_pair"] = str(pair[1])

        return df

    @staticmethod
    def clean_outputs(df: pd.DataFrame) -> pd.DataFrame:
        """Clean final output dataframe."""
        # drop cols used for response mapping
        df = df.drop(columns=["utterance_pair", "tool_pair", "playbook_pair"])
        value_map = {}
        for col, dtype in zip(df.columns, df.dtypes):
            if dtype in ["string", "object"]:
                value_map[col] = ""
            elif dtype == "float64":
                value_map[col] = np.nan

        df.fillna(value=value_map, inplace=True)

        return df

    @staticmethod
    def process_playbook_invocations(
            responses: List[str],
            index: int,
            row: pd.Series,
            df: pd.DataFrame) -> pd.DataFrame:
        if row["playbook_pair"] in [None, "", "NaN", "nan"]:
            playbook_index_list = [index]
        else:
            playbook_index_list = literal_eval(row["playbook_pair"])

        for idx in playbook_index_list:
            playbook = responses.pop(0)
            df.loc[int(idx), ["res_playbook_name"]] = [
                playbook["playbook_name"]
            ]

        return df

    @staticmethod
    def process_tool_invocations(
        tool_responses: List[str],
        index: int,
        row: pd.Series,
        df: pd.DataFrame) -> pd.DataFrame:
        # Check if our golden contained a tool_idx or wasn't
        # expecting tools
        if row["tool_pair"] in [None, "", "NaN", "nan"]:
            tool_index_list = [index]
        else:
            tool_index_list = literal_eval(row["tool_pair"])

        for idx in tool_index_list:
            tool = tool_responses.pop(0)
            df.loc[
                int(idx),
                [
                    "res_tool_name",
                    "res_tool_action",
                    "res_input_params",
                    "res_output_params",
                ],
            ] = [
                tool["tool_name"],
                tool["tool_action"],
                tool["input_params"],
                tool["output_params"],
            ]

        return df

    def pair_tool_calls(self, df: pd.DataFrame) -> pd.DataFrame:
        "Identifies pairings of agent_utterance/tool_invocation by eval_id."
        df["tool_pair"] = pd.Series(dtype="string")
        grouped = df.groupby("eval_id")

        for _, group in grouped:
            user = group[
                group["action_type"] == "User Utterance"
            ].index.tolist()
            tool_list = group[
                group["action_type"] == "Tool Invocation"
            ].index.tolist()

            pairs = self.get_matching_list_idx(
                user, tool_list
            )

            # Create pairs of user/tool_list row indices
            for pair in pairs:
                df.loc[pair[0], "tool_pair"] = str(pair[1])

        return df

    def pair_playbook_calls(self, df: pd.DataFrame) -> pd.DataFrame:
        "Identifies pairings of agent_utterance/playbook_invocation by eval_id."
        df["playbook_pair"] = pd.Series(dtype="string")
        grouped = df.groupby("eval_id")

        for _, group in grouped:
            user = group[
                group["action_type"] == "User Utterance"
            ].index.tolist()
            playbook_list = group[
                group["action_type"] == "Playbook Invocation"
            ].index.tolist()

            pairs = self.get_matching_list_idx(
                user, playbook_list
            )

            # Create pairs of user/playbook_list row indices
            for pair in pairs:
                df.loc[pair[0], "playbook_pair"] = str(pair[1])

        return df


    def validate_input_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate input columns"""
        input_cols = set(df.columns.to_list())
        req_cols = set(self.required_columns)

        if not req_cols.issubset(input_cols):
            missing_cols = req_cols - input_cols
            raise ValueError(
                f"Missing columns: {missing_cols}. Required Columns are: "
                f"{self.required_columns}"
            )

        return df

    def check_existing_tab_name(
        self, sheet_name: str, results_tab: str
    ) -> bool:
        """Check to see if tab already exists."""
        sheet = self.dffx.sheets_client.open(sheet_name)
        existing_sheet = False
        worksheets = sheet.worksheets()
        for worksheet in worksheets:
            if worksheet.title == results_tab:
                existing_sheet = True

        return existing_sheet

    def create_sheet_tab(self, df: pd.DataFrame, results_tab: str):
        sheet = self.dffx.sheets_client.open(self.sheet_name)
        sheet.add_worksheet(results_tab, rows=df.shape[0], cols=df.shape[1])

    def write_eval_results_to_sheets(
        self, df: pd.DataFrame, sheet_name: str, results_tab: str = None
    ):
        tab_name_exists = self.check_existing_tab_name(sheet_name, results_tab)
        if results_tab and not tab_name_exists:
            self.create_sheet_tab(df, results_tab)
            self.dffx.dataframe_to_sheets(sheet_name, results_tab, df)

        elif results_tab and tab_name_exists:
            self.dffx.dataframe_to_sheets(sheet_name, results_tab, df)

        # auto generate a tab name and create it for the user
        else:
            today = datetime.today().strftime("%Y-%m-%d")
            results_tab = f"{today}-Eval Run"
            if not self.check_existing_tab_name(sheet_name, results_tab):
                self.create_sheet_tab(df, results_tab)

            self.dffx.dataframe_to_sheets(sheet_name, results_tab, df)

    def sheets_to_dataframe(
        self, sheet_name: str, sheet_tab: str
    ) -> pd.DataFrame:
        df = self.dffx.sheets_to_dataframe(sheet_name, sheet_tab)

        # Store sheet name for later use
        self.sheet_name = sheet_name

        # Check for action_id column, if none exists
        # add and assume all single turn queries
        if "action_id" not in df.columns.to_list():
            df["action_id"] = 1

        df["action_id"] = df["action_id"].astype(int)
        self.validate_input_columns(df)
        # TODO (pmarlow): self.validate_input_values(df)

        df = self.pair_utterances(df)
        df = self.pair_tool_calls(df)
        df = self.pair_playbook_calls(df)

        # fill remaining NA with empty string
        df.fillna("", inplace=True)

        return df

    def append_test_results_to_sheets(
        self, results: pd.DataFrame, sheet_name: str, sheet_tab: str
    ):
        client = self.dffx.sheets_client
        gsheet = client.open(sheet_name)
        sheet = gsheet.worksheet(sheet_tab)

        sheet.append_rows(
            results.values.tolist(), value_input_option="USER_ENTERED"
        )

    def run_detect_intent_queries(self, df: pd.DataFrame) -> pd.DataFrame:
        for index, row in tqdm(df.iterrows(), total=df.shape[0]):
            data = {}
            if row["action_id"] == 1:
                self.session_id = self.s.build_session_id(self.agent_id)
                data["session_id"] = self.session_id
                data["agent_id"] = self.agent_id

            else:
                data["session_id"] = self.session_id
                data["agent_id"] = self.agent_id

            # If the incoming dataset has an empty value in the row, skip it
            # this is because we build the incoming dataset with multi-row
            # actions to be able to evaluate `inner-loop` tasks
            if row["action_type"] != "User Utterance":
                continue

            res = self.s.detect_intent(
                self.agent_id, self.session_id, row["action_input"]
            )

            # Add data to the existing row
            df.loc[index, ["session_id", "agent_id"]] = [
                data["session_id"],
                data["agent_id"],
            ]
            text_res = self.ar._extract_text(res)
            utterance_idx = int(row["utterance_pair"])
            df.loc[utterance_idx, ["agent_response"]] = [text_res]

            # Handle Play Invocations
            playbook_responses = self.s.collect_playbook_responses(res)
            if len(playbook_responses) > 0:
                df = self.process_playbook_invocations(
                    playbook_responses, index, row, df
                )

            # Handle Tool Invocations
            tool_responses = self.s.collect_tool_responses(res)
            if len(tool_responses) > 0:
                df = self.process_tool_invocations(
                    tool_responses, index, row, df
                )

        return df

    def run_evals(self, df: pd.DataFrame) -> pd.DataFrame:
        print("Starting Evals...")

        for metric in self.metrics:
           df = pd.concat([df, metric.run(df)], axis=1)

        return df

    def run_query_and_eval(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.validate_input_columns(df)
        df = self.run_detect_intent_queries(df)
        df = self.run_evals(df)
        df = self.clean_outputs(df)

        return df
