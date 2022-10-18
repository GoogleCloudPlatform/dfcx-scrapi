"""A set of utils to enable automated Test Cases manipulation."""

# Copyright 2022 Google LLC
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

from typing import List, Dict, Tuple
from ast import literal_eval

import logging
import re
from google.cloud.dialogflowcx_v3beta1.types import test_case
import numpy as np
import pandas as pd

from google.cloud import storage
from google.oauth2 import service_account

from dfcx_scrapi.core import intents
from dfcx_scrapi.core import flows
from dfcx_scrapi.core import pages
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import test_cases
from dfcx_scrapi.tools import dataframe_functions
from requests import session

from builders.test_cases import TestCaseBuilder

logging.basicConfig(
    level=logging.INFO,
    format="[dfcx] %(levelname)s:%(message)s"
)

# TODO: Consider placing in scrapi_base
class GcsUtil:
    @staticmethod
    def _parse_bucket_name(gcs_bucket_uri):
        """Parse the GCS Bucket name from the provided full GCS Bucket URI."""
        pattern = r'gs:\/\/(.*?)\/'
        match = re.search(pattern, gcs_bucket_uri)

        bucket_name = match.groups()[0]

        return bucket_name

    @staticmethod
    def _parse_file_name(gcs_bucket_uri):
        """Parse the filename portion of the full GCS Bucket URI."""
        pattern = r'gs:\/\/.*?\/(.*)'
        match = re.search(pattern, gcs_bucket_uri)

        file_name = match.groups()[0]

        return file_name

    @staticmethod
    def _set_gcp_creds(creds_dict=None):
        """Sets GCP Creds."""
        creds = service_account.Credentials.from_service_account_info(creds_dict)

        return creds

    def _setup_storage_client(self, creds_dict):
        """Instantiate the Storage Client."""
        creds = self._set_gcp_creds(creds_dict)

        storage_client = storage.Client(
            credentials=creds,
            project=creds.project_id,
            )

        return storage_client

    def read_from_gcs(self, creds_dict, gcs_bucket_uri: str):
        """Reads the timestamp from the provided timestamp file.

        gcs_bucket_uri: Fully qualified GCS bucket in the following format:
            gs://bucket_name/filename.blah
        """
        client = self._setup_storage_client(creds_dict)
        bucket_name = self._parse_bucket_name(gcs_bucket_uri)
        file_name = self._parse_file_name(gcs_bucket_uri)

        bucket = client.get_bucket(bucket_name)
        blob = bucket.get_blob(file_name)

        return blob

    def download_from_gcs(self, creds_dict, gcs_bucket_uri: str, destination_file: str):
        """Reads the timestamp from the provided timestamp file.

        gcs_bucket_uri: Fully qualified GCS bucket in the following format:
            gs://bucket_name/filename.blah
        """
        client = self._setup_storage_client(creds_dict)
        bucket_name = self._parse_bucket_name(gcs_bucket_uri)
        file_name = self._parse_file_name(gcs_bucket_uri)

        bucket = client.get_bucket(bucket_name)
        blob = bucket.get_blob(file_name)

        blob.download_to_filename(destination_file)

