"""Test Cases Utility functions."""

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
import time
from typing import Dict, List, Union

from google.api_core import exceptions as core_exceptions
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf.struct_pb2 import Struct

from dfcx_scrapi.core import flows, intents, pages, scrapi_base, test_cases

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class TestCasesUtil(scrapi_base.ScrapiBase):
    """Util class for CX test cases"""

    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id
        self._global_test_cases = test_cases.TestCases(
            creds=self.creds, agent_id=self.agent_id)
        self.source_commons = {}
        self.target_commons = {}

    def _toggle_sentiment_in_convturns(
        self,
        conv_turns: List[types.ConversationTurn],
        sentiment: bool) -> List[types.ConversationTurn]:
        """Enable/disable enable_sentiment_analysis for all conversation turns.
        Args:
            conversation_turns: types.ConversationTurn
        Returns:
            a list of the conversation turns
        """
        new_conversation_turns = []
        for conversation_turn in conv_turns:
            conversation_turn.user_input.enable_sentiment_analysis = sentiment
            new_conversation_turns.append(conversation_turn)

        return new_conversation_turns

    def toggle_sentiment_test_cases(
        self,
        test_case_ids: List[str],
        sentiment: bool) -> List[types.TestCase]:
        """Enable/disable enable_sentiment_analysis for the given test case ids.
        Args:
            test_cases: a list of test case ids
            sentiment:
                if True then enable_sentiment_analysis = True
                else disable_sentiment_analysis = False
            agent_id: The formatted CX Agent ID
        Returns:
            a list of the updated test cases
        """
        test_cases_list = self._global_test_cases.list_test_cases(
            agent_id=self.agent_id, include_conversation_turns=True)
        updated_test_cases_list = []
        for test_case in test_cases_list:
            if test_case.name in test_case_ids:
                test_case.test_case_conversation_turns = (
                    self._toggle_sentiment_in_convturns(
                        conv_turns=test_case.test_case_conversation_turns,
                        sentiment=sentiment)
                )
                updated_test_cases_list.append(test_case)

        return updated_test_cases_list

    def _toggle_webhooks_in_convturns(
        self,
        conv_turns: List[types.ConversationTurn],
        is_webhook_enabled: bool) -> List[types.ConversationTurn]:
        """Sets the webhooks equal to True/False for all conversation turns.
        Args:
            conversation_turns: types.ConversationTurn
        Returns:
            conversation turns
        """

        new_conversation_turns = []
        for conversation_turn in conv_turns:
            conversation_turn.user_input.is_webhook_enabled = is_webhook_enabled
            new_conversation_turns.append(conversation_turn)

        return new_conversation_turns

    def toggle_webhooks_test_cases(
        self,
        test_case_ids: List[str],
        is_webhook_enabled: bool) -> List[types.TestCase]:
        """
        Enable/disable webhooks for the given test case ids.
        Args:
            test_cases: a list of the test case ids
            is_webhook_enabled: if enable then True else False
            agent_id: The formatted CX Agent ID
        Returns:
            list of the updated test caess
        """
        test_cases_list = self._global_test_cases.list_test_cases(
            agent_id=self.agent_id, include_conversation_turns=True)
        updated_test_cases_list = []
        for test_case in test_cases_list:
            if test_case.name in test_case_ids:
                test_case.test_case_conversation_turns = (
                    self._toggle_webhooks_in_convturns(
                        conv_turns=test_case.test_case_conversation_turns,
                        is_webhook_enabled=is_webhook_enabled)
                    )
                updated_test_cases_list.append(test_case)

        return updated_test_cases_list

    @staticmethod
    def _reverse_dict(dict_):
        """Utility method that reverse the dict keys and values
            Args:
                dict_: a dictionary
            Returns:
                a reversed dictionary
        """

        return {v: k for k, v in dict_.items()}

    def _get_resource_map(
        self,
        agent_id: str) -> Dict[str, Dict[str, str]]:
        """This method map flows, pages, and intents
            are in the dictionary format
          Arg:
            agent_id: The formatted CX Agent ID
          Returns:
            a dictionary of flows, pages, and intents
        """

        commons_config = {}
        commons_config["agent_id"] = agent_id
        dfcx_flows = flows.Flows(creds=self.creds, agent_id=agent_id)
        dfcx_pages = pages.Pages(creds=self.creds)
        dfcx_intents = intents.Intents(creds=self.creds, agent_id=agent_id)
        dfcx_testcases = test_cases.TestCases(
            creds=self.creds, agent_id=agent_id)
        dfcx_intents_map = dfcx_intents.get_intents_map(agent_id=agent_id)
        dfcx_flows_map = dfcx_flows.get_flows_map(agent_id=agent_id)
        dfcx_pages_map = {}
        for flow_id in dfcx_flows_map.keys():
            dfcx_pages_map[flow_id] = dfcx_pages.get_pages_map(flow_id=flow_id)
        commons_config["test_cases"] = dfcx_testcases
        commons_config["flows"] = dfcx_flows
        commons_config["pages"] = dfcx_pages
        commons_config["intents"] = dfcx_intents
        commons_config["flows_map"] = dfcx_flows_map
        commons_config["pages_map"] = dfcx_pages_map
        commons_config["intents_map"] = dfcx_intents_map
        commons_config["flows_map_reverse"] = (
            self._reverse_dict(dict_=commons_config["flows_map"]))
        commons_config["intents_map_reverse"] = (
            self._reverse_dict(dict_=commons_config["intents_map"]))
        commons_config["pages_map_reverse"] = (
            {f_id:self._reverse_dict(dict_=pages_map) \
             for f_id, pages_map in dfcx_pages_map.items()})

        return commons_config

    def _get_new_test_config(
        self,
        source_resource_map: dict,
        target_resource_map: dict,
        test_case: types.TestCase) -> Union[types.TestConfig, None]:
        """Update the test case types.test_config to the new types.test_config
            Update the uuids of flow, page, intent by the display_name
            If a TestConfig is found, it will return that,
            otherwise an empty TestConfig is returned.
          args:
            source_resource_map: a source resource dictionary
            target_resource_map: a target resource dictionary
            test_case: types.test_config object
          returns:
            types.test_config
        """
        source_flow_id = (
            # pylint: disable=W0212
            source_resource_map["test_cases"]._get_flow_id_from_test_config(
            test_case=test_case)
        )
        source_page_id = (
            # pylint: disable=W0212
            source_resource_map["test_cases"]._get_page_id_from_test_config(
                test_case=test_case, flow_id=source_flow_id)
        )
        source_flow = self._get_flow_display_name_by_id(
            source_flow_id, source_resource_map["flows_map"])
        source_page = self._get_page_display_name_by_id(
            source_flow_id, source_page_id, source_resource_map["pages_map"])
        target_test_config = types.TestConfig()

        if test_case.test_config.flow:
            target_flow_id = self._get_flow_id_by_flow_name(
                flow_name=source_flow,
                flows_map=target_resource_map["flows_map_reverse"])
            if target_flow_id:
                target_test_config.flow = target_flow_id
            else:
                return None

        elif test_case.test_config.page:
            target_flow_id = self._get_flow_id_by_flow_name(
                flow_name=source_flow,
                flows_map=target_resource_map["flows_map_reverse"])
            target_page_id = self._get_page_id_by_page_name(
                flow_id=target_flow_id,
                page_name=source_page,
                pages_map=target_resource_map["pages_map_reverse"])
            if target_page_id:
                target_test_config.page = target_page_id
            else:
                return None

        return target_test_config

    def _get_flow_display_name_by_id(
        self,
        flow_id: str,
        flows_map: Dict[str, str]) -> str:
        """Attempt to get the Flow Display Name from the Flows Map
            by the flow ID."""

        flow = flows_map.get(flow_id, None)

        return flow

    def _get_page_display_name_by_id(
        self,
        flow_id: str,
        page_id: str,
        pages_map: Dict[str, Dict[str, str]]) -> str:
        """Get the Page Display Name from the Pages Map based on the Page ID."""

        page_map = pages_map.get(flow_id, None)
        page = "START_PAGE"

        if page_map:
            page = page_map.get(page_id, None)

        return page

    def _get_flow_id_by_flow_name(
        self,
        flow_name: str,
        flows_map: Dict[str, str]) -> str:
        """Attempt to get the Flow id from the Flows Map
            by the flow display name."""

        return flows_map.get(flow_name, None)

    def _get_page_id_by_page_name(
        self,
        flow_id: str,
        page_name: str,
        pages_map: Dict[str, Dict[str, str]]) -> str:
        """Attempt to get the Page id from the Pages Map
            by the Page display name."""

        if not flow_id:
            return None
        page_map = pages_map.get(flow_id, None)
        page_id = None
        if  page_name in [
            "Start Page",
            "End Flow",
            "End Session",
            "End Flow With Failure",
            "End Flow With Human Escalation",
            "End Flow With Cancellation"
            ]:
            page_name = page_name.upper().replace(" ", "_")
            page_id = f"{flow_id}/pages/{page_name}"
        elif page_map:
            page_id = page_map.get(page_name, None)

        return page_id

    def _get_intent_id_by_intent_name(
        self,
        intent_name: str,
        intents_map: Dict[str, str]) -> str:
        """Attempt to get the intent id from the Intents Map
            by the intent's display name."""

        return intents_map.get(intent_name, None)

    def _get_intent_name_by_intent_id(
        self,
        intent_id: str,
        intents_map: Dict[str, str]) -> str:
        """Attempt to get the intent display name from the Intents Map
            by the intent's display name."""

        return intents_map.get(intent_id, None)

    def _get_intent_id_from_virtual_agent_output(
        self,
        virtual_agent_output: types.ConversationTurn.VirtualAgentOutput,
        target_resource_map: dict) -> Union[str, None]:
        """Attempt to find the intent id from the source's agent
        conversation_turn.virtual_agent_output triggered intent
        display name using the target's intents map
        """

        source_intent = (
          virtual_agent_output.triggered_intent.display_name
        )
        return self._get_intent_id_by_intent_name(
            intent_name=source_intent,
            intents_map=target_resource_map["intents_map_reverse"])

    def _get_page_id_from_virtual_agent_output(
        self,
        virtual_agent_output: types.ConversationTurn.VirtualAgentOutput,
        source_resource_map: dict,
        target_resource_map: dict) -> Union[str, None]:
        """Attempt to find the page id from the source's agent conversation turn
          virtual agent output page id to the target's pages map
        """

        source_page = virtual_agent_output.current_page.display_name
        source_page_id = virtual_agent_output.current_page.name
        source_flow = self._get_flow_display_name_by_id(
            flow_id = source_page_id.split("/pages/")[0],
            flows_map = source_resource_map["flows_map"])
        target_flow_id = self._get_flow_id_by_flow_name(
            flow_name=source_flow,
            flows_map=target_resource_map["flows_map_reverse"])
        target_page_id = self._get_page_id_by_page_name(
            flow_id=target_flow_id,
            page_name=source_page,
            pages_map=target_resource_map["pages_map_reverse"])

        return target_page_id

    def _get_intent_id_from_user_input(
        self,
        user_input: types.ConversationTurn.UserInput,
        source_resource_map: dict,
        target_resource_map: dict) -> Union[str, None]:
        """Attempt to find the intent id from the source's agent
          conversation turn user input intent id to the target's pages map
        """

        source_intent_id = user_input.input.intent
        source_intent = self._get_intent_name_by_intent_id(
            intent_id=source_intent_id,
            intents_map=source_resource_map["intents_map"])
        target_intent_id = self._get_intent_id_by_intent_name(
            intent_name=source_intent,
            intents_map=target_resource_map["intents_map_reverse"])

        return target_intent_id

    def _build_conversation_turns_for_target_agent(
        self,
        source_resource_map: dict,
        target_resource_map: dict,
        conversation_turns: types.ConversationTurn
        ) -> Union[List[types.ConversationTurn], None]:
        """ Update the uuids of the current page and intent
            by display name in each conversation turn.
          Args:
            source_resource_map: a source resource dictionary
            target_resource_map: a target commons_config dictionary
            conversation_turns: types.ConversationTurn
          Returns:
            types.test_case_conversation_turns
        """

        new_conversation_turns = []
        for conv_turn in conversation_turns:
            user_input_intent = conv_turn.user_input
            virtual_agent_output = conv_turn.virtual_agent_output
            if user_input_intent.input.intent:
                conv_turn.user_input.input.intent = (
                    self._get_intent_id_from_user_input(
                        user_input=user_input_intent,
                        source_resource_map=source_resource_map,
                        target_resource_map=target_resource_map
                        )
                )
                if not conv_turn.user_input.input.intent:
                    return None
            if virtual_agent_output.current_page:
                conv_turn.virtual_agent_output.current_page.name = (
                    self._get_page_id_from_virtual_agent_output(
                        virtual_agent_output=virtual_agent_output,
                        source_resource_map=source_resource_map,
                        target_resource_map=target_resource_map
                        )
                )
                if not conv_turn.virtual_agent_output.current_page.name:
                    return None
            if virtual_agent_output.triggered_intent:
                conv_turn.virtual_agent_output.triggered_intent.name = (
                    self._get_intent_id_from_virtual_agent_output(
                        virtual_agent_output=virtual_agent_output,
                        target_resource_map=target_resource_map
                    )
                )
                if not conv_turn.virtual_agent_output.triggered_intent.name:
                    return None
            new_conversation_turns.append(conv_turn)

        return new_conversation_turns

    def _log_missing_attributes(
        self,
        test_case: types.TestCase,
        test_config: types.TestConfig,
        conv_turns: List[types.ConversationTurn],
        last_test_conv_turns: List[types.ConversationTurn]):
        """This method is a logger that indicates which attributes are not
        convertible in the test case.
        Args:
          test_config: types.TestConfig
          conv_turns: List[types.ConversationTurn]
          last_test_conv_turns: List[types.ConversationTurn]
        """

        if test_config is None:
            logging.warning(
                "-- ERROR --  DFCX Test case failed to convert -- "
                f"test_case: {test_case.display_name} "
                "Reason: test_config is None.")
        if conv_turns is None:
            logging.warning(
                "-- ERROR --  DFCX Test case failed to convert -- "
                f"test_case: {test_case.display_name} "
                "Reason: test_conversation_turns is None.")
        if last_test_conv_turns is None:
            logging.warning(
                "-- ERROR --  DFCX Test case failed to convert -- "
                f"test_case: {test_case.display_name} "
                "Reason: last_test_result is None.")

    def convert_test_case(
        self,
        test_case: types.TestCase,
        source_agent_id: str,
        target_agent_id: str,
        rate_limit: int = 5) -> Union[types.TestCase, None]:
        """This method converts the test case from the source agent to the
          target agent.
          Note: In dfcx_scrapi.core.test_case.TestCases, it requires
          list_test_cases(include_conversation_turns=True),
          Otherwise, it will fail to convert.
        Args:
          test_case: types.TestCase
          source_agent_id: str
          target_agent_id: str
          rate_limit: int
        Returns:
          types.TestCase or None if  fails
        """

        if not test_case.test_case_conversation_turns:
            raise UserWarning(
                "types.TestCase is not convertible if "
                "test_case_conversation_turns is empty "
                f"test case : {test_case.display_name}"
            )
        if not self.source_commons.get("agent_id") == source_agent_id:
            self.source_commons = self._get_resource_map(
                agent_id=source_agent_id)
        if not self.target_commons.get("agent_id") == target_agent_id:
            self.target_commons = self._get_resource_map(
                agent_id=target_agent_id)

        test_config = self._get_new_test_config(
            self.source_commons, self.target_commons, test_case)
        conv_turns = self._build_conversation_turns_for_target_agent(
            self.source_commons,
            self.target_commons,
            test_case.test_case_conversation_turns)
        last_test_conv_turns = self._build_conversation_turns_for_target_agent(
            self.source_commons,
            self.target_commons,
            test_case.last_test_result.conversation_turns)

        if not all([test_config, conv_turns, last_test_conv_turns]):
            self._log_missing_attributes(
                test_case, test_config, conv_turns, last_test_conv_turns)
            return None

        test_case.name = None
        test_case.test_config = test_config
        test_case.test_case_conversation_turns = conv_turns
        test_case.last_test_result.conversation_turns = last_test_conv_turns
        new_test_case = None
        try:
            new_test_case = self.target_commons["test_cases"].create_test_case(
                test_case=test_case)
            time.sleep(rate_limit)
        except core_exceptions.InternalServerError as err:
            logging.error(
                f"-- ERROR -- InternalServerError caught on CX.detect -- {err}")
            logging.error("test_case: %s", test_case.display_name)
        except core_exceptions.ClientError as err:
            logging.error(
                f"-- ERROR -- ClientError caught on CX.detect -- {err}")
            logging.error("test_case: %s", test_case.display_name)
        logging.info(
            "-- SUCCESS -- DFCX test_case converted -- "
            f"test case: {new_test_case.display_name}")

        return new_test_case

    def _initialize_conversation_turn(self) -> types.ConversationTurn:
        """it initializes the conversation turn.
        Returns:
          types.ConversationTurn
        """
        conversation_turn = types.ConversationTurn()
        conversation_turn.user_input = (
            conversation_turn.UserInput(input=types.QueryInput()))

        return conversation_turn

    def _set_query_input(
        self,
        send_obj: Dict,
        conversation_turn: types.ConversationTurn
        ) -> types.ConversationTurn:
        """it sets the query input. In query input, it handle 4 types
          of input: text, event, intent, dtmf if not, then it raises a warning.
        Args:
          conversation_turn: types.ConversationTurn
        Returns:
          types.ConversationTurn
        """
        if "dtmf" in send_obj:
            finish_digit = send_obj.get("finish_digit", None)
            if finish_digit:
                finish_digit = str(finish_digit)
            conversation_turn.user_input.input.dtmf = (
                types.DtmfInput(
                    digits=send_obj["dtmf"],
                    finish_digit=finish_digit))
        elif "event" in send_obj:
            conversation_turn.user_input.input.event = (
                types.EventInput(event=send_obj["event"]))
        elif "text" in send_obj:
            conversation_turn.user_input.input.text = (
                types.TextInput(text=send_obj["text"]))
        elif "intent" in send_obj:
            conversation_turn.user_input.input.intent = (
                types.IntentInput(intent=send_obj["intent"]))
        else:
            raise UserWarning(
                "send_obj doesn't contain the proper query input type. "
                "it must contains one of [text, event, intent, dtmf] as a key")

        return conversation_turn

    def _convert_send_objs_to_conv_turns(
        self,
        send_objs: List[Dict],
        webhooks: bool) -> List[types.ConversationTurn]:
        """This function converts the send_objs to conversation turns.
          Iterate send_objs, set the params and a user_input of every turn.
        Args:
          send_objs: List[dict]
          webhooks: bool
        Returns:
          List[types.ConversationTurn]
        """
        conversation_turns = []
        for send_obj in send_objs:
            conversation_turn = self._initialize_conversation_turn()
            if "params" in send_obj:
                param = Struct()
                param.update(send_obj["params"])
                conversation_turn.user_input.injected_parameters = param
            conversation_turn.user_input.is_webhook_enabled = webhooks
            conversation_turn = self._set_query_input(
                send_obj=send_obj,
                conversation_turn=conversation_turn)
            conversation_turns.append(conversation_turn)
        return conversation_turns

    def _set_test_config(
        self,
        current_page) -> types.TestConfig:
        """it sets the test config of the test case.
        if current page is None, then it starts at Default Start Flow/Start page
        if current page is a page id, then it starts at the specific page id
        if current page is a flow id, then it starts at the flow start page
        Args:
          current_page: str
        Returns:
          types.TestConfig
        """
        test_config = types.TestConfig()
        if current_page:
            if "pages" in current_page:
                test_config.page = current_page
            else:
                test_config.flow = current_page

        return test_config

    def create_test_case_by_send_objs(
        self,
        display_name: str,
        send_objs: List[Dict],
        webhooks: bool = False,
        current_page: str = None,
        tags: List[str] = None,
        rate_limit: int = 5) ->  Union[types.TestCase, None]:
        """it creates a test case by a list of send_objs. Each send_obj
        consists of params and user input of every turn. Send_obj is commonly
        used in the e2e testing, dfcx_scrapi.core.conversation.reply().
        With this function, it can simultaneously create the test case while
        running the e2e test.
        Args:
          display_name: a display_name of the test case
          send_objs: a list of send_objs
          webhooks: False by default, if True, then it enables webhooks
          current_page: page_id of where the test case begins
          tags: List[str]
          rate_limit: int
        Returns:
          types.TestCase or None if fails
        """
        test_case = types.TestCase()
        test_case.display_name = display_name
        test_case.tags = tags
        if current_page:
            test_case.test_config = self._set_test_config(
                current_page=current_page)
        test_case.test_case_conversation_turns = (
            self._convert_send_objs_to_conv_turns(
                send_objs=send_objs, webhooks=webhooks)
        )
        response = None
        try:
            response = self._global_test_cases.create_test_case(
                test_case=test_case)
            time.sleep(rate_limit)
        except core_exceptions.InternalServerError as err:
            logging.error(
                f"-- ERROR -- InternalServerError caught on CX.detect -- {err}")
            logging.error("test_case: %s", test_case.display_name)
        except core_exceptions.ClientError as err:
            logging.error(
                f"-- ERROR -- ClientError caught on CX.detect -- {err}")
            logging.error("test_case: %s", test_case.display_name)

        return response
