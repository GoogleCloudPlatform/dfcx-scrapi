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

import logging
from ast import literal_eval
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from google.cloud.dialogflowcx_v3beta1 import types
from google.oauth2 import service_account
from tqdm import tqdm

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.conversation_history import ConversationHistory
from dfcx_scrapi.core.playbooks import Playbooks
from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.sessions import Sessions
from dfcx_scrapi.core.tools import Tools
from dfcx_scrapi.tools.agent_response import AgentResponse
from dfcx_scrapi.tools.dataframe_functions import DataframeFunctions
from dfcx_scrapi.tools.metrics import build_metrics

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

@dataclass
class Interaction:
    actions: List[types.Action] = field(default_factory=list)
    generative_info: types.GenerativeInfo = None
    playbook_invocation: str = None
    query: str = None
    query_result: types.QueryResult = None
    responses: List = field(default_factory=list)
    tool_calls: List = field(default_factory=list)

    def __post_init__(self):
        if hasattr(self.query_result, "generative_info"):
            self.generative_info = self.query_result.generative_info
            self.actions = self.generative_info.action_tracing_info.actions

class Evaluations(ScrapiBase):
    """Evaluation tooling for Generative features in Agent Builder and DFCX."""

    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict[str, str] = None,
        creds: service_account.Credentials = None,
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

        self.agent_id = agent_id
        self.session_id = None

        print("Initializing Vertex AI...")
        self.init_vertex(self.agent_id)
        self.sessions_client = Sessions(
            agent_id=self.agent_id, tools_map=tools_map, creds=self.creds)
        self.playbooks_client = Playbooks(
            agent_id=self.agent_id,
            playbooks_map=playbooks_map, creds=self.creds)
        self.tools_client = Tools(
            agent_id=self.agent_id, tools_map=tools_map, creds=self.creds)
        self.ar = AgentResponse()
        self.ch = ConversationHistory(agent_id=self.agent_id, creds=self.creds)

        self.tools_map = None
        self.playbooks_map = None
        self.action_counter = 1

        self.generation_model = self.model_setup(generation_model)
        self.embedding_model = self.model_setup(embedding_model)

        self.user_input_metrics = metrics
        self.metrics = build_metrics(
            metrics=self.user_input_metrics,
            generation_model=self.generation_model,
            embedding_model=self.embedding_model
            )
        self.unexpected_rows = []

        if debug:
            logging.basicConfig(level=logging.DEBUG, force=True)
        if not debug:
            logging.basicConfig(level=logging.ERROR, force=True)

    @staticmethod
    def clean_outputs(df: pd.DataFrame) -> pd.DataFrame:
        """Clean final output dataframe."""
        # drop cols used for response mapping
        df = df.drop(columns=[
            "utterance_pair",
            "tool_pair",
            "playbook_pair",
            "flow_pair"
            ])
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
            df.loc[int(idx), "res_playbook_name"] = playbook["playbook_name"]

        return df

    @staticmethod
    def process_flow_invocations(
        responses: List[str],
        index: int,
        row: pd.Series,
        df: pd.DataFrame) -> pd.DataFrame:
        if row["flow_pair"] in [None, "", "NaN", "nan"]:
            flow_index_list = [index]
        else:
            flow_index_list = literal_eval(row["flow_pair"])

        for idx in flow_index_list:
            flow = responses.pop(0)
            df.loc[int(idx), "res_flow_name"] = flow["flow_name"]

        return df

    @staticmethod
    def process_tool_invocations(
        tool_responses: List[Dict],
        index: int,
        row: pd.Series,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Process tool invocations and map them
        to the correct rows in the dataframe."""
        # Get the list of indices where tool responses should be mapped
        if row["tool_pair"] in [None, "", "NaN", "nan"]:
            tool_index_list = [index]
        else:
            tool_index_list = literal_eval(row["tool_pair"])

        # Process each tool response and map it to the corresponding index
        for i, idx in enumerate(tool_index_list):
            if i < len(tool_responses):
                tool = tool_responses[i]
                df.loc[int(idx), "res_tool_name"] = (
                    tool.get("tool_name", "")
                )
                df.loc[int(idx), "res_tool_action"] = (
                    tool.get("tool_action", "")
                )
                df.loc[int(idx), "res_input_params"] = (
                    str(tool.get("input_params", {}))
                )
                df.loc[int(idx), "res_output_params"] = (
                    str(tool.get("output_params", {}))
                )
            else:
                df.loc[int(idx), [
                    "res_tool_name",
                    "res_tool_action",
                    "res_input_params",
                    "res_output_params"
                    ]] = [
                    "NO_TOOL_RESPONSE",
                    "NO_TOOL_RESPONSE",
                    "NO_TOOL_RESPONSE",
                    "NO_TOOL_RESPONSE"
                ]

        return df

    @staticmethod
    def append_row(
        df_rows: List[pd.Series],
        eval_id: str,
        action_id: str,
        action_type: str,
        action_input: Any,
        action_input_parameters: str = "",
        tool_action: str = "",
        notes: str = ""):
        df_rows.append({
            'eval_id': eval_id,
            'action_id': action_id,
            'action_type': action_type,
            'action_input': action_input,
            'action_input_parameters': action_input_parameters,
            'tool_action': tool_action,
            'notes': notes
        })

    def parse_tool_use_from_conversation_history(
            self,
            tool_use: types.ToolUse) -> Dict[str, Any]:
        tool_name = self.tools_map.get(tool_use.tool, None)
        input_params = self.recurse_proto_marshal_to_dict(
            tool_use.input_action_parameters)

        # The DFCX proto for input params will add an extra top level key that
        # needs to be removed before writing to our output sheet. This only
        # applies to input_action_parameters
        if len(input_params) == 1 and input_params.get("", None):
            input_params = input_params.get("")

        output_params = self.recurse_proto_marshal_to_dict(
            tool_use.output_action_parameters)

        return {
            "tool_name": tool_name,
            "action": tool_use.action,
            "input_parameters": input_params,
            "output_parameters": output_params
        }

    def append_user_query(
            self,
            df_rows: List[Dict[str, Any]],
            eval_id: str,
            interaction: Interaction) -> None:
            self.append_row(
                df_rows=df_rows,
                eval_id=eval_id,
                action_id=self.action_counter,
                action_type="User Utterance",
                action_input=interaction.query
                )

            self.action_counter += 1

    def append_playbook(
            self,
            df_rows: List[Dict[str, Any]],
            eval_id: str,
            interaction: Interaction) -> int:
        if interaction.playbook_invocation:
            self.append_row(
                df_rows=df_rows,
                eval_id=eval_id,
                action_id=self.action_counter,
                action_type="Playbook Invocation",
                action_input=interaction.playbook_invocation
                )
            self.action_counter += 1

    def append_tools(
            self,
            df_rows: List[Dict[str, Any]],
            eval_id: str,
            interaction: Interaction) -> int:

        count = 0
        for tool_call in interaction.tool_calls:
            tool_name = tool_call.get('tool_name', '')
            tool_action = tool_call.get('action', '')
            input_params = str(tool_call.get('input_parameters', {}))
            self.append_row(
                df_rows=df_rows,
                eval_id=eval_id,
                action_id=self.action_counter + count,
                action_type="Tool Invocation",
                action_input=tool_name,
                action_input_parameters=input_params,
                tool_action=tool_action
            )
            count += 1
        self.action_counter += count

    def append_responses(
            self,
            df_rows: List[Dict[str, Any]],
            eval_id: str,
            interaction: Interaction) -> int:

        count = 0
        for response in interaction.responses:
            self.append_row(
                df_rows=df_rows,
                eval_id=eval_id,
                action_id=self.action_counter + count,
                action_type="Agent Response",
                action_input=str(response)
                )
            count += 1
        self.action_counter += count


    def parse_interactions_from_conversation_history(
                self,
                conversation: types.Conversation) -> List[Dict[str, Any]]:
            results = []

            # Load maps if they don't already exist
            if not self.tools_map:
                self.tools_map = self.tools_client.get_tools_map(self.agent_id)
            if not self.playbooks_map:
                self. playbooks_map = self.playbooks_client.get_playbooks_map(
                    self.agent_id)

            for conv_interaction in conversation.interactions:
                interaction = Interaction(
                    query=conv_interaction.request.query_input.text.text,
                    query_result=conv_interaction.response.query_result
                )

                if interaction.generative_info:
                    for action in interaction.actions:
                        if "tool_use" in action:
                            tool_calls = (
                                self.parse_tool_use_from_conversation_history(
                                    action.tool_use)
                            )
                            interaction.tool_calls.append(tool_calls)

                        elif "agent_utterance" in action:
                            response_text = action.agent_utterance.text
                            interaction.responses.append(response_text)

                        elif "playbook_invocation" in action:
                            playbook_name = self.playbooks_map.get(
                                action.playbook_invocation.playbook, None)
                            interaction.playbook_invocation = playbook_name

                results.append(interaction)
            results.reverse()

            return results

    def add_response_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df.loc[:, "agent_response"] = pd.Series(dtype="str")
        df.loc[:, "agent_id"] = pd.Series(dtype="str")
        df.loc[:, "session_id"] = pd.Series(dtype="str")
        df.loc[:, "res_playbook_name"] = pd.Series(dtype="str")

        if "tool_call_quality" in self.user_input_metrics:
            df.loc[:, "res_tool_name"] = pd.Series(dtype="str")
            df.loc[:, "res_tool_action"] = pd.Series(dtype="str")
            df.loc[:, "res_input_params"] = pd.Series(dtype="str")
            df.loc[:, "res_output_params"] = pd.Series(dtype="str")

        return df

    def run_detect_intent_queries(self, df: pd.DataFrame) -> pd.DataFrame:
        for index, row in tqdm(df.iterrows(), total=df.shape[0]):
            data = {}
            if row["action_id"] == 1:
                self.session_id = self.sessions_client.build_session_id(
                    self.agent_id)
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

            session_parameters = None

            if "session_parameters" in row:
                session_parameters = self.str_to_dict(row["session_parameters"])

            res = self.sessions_client.detect_intent(
                agent_id=self.agent_id,
                session_id=self.session_id,
                text=row["action_input"],
                parameters=session_parameters
            )
            # Add data to the existing row
            df.loc[index, ["session_id", "agent_id"]] = [
                data["session_id"],
                data["agent_id"],
            ]
            text_res = self.ar._extract_text(res)

            # Handle Agent Responses
            if row["utterance_pair"] != "":
                utterance_idx = int(row["utterance_pair"])
                df.loc[utterance_idx, ["agent_response"]] = [text_res]

            else:
                # collect the data for inserting later
                self.unexpected_rows.append(
                    {
                        "session_id": data["session_id"],
                        "agent_id": data["agent_id"],
                        "action_type": "UNEXPECTED Agent Response",
                        "index": index,
                        "column": "agent_response",
                        "data": text_res
                    }
                    )

            # Handle Playbook Invocations
            playbook_responses = (
                self.sessions_client.collect_playbook_responses(res)
            )
            if len(playbook_responses) > 0:
                df = self.process_playbook_invocations(
                    playbook_responses, index, row, df
                )

            # Handle Flow Invocations
            flow_responses = self.sessions_client.collect_flow_responses(res)
            if len(flow_responses) > 0:
                df = self.process_flow_invocations(
                    flow_responses, index, row, df
                )

            # Handle Tool Invocations
            if "tool_call_quality" in self.user_input_metrics:
                tool_responses = (
                    self.sessions_client.collect_tool_responses(res)
                )
                if tool_responses:  # Only call if not empty
                    df = self.process_tool_invocations(
                        tool_responses,
                        index,
                        row,
                        df
                    )

        return df

    def insert_unexpected_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Insert any unexpected rows collected during runtime."""
        if self.unexpected_rows:
            for row in reversed(self.unexpected_rows):
                index = row["index"]
                new_row = pd.DataFrame(columns=df.columns, index=[index])
                new_row["session_id"] = row["session_id"]
                new_row["agent_id"] = row["agent_id"]
                new_row["action_type"] = row["action_type"]
                new_row[row["column"]] = row["data"]
                df = pd.concat(
                    [
                        df.iloc[:index],
                        new_row,
                        df.iloc[index:]
                    ])

        df = df.sort_index()

        return df

    def run_evals(self, df: pd.DataFrame) -> pd.DataFrame:
        print("Starting Evals...")

        for metric in self.metrics:
           df = pd.concat([df, metric.run(df)], axis=1)

        return df

    def scrape_results(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.add_response_columns(df)
        df = self.run_detect_intent_queries(df)
        df = self.insert_unexpected_rows(df)

        return df

    def run_query_and_eval(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.scrape_results(df)
        df = self.run_evals(df)
        df = self.clean_outputs(df)

        return df

    def create_dataset_from_conv_ids(
            self,
            conversation_ids: List) -> pd.DataFrame:
        columns = [
            'eval_id', 'action_id', 'action_type', 'action_input',
            'action_input_parameters', 'tool_action', 'notes'
        ]
        df_rows = []

        # Load maps if they don't already exist
        if not self.tools_map:
            self.tools_map = self.tools_client.get_tools_map(self.agent_id)
        if not self.playbooks_map:
            self. playbooks_map = self.playbooks_client.get_playbooks_map(
                self.agent_id)

        for idx, conv_id in enumerate(conversation_ids, start=1):
            eval_id = f"{idx:03d}"
            convo = self.ch.get_conversation(conv_id)
            interactions = self.parse_interactions_from_conversation_history(
                convo)

            self.action_counter = 1

            for interaction in interactions:
                self.append_user_query(df_rows, eval_id, interaction)
                self.append_playbook(df_rows, eval_id, interaction)
                self.append_tools(df_rows, eval_id, interaction)
                self.append_responses(df_rows, eval_id, interaction)

        return pd.DataFrame(df_rows, columns=columns)


class DataLoader:
    def __init__(
            self,
            creds_path: str = None,
            creds_dict: Dict[str, str] = None,
            creds: service_account.Credentials = None,
            agent_id: str = None,
            sheet_name: str = None,
            language_code: str = "en"
            ):

        self.agent_id = agent_id
        self.sheet_name = sheet_name
        self.dffx = DataframeFunctions(
            creds_path=creds_path, creds_dict=creds_dict, creds=creds
            )
        self.required_columns = [
            "eval_id",
            "action_id",
            "action_type",
            "action_input",
        ]
        self.language_code = language_code

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
    def get_agent_id_from_results(df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique Agent ID from eval results."""
        agent_id_vals = df.agent_id.dropna().unique().tolist()
        for id in agent_id_vals:
            if len(id) > 0:
                return id

        return ""

    @staticmethod
    def get_model_name(settings: types.GenerativeSettings) -> str:
        """Get the model name from the Generative Settings."""
        model_name = settings.llm_model_settings.model
        model_map = {
            "gemini-pro": "gemini-1.0.pro-001",
            "gemini-1.5-pro": "gemini-1.5-pro-001",
            "gemini-ultra": "gemini-ultra",
            "text-unicorn-001": "text-unicorn-001",
            "gemini-1.5-flash": "gemini-1.5-flash-001",
            "text-bison-002": "text-bison-002"
        }

        return model_map.get(model_name, "")

    def pair_tool_calls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pairs user utterances with indices of relevant tool invocations."""

        df["tool_pair"] = pd.Series(dtype="string")
        grouped = df.groupby("eval_id")

        for _, group in grouped:
            tool_indices = []
            last_user_utterance_index = None

            for index, row in group.iterrows():
                if row["action_type"] == "User Utterance":
                    # Assign accumulated tool indices to
                    # the *previous* user utterance (if any)
                    if last_user_utterance_index is not None:
                        df.loc[last_user_utterance_index, "tool_pair"] = (
                            str(tool_indices)
                        )
                    # Reset for the current user utterance:
                    tool_indices = []
                    last_user_utterance_index = index

                elif row["action_type"] == "Tool Invocation":
                    tool_indices.append(index)

            # After processing the group, assign any remaining
            # tool indices to the last user utterance
            if last_user_utterance_index is not None and tool_indices:
                df.loc[last_user_utterance_index, "tool_pair"] = (
                    str(tool_indices)
                )

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

    def pair_flow_calls(self, df: pd.DataFrame) -> pd.DataFrame:
        "Identifies pairings of agent_utterance/flow_invocation by eval_id."
        df["flow_pair"] = pd.Series(dtype="string")
        grouped = df.groupby("eval_id")

        for _, group in grouped:
            user = group[
                group["action_type"] == "User Utterance"
            ].index.tolist()
            flow_list = group[
                group["action_type"] == "Flow Invocation"
            ].index.tolist()

            pairs = self.get_matching_list_idx(
                user, flow_list
            )

            # Create pairs of user/flow_list row indices
            for pair in pairs:
                df.loc[pair[0], "flow_pair"] = str(pair[1])

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


    def build_report_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        # Check for agent_id or get from dataframe
        if not self.agent_id:
            self.agent_id = self.get_agent_id_from_results(df)

        # Get Generative Settings for report data
        a = Agents(language_code=self.language_code)
        agent = a.get_agent(self.agent_id)
        gen_settings = a.get_generative_settings(
            self.agent_id, language_code=self.language_code)
        model_name = self.get_model_name(gen_settings)

        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metrics_info = {}
        if "similarity" in df.columns:
            metrics_info["similarity"] = df["similarity"].mean()
        if "tool_name_match" in df.columns:
            metrics_info["tool_match"] = df["tool_name_match"].mean()

        eval_results_summary = pd.DataFrame({
            'timestamp': [current_datetime],
            'total_conversations': [len(df['eval_id'].unique())],
            'model_name': [model_name],
            'agent_name': agent.display_name,
            'agent_id': [self.agent_id],
            'notes': [""]
        })

        # insert metrics for report
        insert_index = eval_results_summary.columns.get_loc(
            "total_conversations") + 1
        for metric, value in metrics_info.items():
            if (isinstance(value, float) and np.isnan(value)):
                value = "-"
            eval_results_summary.insert(insert_index, metric, [value])
            insert_index += 1

        return eval_results_summary

    def append_test_results_to_sheets(
        self, results: pd.DataFrame, sheet_name: str, summary_tab: str
        ):

        summary = self.build_report_summary(results)

        client = self.dffx.sheets_client
        gsheet = client.open(sheet_name)
        sheet = gsheet.worksheet(summary_tab)

        sheet.append_rows(
            summary.values.tolist(), value_input_option="USER_ENTERED"
        )

    def convert_column_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert column types as needed."""
        STR_COLUMNS = [
            "eval_id", "action_type", "action_input", "action_input_parameters",
            "tool_action", "notes", "session_parameters"
        ]

        for col in df.columns:
            if col in STR_COLUMNS and df[col].dtype != "object":
                df[col] = df[col].astype("object")

        return df


    def validate_and_prep_inputs(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform validations and transforms on input dataframe for evals."""
        # Check for action_id column, if none exists
        # add and assume all single turn queries
        if "action_id" not in df.columns.to_list():
            df["action_id"] = 1

        df["action_id"] = df["action_id"].astype(int)
        self.validate_input_columns(df)
        self.convert_column_types(df)

        df = self.pair_utterances(df)
        df = self.pair_tool_calls(df)
        df = self.pair_playbook_calls(df)
        df = self.pair_flow_calls(df)

        # fill remaining NA with empty string
        for col in df.columns:
            if df[col].dtype in ["object", "string"]:
                df[col] = df[col].fillna("")

        return df

    def from_google_sheets(
            self, sheet_name: str, sheet_tab: str) -> pd.DataFrame:
        """Load eval dataset from Google Sheets."""
        df = self.dffx.sheets_to_dataframe(sheet_name, sheet_tab)

        # Store sheet name for later use
        self.sheet_name = sheet_name
        df = self.validate_and_prep_inputs(df)

        return df

    def from_csv(self, file_path: str) -> pd.DataFrame:
        """Load eval dataset from local CSV file."""
        df = pd.read_csv(file_path)
        df = self.validate_and_prep_inputs(df)

        return df

    def from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Load eval dataset from local premade dataframe."""
        df = self.validate_and_prep_inputs(df)

        return df
