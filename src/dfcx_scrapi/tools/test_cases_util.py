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
from typing import Dict, List, Union
import time
from google.cloud.dialogflowcx_v3beta1 import types

from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import flows
from dfcx_scrapi.core import pages
from dfcx_scrapi.core import intents
from dfcx_scrapi.core import test_cases
from google.api_core import exceptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class TestCasesUtil(scrapi_base.ScrapiBase):
    """Util class for CX test cases"""

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
        sentiment: bool,
        agent_id: str = None) -> List[types.TestCase]:
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

        if not agent_id:
            agent_id = self.agent_id
        dfcx_testcases = test_cases.TestCases(
            creds=self.creds,
            agent_id=agent_id)
        test_cases_list = dfcx_testcases.list_test_cases(
            agent_id, include_conversation_turns=True)
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
        is_webhook_enabled: bool,
        agent_id: str = None) -> List[types.TestCase]:
        """
        Enable/disable webhooks for the given test case ids.
        Args:
            test_cases: a list of the test case ids
            is_webhook_enabled: if enable then True else False
            agent_id: The formatted CX Agent ID
        Returns:
            list of the updated test caess
        """

        if not agent_id:
            agent_id = self.agent_id
        dfcx_testcases = test_cases.TestCases(
            creds=self.creds,
            agent_id=agent_id)
        test_cases_list = dfcx_testcases.list_test_cases(
            agent_id, include_conversation_turns=True)
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

    def _reverse_dict(self, dict_):
        """Utility method that reverse the dict keys and values
            Args:
                dict_: a dictionary
            Returns:
                a reversed dictionary
        """

        return {v: k for k, v in dict_.items()}

    def _get_commons_config(
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
        dfcx_flows = flows.Flows(creds=self.creds, agent_id=agent_id)
        dfcx_pages = pages.Pages(creds=self.creds)
        dfcx_intents = intents.Intents(creds=self.creds, agent_id=agent_id)
        dfcx_intents_map = dfcx_intents.get_intents_map(agent_id=agent_id)
        dfcx_flows_map = dfcx_flows.get_flows_map(agent_id=agent_id)
        dfcx_pages_map = {}
        for flow_id in dfcx_flows_map.keys():
            dfcx_pages_map[flow_id] = dfcx_pages.get_pages_map(flow_id=flow_id)
        commons_config["flows"] = dfcx_flows
        commons_config["pages"] = dfcx_pages
        commons_config["intents"] = dfcx_intents
        commons_config["flows_map"] = dfcx_flows_map
        commons_config["pages_map"] = dfcx_pages_map
        commons_config["intents_map"] = dfcx_intents_map
        commons_config["flows_map_reverse"] = (
            self._reverse_dict(commons_config["flows_map"]))
        commons_config["intents_map_reverse"] = (
            self._reverse_dict(commons_config["intents_map"]))
        commons_config["pages_map_reverse"] = (
            {f_id:self._reverse_dict(pages_map) \
             for f_id, pages_map in dfcx_pages_map.items()})

        return commons_config

    def _get_new_test_config(
        self,
        source: dict,
        target: dict,
        test_case: types.TestCase) -> Union[types.TestConfig, None]:
        """Update the test case types.test_config to the new types.test_config
            Update the uuids of flow, page, intent by the display_name
          args:
            source: a dictionary of the source agent's flows, pages, and intents
            target: a dictionary of the target agent's flows, pages, and intents
            test_case: types.test_config object
          returns:
            types.test_config
        """
        source_flow_id = self._get_flow_id_from_test_config(test_case)
        source_page_id = self._get_page_id_from_test_config(
            test_case, source_flow_id)
        source_flow = self._get_flow_display_name_by_id(
            source_flow_id, source["flows_map"])
        source_page = self._get_page_display_name_by_id(
            source_flow_id, source_page_id, source["pages_map"])
        target_test_config = types.TestConfig()

        if test_case.test_config.flow:
            target_flow_id = self._get_flow_id_by_flow_name(
                flow_name = source_flow,
                flows_map = target["flows_map_reverse"])
            if target_flow_id:
                target_test_config.flow = target_flow_id
            else:
                return None

        elif test_case.test_config.page:
            target_flow_id = self._get_flow_id_by_flow_name(
                flow_name = source_flow,
                flows_map = target["flows_map_reverse"])
            target_page_id = self._get_page_id_by_page_name(
                flow_id = target_flow_id,
                page_name = source_page,
                pages_map = target["pages_map_reverse"])
            if target_page_id:
                target_test_config.page = target_page_id
            else:
                return None

        return target_test_config

    def _get_flow_id_from_test_config(
        self,
        test_case: types.TestCase) -> str:
        """Attempt to get the Flow ID from the Test Case Test Config."""

        if "flow" in test_case.test_config:
            return test_case.test_config.flow
        elif "page" in test_case.test_config:
            return "/".join(test_case.test_config.page.split("/")[:8])
        else:
            agent_id = "/".join(test_case.name.split("/")[:6])
            return f"{agent_id}/flows/00000000-0000-0000-0000-000000000000"

    def _get_page_id_from_test_config(
        self,
        test_case: types.TestCase,
        flow_id: str) -> str:
        """Attempt to get the Page ID from the Test Case Test Config."""

        if "page" in test_case.test_config:
            return test_case.test_config.page
        else:
            return f"{flow_id}/pages/START_PAGE"

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

        flow_id = flows_map.get(flow_name, None)

        return flow_id

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

        intent_id = intents_map.get(intent_name, None)

        return intent_id

    def _get_intent_name_by_intent_id(
        self,
        intent_id: str,
        intents_map: Dict[str, str]) -> str:
        """Attempt to get the intent display name from the Intents Map
            by the intent's display name."""

        intent_name = intents_map.get(intent_id, None)

        return intent_name

    def _get_intent_id_from_virtual_agent_output(
        self,
        virtual_agent_output: types.ConversationTurn.VirtualAgentOutput,
        target: dict) -> Union[str, None]:
        """Attempt to find the intent id from the source's agent 
        conversation_turn.virtual_agent_output triggered intent
        display name using the target's intents map
        """

        source_intent = (
          virtual_agent_output.triggered_intent.display_name
        )
        target_intent_id = self._get_intent_id_by_intent_name(
          intent_name = source_intent,
          intents_map = target["intents_map_reverse"])

        return target_intent_id

    def _get_page_id_from_virtual_agent_output(
        self,
        virtual_agent_output: types.ConversationTurn.VirtualAgentOutput,
        source: dict,
        target: dict) -> Union[str, None]:
        """Attempt to find the page id from the source's agent conversation turn
          virtual agent output page id to the target's pages map
        """

        source_page = virtual_agent_output.current_page.display_name
        source_page_id = virtual_agent_output.current_page.name
        source_flow = self._get_flow_display_name_by_id(
          flow_id = source_page_id.split("/pages/")[0],
          flows_map = source["flows_map"])
        target_flow_id = self._get_flow_id_by_flow_name(
          flow_name = source_flow,
          flows_map = target["flows_map_reverse"])
        target_page_id = self._get_page_id_by_page_name(
          flow_id = target_flow_id,
          page_name = source_page,
          pages_map = target["pages_map_reverse"])

        return target_page_id

    def _get_intent_id_from_user_input(
        self,
        user_input: types.ConversationTurn.UserInput,
        source: dict,
        target: dict) -> Union[str, None]:
        """Attempt to find the intent id from the source's agent 
          conversation turn user input intent id to the target's pages map
        """

        source_intent_id = user_input.input.intent
        source_intent = self._get_intent_name_by_intent_id(
            intent_id = source_intent_id,
            intents_map = source["intents_map"])
        target_intent_id = self._get_intent_id_by_intent_name(
            intent_name = source_intent,
            intents_map = target["intents_map_reverse"])

        return target_intent_id

    def _get_new_conversation_turns(
        self,
        source: dict,
        target: dict,
        conversation_turns: types.ConversationTurn
        ) -> Union[List[types.ConversationTurn], None]:
        """ Update the uuids of the current page and intent
            by display name in each conversation turn.
          Args:
            source: The formatted CX Agent ID
            target: The formatted CX Agent ID
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
                        user_input = user_input_intent,
                        source = source,
                        target = target
                    )
                )
                if not conv_turn.user_input.input.intent:
                    return None
            if virtual_agent_output.current_page:
                conv_turn.virtual_agent_output.current_page.name = (
                    self._get_page_id_from_virtual_agent_output(
                        virtual_agent_output = virtual_agent_output,
                        source = source,
                        target = target
                    )
                )
                if not conv_turn.virtual_agent_output.current_page.name:
                    return None
            if virtual_agent_output.triggered_intent:
                conv_turn.virtual_agent_output.triggered_intent.name = (
                    self._get_intent_id_from_virtual_agent_output(
                        virtual_agent_output = virtual_agent_output,
                        target = target
                    )
                )
                if not conv_turn.virtual_agent_output.triggered_intent.name:
                    return None
            new_conversation_turns.append(conv_turn)

        return new_conversation_turns

    def migrate_test_cases(
        self,
        source_agent: str,
        target_agent: str,
        rate_limit: int = 5) -> List[types.TestCase]:
        """The purpose of this method is to create a new set of the test cases
            from (old) a source agent to (new) a target agent.
            When the new agent (target) is created by the copy util,
            UUIDs of flows, pages, intents, and etc are newly generated.
            Therefore, the discrepencies of the uuids creates conflict
            when importing the test cases from a source to a target agent.
            To prevent this, this method helps to migrate the test cases by
            replacing the UUIDs that are relevant to a target agent. The test
            cases are only migratable if the display names of flows, pages,
            intents, and etc have the matching set in both source and target
            agents.
          Args:
            source_agent: The agent that contain the test cases for.
              Format:
                `projects/<ProjectID>/locations/<LocationID>/agents/<AgentID>`
            target_agent: The new agent where you want to migrate.
              Format:
                `projects/<ProjectID>/locations/<Location ID>/agents/<AgentID>`
          Returns:
            a list of the types.TestCase objects that are created in the
            target agent.
        """

        source_dfcx_test_cases = test_cases.TestCases(
            creds=self.creds, agent_id=source_agent)
        target_dfcx_test_cases = test_cases.TestCases(
            creds=self.creds, agent_id=target_agent)
        source_agent_tcs = source_dfcx_test_cases.list_test_cases(
            source_agent, include_conversation_turns=True)
        if not source_agent_tcs:
            raise f"source agent:{source_agent} does not have any test cases"
        new_test_cases = []
        s_commons = self._get_commons_config(agent_id=source_agent)
        t_commons = self._get_commons_config(agent_id=target_agent)
        for tc in source_agent_tcs:
            new_test_config = self._get_new_test_config(
                s_commons, t_commons, tc)
            new_conv_turns = self._get_new_conversation_turns(
                s_commons, t_commons, tc.test_case_conversation_turns)
            new_last_test_conv_turns = self._get_new_conversation_turns(
                s_commons, t_commons, tc.last_test_result.conversation_turns)
            if None in [
                new_test_config,
                new_conv_turns,
                new_last_test_conv_turns]:
                if not new_test_config:
                    logging.warning(
                        f"test_case: {tc.display_name} "\
                        f"Reason: test_config is None.")
                elif not new_conv_turns:
                    logging.warning(
                        f"test_case: {tc.display_name} "\
                        f"Reason: test_conversation_turns is None.")
                elif not new_last_test_conv_turns:
                    logging.warning(
                        f"test_case: {tc.display_name} "\
                        f"Reason: last_test_result is None.")
                continue
            tc.test_config = new_test_config
            tc.test_case_conversation_turns = new_conv_turns
            tc.last_test_result.conversation_turns = new_last_test_conv_turns
            tc.name = None
            try:
                new_test_case = target_dfcx_test_cases.create_test_case(
                    test_case=tc)
                time.sleep(rate_limit)
            except exceptions.InternalServerError as err:
                logging.error(
                    "---- ERROR --- InternalServerError caught on CX.detect\
                    %s", err)
                logging.error("test_case: %s", tc.display_name)
                continue
            except exceptions.ClientError as err:
                logging.error(
                    "---- ERROR --- ClientError caught on CX.detect %s", err)
                logging.error("test_case: %s", tc.display_name)
                continue
            new_test_cases.append(new_test_case)

        return new_test_cases
