"""Test Case processing methods and functions."""

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

import json
import os

from typing import Dict, List, Any

from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types


class TestCases:
    """Test Case processing methods and functions."""

    def __init__(self):
        self.common = common.Common()

    @staticmethod
    def build_test_case_path_list(agent_local_path: str):
        """Builds a list of files, each representing a test case."""
        root_dir = agent_local_path + "/testCases"

        test_case_paths = []

        for test_case in os.listdir(root_dir):
            end = test_case.split(".")[-1]
            if end == "json":
                test_case_path = f"{root_dir}/{test_case}"
                test_case_paths.append(test_case_path)

        return test_case_paths

    @staticmethod
    def get_test_case_intent_phrase_pair(
        tc: types.TestCase) -> List[Dict[str, str]]:
        """Parse Test Case and return a list of intents in use.

        This method will produce a List of Dicts where the contents of each
        dict is the Training Phrase and associated Triggered Intent as listed
        in the Test Case Conversation Turn. This information is used to compare
        the User Input training phrase with the actual training phrases that
        exist in the Intent resource.

        The dict format is as follows:
            {
                training_phrase: <training_phrase>,
                intent: <intent_display_name>
            }
        """
        intent_data = []

        if tc.conversation_turns:
            for turn in tc.conversation_turns:
                user = turn["userInput"]
                agent = turn["virtualAgentOutput"]
                intent = agent.get("triggeredIntent", None)
                phrase = user.get("input", None)

                text = phrase.get("text", None)

                if text:
                    text = text["text"]

                if intent and text:
                    intent_data.append(
                        {
                            "user_utterance": text,
                            "intent": intent["name"],
                            "status": "valid",
                            "training_phrases": [],
                        }
                    )

        return intent_data

    @staticmethod
    def get_test_case_intent_data(agent_local_path: str):
        """Collect all Intent Files and Training Phrases for Test Case."""
        intents_path = agent_local_path + "/intents"

        intent_paths = []

        for intent_dir in os.listdir(intents_path):
            intent_dir_path = f"{intents_path}/{intent_dir}"
            intent_paths.append(
                {"intent": intent_dir, "file_path": intent_dir_path}
            )

        return intent_paths

    @staticmethod
    def flatten_tp_data(tp_data: List[Any]):
        """Flatten the Training Phrase proto to a list of strings."""
        cleaned_tps = []

        for tp in tp_data["trainingPhrases"]:
            parts_list = [part["text"].lower() for part in tp["parts"]]
            cleaned_tps.append("".join(parts_list))

        return cleaned_tps

    def gather_intent_tps(self, tc: types.TestCase):
        """Collect all TPs associated with Intent data in Test Case."""
        tc.associated_intent_data = {}

        for i, pair in enumerate(tc.intent_data):
            intent_dir = tc.agent_path + "/intents/" + pair["intent"]

            try:
                if "trainingPhrases" in os.listdir(intent_dir):
                    training_phrases_path = intent_dir + "/trainingPhrases"

                    for lang_file in os.listdir(training_phrases_path):
                        # lang_code = lang_file.split(".")[0]
                        lang_code_path = f"{training_phrases_path}/{lang_file}"

                        with open(
                            lang_code_path, "r", encoding="UTF-8"
                        ) as tp_file:
                            tp_data = json.load(tp_file)
                            cleaned_tps = self.flatten_tp_data(tp_data)

                            tp_file.close()

                        tc.intent_data[i]["training_phrases"].extend(
                            cleaned_tps
                        )
                        tc.associated_intent_data[pair["intent"]] = cleaned_tps

            except FileNotFoundError:
                tc.intent_data[i]["status"] = "invalid_intent"
                tc.has_invalid_intent = True
                continue

        return tc

    def process_test_case(self, tc: types.TestCase, stats: types.AgentData):
        """Process a single Test Case file."""

        with open(tc.dir_path, "r", encoding="UTF-8") as tc_file:
            tc.data = json.load(tc_file)
            tc.resource_id = tc.data.get("name", None)
            tc.display_name = tc.data.get("displayName", None)
            tc.tags = tc.data.get("tags", None)
            tc.conversation_turns = tc.data.get(
                "testCaseConversationTurns", None
            )
            tc.test_config = tc.data.get("testConfig", None)

            full_tc_id = f"{stats.agent_id}/testCases/{tc.resource_id}"
            tc.data["name"] = full_tc_id
            stats.test_cases.append(tc.data)

            tc_file.close()

        return stats

    def process_test_cases_directory(
            self, agent_local_path: str, stats: types.AgentData):
        """Processing the test cases dir in the JSON package structure."""
        test_case_paths = self.build_test_case_path_list(agent_local_path)
        stats.total_test_cases = len(test_case_paths)

        for test_case in test_case_paths:
            tc = types.TestCase()
            tc.dir_path = test_case
            tc.agent_path = agent_local_path
            stats = self.process_test_case(tc, stats)

        return stats