class TestCaseUtil(scrapi_base.ScrapiBase):
    """Util class for test case automation and transformation."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.dffx = dataframe_functions.DataframeFunctions(creds=self.creds)
        self.intents = intents.Intents(creds=self.creds)
        self.flows = flows.Flows(creds=self.creds)
        self.pages = pages.Pages(creds=self.creds)
        self.test_cases = test_cases.TestCases(creds=self.creds)
        self.tcb = TestCaseBuilder()

    @staticmethod
    def _dataframe_to_dict_of_dataframes(df, group_column):
        """Converts the incoming dataframe into a dict of dataframes.
        
        Args:
          df: The incoming dataframe to be sliced and converted
          group_column: the specified column to slice the incoming dataframe
          
        Returns
          A Dictionary of Dataframes with the keys consisting of the
          group_column values that were sliced, and the values consisting
          of the grouped dataframe.
        """
        df_dict = {}

        tcid_set = set(df.test_case_id.to_list())
        for tcid in tcid_set:
            temp_df = df[df.test_case_id == tcid].copy()
            temp_df.reset_index(drop=True, inplace=True)

            df_dict[tcid] = temp_df

        # if the incoming sheet has empty rows in it they'll be grouped
        # together in this kv pair that we can drop.
        df_dict.pop('', None)

        return df_dict

    @staticmethod
    def add_generic_pages_to_map(flow_id, pages_map):
        """Add the generic page names to each Flow map."""
        page_names = ['START_PAGE', 'END_FLOW', 'END_SESSION']

        for page in page_names:
            pages_map[page] = f'{flow_id}/pages/{page}'

        return pages_map

    @staticmethod
    def _parse_incoming_responses(agent_output, delimiter):
        """Split the incoming responses based on the provided delimiter."""
        responses = agent_output.split(delimiter)

        return responses

    # @staticmethod
    # def _check_for_dict_structure(session_parameters):
    #     """Parses incoming params if they are in a Dict-like structure."""

    #     match_string = None
    #     # Dict Type Matching
    #     dict_pattern = r'(\{.*\})'

    #     match = re.search(dict_pattern, session_parameters)
    #     if match:
    #         match_string = match.groups()[0]

    #     return match_string

    @staticmethod
    def _parse_incoming_parameters_struct(session_parameters: str):
        """Parse dict-like string structure to extract session parameters.

        Will attempt to match dict-like structure from exisinting string format
        and extract as group. If there are chars outside of dict (i.e. spaces,
        etc.) it will ignore and/or remove.

        Args:
          session_parameters: A dict-like structure in string format to be used
            for parameters in the Test Case object. Format:
            '{"key1": "value1", "key2":"value2", "key3": True}'
        """
        match_dict = None

        if session_parameters:
            cleaned_session_parameters = session_parameters.replace('\n', '')
            match_pattern = r'(\{.*\})'

            match_string = re.search(
                match_pattern, cleaned_session_parameters).groups()[0]
            
            try:
                match_dict = literal_eval(match_string)

            except ValueError:
                input_format = '{"key1": "value1", "key2":"value2", "key3": True}'
                print('Input Parameters are malformed. Please check the '\
                'required format')
                print(f'Required Format: {input_format}')
                print(f'Provided Format: {match_string}')

        return match_dict

    @staticmethod
    def _parse_incoming_flow_page_fields(
        flow_name,
        page_name,
        flow_page_map) -> Tuple[str,str]:
        """Performs lookup of Flow/Page names and returns IDs for each."""

        flow_id = None
        page_id = None

        start_pages = ['start', 'start page']

        if page_name.lower() in start_pages:
            page_name = 'START_PAGE'

        if flow_name and page_name:
            if flow_name in flow_page_map:
                if page_name in flow_page_map[flow_name]['pages']:
                    page_id = flow_page_map[flow_name]['pages'][page_name]

        # check if start_flow exists
        elif flow_name:
            # check if flow is in flow_page_map
            if flow_name in flow_page_map:
                flow_id = flow_page_map[flow_name]['id']

        elif page_name:
            # Find page in flow_page_map
            # this will be a `best_effort` search by Page Name and we will
            # grab the first key that matches the Page name. This could cause
            # issues if the Page name is duplicated across multiple flows. In
            # this case, it's best to provide both Flow and Page name to limit
            # the search space.
            for flow in flow_page_map:
                if page_name in flow_page_map[flow]['pages']:
                    page_id= flow_page_map[flow]['pages'][page_name]

        return (flow_id, page_id)

    @staticmethod
    def _parse_tracking_parameters(tracking_parameters):
        """Split the incoming string into a list by comma."""
        split_params = tracking_parameters.split(',')
        final_params = [x.strip() for x in split_params]

        return final_params

    @staticmethod
    def _parse_incoming_intent(intent_display_name, intents_map):
        """Gather info to create Intent Proto."""
        intent_id = None

        if intent_display_name and intent_display_name in intents_map:
            intent_id = intents_map[intent_display_name]

        return intent_id

    @staticmethod
    def _parse_incoming_current_page(page_display_name, flow_page_map):
        """Gather info to create Page Proto."""
        page_id = None

        # remove any accidental whitespace
        page_display_name = page_display_name.strip()

        generic_pages_list = ['End Session', 'End Flow', 'Start Page']

        if page_display_name in generic_pages_list:
            page_display_name = '_'.join(page_display_name.upper().split(' '))


        for flow in flow_page_map:
            if page_display_name in flow_page_map[flow]['pages']: 
                page_id = flow_page_map[flow]['pages'][page_display_name]

        return page_id

    @staticmethod
    def _parse_incoming_tags(tags):
        """Split the incoming tags into a list."""
        tag_list = tags.split(',')

        # strip any space from front of tag item
        # check for existence of hashtag, and add if missing
        for i, tag in enumerate(tag_list):
            tag = tag.replace(' ', '')
            if tag[0] != '#':
                tag = '#' + tag
            tag_list[i] = tag

        return tag_list

    @staticmethod
    def _check_and_convert_str_to_bool(test_string: str):
        """Checks to see if String is bool-like value and converts it."""
        valid_bool = None

        bool_map = {
            'false': False,
            'true': True
        }

        if isinstance(test_string, str) and test_string != '':
            test_string = test_string.lower()
            valid_bool = bool_map[test_string]
        
        return valid_bool

    def _build_user_input(
        self,
        injected_parameters: str,
        user_input_str: str,
        webhook_enabled: bool = False,
        sentiment_analysis_enabled: bool = False,
        type: str = 'text') -> test_case.ConversationTurn.UserInput:
        """Builds the User Input object for the Conversation Turn."""
        injected_parameters = self._parse_incoming_parameters_struct(
            injected_parameters)

        # Convert Bool Values if they come as String
        webhook_enabled = self._check_and_convert_str_to_bool(
            webhook_enabled
        )
        sentiment_analysis_enabled = self._check_and_convert_str_to_bool(
            sentiment_analysis_enabled
        )

        user_input = self.tcb.create_user_input(
            input=user_input_str,
            type=type,
            injected_parameters=injected_parameters,
            webhook_enabled=webhook_enabled,
            sentiment_analysis_enabled=sentiment_analysis_enabled)

        return user_input

    def _build_test_config(
        self,
        start_flow_display_name: str,
        start_page_display_name: str,
        tracking_parameters_str: str
        ) -> test_case.TestConfig:
        """Builds the Test Config object for the Test Case."""
        flow_id, page_id = self._parse_incoming_flow_page_fields(
            start_flow_display_name,
            start_page_display_name,
            self.flow_page_map)
            
        tracking_parameters = self._parse_tracking_parameters(
            tracking_parameters_str)
            
        test_config = self.tcb.create_test_config(
            tracking_parameters=tracking_parameters,
            start_flow=flow_id,
            start_page=page_id
            )

        return test_config

    def _build_virtual_agent_output(
        self,
        expected_parameters_str: str,
        expected_intent: str,
        agent_output: str,
        expected_page: str
        ) -> test_case.ConversationTurn.VirtualAgentOutput:
        """Builds the Virtual Agent Output object for the Conversation Turn."""
        session_parameters = self._parse_incoming_parameters_struct(
            expected_parameters_str)
        
        ## Build Expected Intent
        intent_display_name = expected_intent
        intent_id = self._parse_incoming_intent(
            intent_display_name, self.intent_map)
        triggered_intent = self.tcb.build_intent(
            intent_display_name, intent_id)

        ## Build text_responses
        responses_list = self._collect_virtual_agent_responses(agent_output)

        ## Get Current Page Information for Turn
        current_page = None
        page_display_name = expected_page
        if expected_page:
            page_id = self._parse_incoming_current_page(
                page_display_name, self.flow_page_map)
            current_page = self.tcb.build_page(page_display_name, page_id)

        virtual_agent_output = self.tcb.create_virtual_agent_output(
            session_parameters=session_parameters,
            triggered_intent=triggered_intent,
            current_page=current_page,
            text_responses=responses_list
            )

        return virtual_agent_output


    def _collect_virtual_agent_responses(self, responses_string):
        """Gather responses in proper format for Virtual Agent object
        
        """
        responses_from_input = self._parse_incoming_responses(
            responses_string, '\n')
        responses_list = []

        for response in responses_from_input:
            response_text = self.tcb.build_response_message_text(response)
            responses_list.append(response_text)

        return responses_list


    # TODO: Consider putting in core.flows instead
    def get_flow_page_map(self, agent_id: str) -> Dict[str, Dict[str, str]]:
        flow_page_map = {}

        flows_map = self.flows.get_flows_map(agent_id, reverse=True)

        for flow in flows_map:
            pages_map = self.pages.get_pages_map(
                flows_map[flow], reverse=True)
            pages_map = self.add_generic_pages_to_map(
                flows_map[flow], pages_map)
            flow_page_map[flow] = {'id': flows_map[flow], 'pages': pages_map}

        return flow_page_map

    def build_test_cases_from_dataframe(
        self,
        df: pd.DataFrame,
        agent_id: str
        ) -> List[test_case.TestCase]:
        """Builds a List of Test Cases from the provided DataFrame.
        
        Args:
          df: Input DataFrame used to build Test Cases.
          flow_page_map: A dictionary of Flows/Pages mapped out to provide
            easy lookup for the various Flows/Pages to build a Test Case.
          intent_map: A dictionary of Intent Names/IDs used to perform lookups
            for various Intent Names/IDs to build a Test Case.
        """
        all_tcs = []
        self.intent_map = self.intents.get_intents_map(agent_id, reverse=True)
        self.flow_page_map = self.get_flow_page_map(agent_id)

        df_dict = self._dataframe_to_dict_of_dataframes(df, 'test_case_id')

        for tc_id in df_dict:
            logging.debug(f'Processing Test Case ID: {tc_id}')
            # init new list of convo turns for new Test Case
            conversation_turns = []

            for i, row in df_dict[tc_id].iterrows():

                # Set top level test_case parameters
                if row.position == '1':
                    display_name = row.display_name
                    tags = self._parse_incoming_tags(row.tags)

                    # Build Test Config
                    test_config = self._build_test_config(
                        row.start_flow,
                        row.start_page,
                        row.tracking_parameters
                    )

                # Check for Existing ID in proper format
                if row.test_case_id:
                    tcid = self.tcb.build_test_case_id(
                        agent_id, row.test_case_id)
                    self.test_cases._parse_resource_path('test_case', tcid)
                
                # Build User Input
                user_input = self._build_user_input(
                    row.injected_parameters,
                    row.user_input,
                    row.webhook_enabled,
                    row.sentiment_analysis_enabled
                )



                # Build Virtual Agent Output
                virtual_agent_output = self._build_virtual_agent_output(
                    row.expected_parameters,
                    row.expected_intent,
                    row.agent_output,
                    row.expected_page
                )

                # Build Conversation Turn
                conv_turn = self.tcb.create_conversation_turn(
                    user_input, virtual_agent_output)
                conversation_turns.append(conv_turn)

            test_case_obj = self.tcb.create_new_test_case(
                display_name,
                tags,
                conversation_turns,
                test_config,
                overwrite=True
            )

            all_tcs.append(test_case_obj)
        
        return all_tcs
