"""A set of builder methods to create CX proto resource objects"""

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

import logging
from typing import List, Dict, Any

from dfcx_scrapi.core import scrapi_base

from google.cloud.dialogflowcx_v3beta1.types import ConversationTurn
from google.cloud.dialogflowcx_v3beta1.types import DtmfInput
from google.cloud.dialogflowcx_v3beta1.types import EventInput
from google.cloud.dialogflowcx_v3beta1.types import Intent
from google.cloud.dialogflowcx_v3beta1.types import Page
from google.cloud.dialogflowcx_v3beta1.types import QueryInput
from google.cloud.dialogflowcx_v3beta1.types import ResponseMessage
from google.cloud.dialogflowcx_v3beta1.types import TestCase
from google.cloud.dialogflowcx_v3beta1.types import TestConfig
from google.cloud.dialogflowcx_v3beta1.types import TextInput

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [test_cases_builder] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class TestCaseBuilder:
    """Base Class for CX Test Case builder."""

    def __init__(
        self, 
        obj: TestCase = None
        ):

        self.proto_obj = None
        if obj:
            self.load_test_case(obj)

        self.scrapi_base = scrapi_base.ScrapiBase()

    def __str__(self) -> str:
        """String representation of the proto_obj."""
        # self._check_agent_exist()

        return (
            f"test_case_id: {self.proto_obj.test_case_id}"
            f"display_name: {self.proto_obj.display_name}"
            f"\ntags: {self.proto_obj.tags}"
            f"\nnotes: {self.proto_obj.notes}"
            f"\ntest_config: {self.proto_obj.test_config}"
            f"\natest_case_conversation_turns: \
                {self.proto_obj.test_case_conversation_turns}"
            f"\nlast_test_result: {self.proto_obj.last_test_result}"
            )

    @staticmethod
    def build_test_case_id(agent_id: str, test_case_id: str):
        """Builds the fully qualified Test Case ID from basic inputs
        
        Args:
            agent_id (str): The DFCX agent being used for adding Test Cases
            test_case_id (str): The UUID of the Test Cases
            
        Returns:
            A fully qualified Test Case ID path / name
        """
        full_test_case_id = f'{agent_id}/testCases/{test_case_id}'

        return full_test_case_id

    @staticmethod
    def build_intent(
        intent_display_name: str,
        intent_id: str) -> Intent:
        """Builds an Intent proto for use in the Virtual Agent Output.
        
        intent_display_name (str): The human-readable name of the intent,
          unique within the agent.
        intent_id (str): The unique identifier of the intent. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              intents/<Intent ID>``.
        """
        intent = Intent()
        intent.display_name = intent_display_name
        intent.name = intent_id

        return intent

    @staticmethod
    def build_page(
        page_display_name: str,
        page_id: str) -> Intent:
        """Builds a Page proto for use in the Virtual Agent Output.
        
        page_display_name (str): The human-readable name of the page.
        page_id (str): The unique identifier of the page. Format:
          ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
            flows/<Flow ID>/pages/<Page ID>``
        """
        page = Page()
        page.display_name = page_display_name
        page.name = page_id

        if page.display_name and not page.name:
            logging.warn(f'Page ID for `{page.display_name}` is `None`. This '\
                'will cause an error when creating the Test Case in '\
                'Dialogflow CX.')

        return page

    @staticmethod
    def build_response_message_text(response: str):
        """Build a ResponseMessage.Text obj for use in Virtual Agent Output.
        
        """
        rm = ResponseMessage()
        response_text = rm.Text()
        response_text.text.extend([response])

        return response_text

    def load_test_case(
        self, obj: TestCase, overwrite: bool = False
        ) -> TestCase:
        """Load an existing Test Case to proto_obj for further uses.

        Args:
          obj (TestCase):
            An existing Test Case obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a Test Case.

        Returns:
          A Test Case object stored in proto_obj
        """
        if not isinstance(obj, TestCase):
            raise ValueError(
                "The object you're trying to load is not a TestCase!"
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a Test Case."
                " If you wish to overwrite it, pass overwrite as True."
            )

        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj

    def create_new_test_case(
            self,
            display_name: str,
            tags: List[str],
            conversation_turns: List[ConversationTurn],
            test_config: TestConfig,
            notes: str = None,
            test_case_id: str = None,
            overwrite: bool = False
        ) -> TestCase:
            """Create a new Test Case.

            Args:
                display_name (str):
                    Required. The human-readable name of the test
                    case, unique within the agent. Limit of 200
                    characters.
                tags (Sequence[str]):
                    Tags are short descriptions that users may
                    apply to test cases for organizational and
                    filtering purposes. Each tag should start with
                    "#" and has a limit of 30 characters.
                notes (str):
                    Additional freeform notes about the test
                    case. Limit of 400 characters.
                test_config (google.cloud.dialogflowcx_v3beta1.types.TestConfig):
                    Config for the test case.
                test_case_conversation_turns (Sequence[google.cloud.dialogflowcx_v3beta1.types.ConversationTurn]):
                    The conversation turns uttered when the test
                    case was created, in chronological order. These
                    include the canonical set of agent utterances
                    that should occur when the agent is working
                    properly.
                test_case_id (str):
                    The unique identifier of the test case.
                    [TestCases.CreateTestCase][google.cloud.dialogflow.cx.v3beta1.TestCases.CreateTestCase]
                    will populate the name automatically. Otherwise use format:
                    ``projects/<Project ID>/locations/<LocationID>/agents/ <AgentID>/testCases/<TestCase ID>``.

            Returns:
                A Test Case object stored in proto_obj
            """
            if (display_name and not isinstance(display_name, str)):
                raise ValueError(
                    "display_name should be string."
                )
            if self.proto_obj and not overwrite:
                raise Exception(
                    "proto_obj already contains a Test Case."
                    " If you wish to overwrite it, pass overwrite as True."
                )
            if overwrite or not self.proto_obj:
                self.proto_obj = TestCase(
                    tags=tags,
                    display_name=display_name,
                    notes=notes,
                    test_config=test_config,
                    test_case_conversation_turns=conversation_turns
                )

            return self.proto_obj

    def create_conversation_turn(
        self,
        user_input: ConversationTurn.UserInput,
        virtual_agent_output: ConversationTurn.VirtualAgentOutput):

        conversation_turn = ConversationTurn()
        conversation_turn.user_input = user_input
        conversation_turn.virtual_agent_output = virtual_agent_output

        return conversation_turn

    def create_user_input(
        self,
        input: str,
        type: str = 'text',
        finish_digit: str = None,
        injected_parameters: Dict[str, Any] = None,
        webhook_enabled: bool = True,
        sentiment_analysis_enabled: bool = True) -> ConversationTurn.UserInput:
        """Creates a User Input type for use in ConversationTurn.
        
        Args:
          input (str): The input that the user or system is stating for this
            turn of the conversation.
          type (str): The type of input expected to be sent which can be one
            of: `text`, `dtmf`, `event`
          finish_digit (str): If type `dtmf` is specified, the finish digit
            will be used to build the DtmfInput type. Even when type `dtmf`
            is used this field is still optional.
          injected_parameters (Dict[str,Any]): Parameters that need to be
            injected into the conversation during intent detection.
        Returns:
          A ConversationTurn.UserInput object for use in a Test Case
        """
        user_input = ConversationTurn.UserInput()
        query_input = QueryInput()

        if type == 'text':
            text_input = TextInput()
            text_input.text = input
            query_input.text = text_input

        elif type == 'dtmf':
            dtmf_input = DtmfInput()
            dtmf_input.digits = input
            dtmf_input.finish_digit = finish_digit
            query_input.dtmf = dtmf_input

        elif type == 'event':
            event_input = EventInput()
            event_input.event
            query_input.event = event_input

        user_input.input = query_input
        user_input.is_webhook_enabled = webhook_enabled
        user_input.enable_sentiment_analysis = sentiment_analysis_enabled

        if injected_parameters:
            user_input.injected_parameters = injected_parameters

        return user_input

    def create_virtual_agent_output(
        self,
        session_parameters: Dict[str,Any] = None,
        triggered_intent: Intent = None,
        current_page: Page = None,
        text_responses: List[ResponseMessage.Text] = None
        ) -> ConversationTurn.VirtualAgentOutput:
        """Creates a Virtual Agent Output type for use in Conversation Turn.

        Args:
          session_parameters (Dict[str, Any]): The session parameters available
            to the bot at this point.
          triggered_intent (Intent): The Intent that triggered the response.
            Only name and displayName will be set.
          current_page (Page): The Page on which the utterance was spoken.
            Only name and displayName will be set.
          text_responses (List[ResponseMessage.Text]): The Text responses from
            the agent for the turn
        """
        virtual_agent_output = ConversationTurn.VirtualAgentOutput()

        if session_parameters:
            virtual_agent_output.session_parameters = session_parameters

        if triggered_intent:
            virtual_agent_output.triggered_intent = triggered_intent

        virtual_agent_output.current_page = current_page
        virtual_agent_output.text_responses = text_responses

        return virtual_agent_output

    def create_test_config(
        self,
        tracking_parameters: List[str] = None,
        start_flow: str = None,
        start_page: str = None
        ) -> TestConfig:
        """Creates the TestConfig to be used with a Test Case.
        
        Args:
          tracking_parameters (List[str]): Session parameters to be compared
            when calculating differences.
          start_flow (str): Flow name to start the test case with. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              flows/<Flow ID>``. Only one of ``start_flow`` or ``start_page``
              should be set to indicate the starting point of the test case.
              If both are set, ``start_page`` takes precedence over
              ``start_flow``. If neither is set, the test case will start with
              start page on the default start flow.
          start_page (str): Page name to start the test case with. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              flows/<Flow ID>/pages/<Page ID>``. Only one of ``start_flow`` or
              ``start_page`` should be set to indicate the starting point of
              the test case. If both are set, ``start_page`` takes precedence
              over ``start_flow``. If neither is set, the test case will start
              with start page on the default start flow.

        Returns:
          A TestConfig object
        """
        if start_flow and start_page:
            raise ValueError (
                'Only provide ONE OF `start_flow` or `start_page`.'
            )

        if start_flow:
            self.scrapi_base._parse_resource_path('flow', start_flow)

        if start_page:
            self.scrapi_base._parse_resource_path('page', start_page)

        test_config = TestConfig()
        test_config.flow = start_flow
        test_config.page = start_page
        test_config.tracking_parameters = tracking_parameters

        return test_config
