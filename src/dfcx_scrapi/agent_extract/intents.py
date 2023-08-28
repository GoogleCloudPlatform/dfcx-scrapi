"""Intent processing methods and functions."""

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

from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types


class Intents:
    """Intent processing methods and functions."""

    def __init__(self):
        self.common = common.Common()

    @staticmethod
    def parse_lang_code(lang_code_path: str) -> str:
        """Extract the language_code from the given file path."""

        first_parse = lang_code_path.split("/")[-1]
        lang_code = first_parse.split(".")[0]

        return lang_code

    @staticmethod
    def build_lang_code_paths(intent: types.Intent):
        """Builds dict of lang codes and file locations.

        The language_codes and paths for each file are stored in a dictionary
        inside of the Intent dataclass. This dict is access later to process
        each file and provide reporting based on each language code.
        """
        root_dir = intent.dir_path + "/trainingPhrases"

        for lang_file in os.listdir(root_dir):
            lang_code = lang_file.split(".")[0]
            lang_code_path = f"{root_dir}/{lang_file}"
            intent.training_phrases[lang_code] = {"file_path": lang_code_path}

    @staticmethod
    def build_intent_path_list(agent_local_path: str):
        """Builds a list of dirs, each representing an Intent directory.

        Ex: /path/to/agent/intents/<intent_dir>

        This dir path can be used to find the next level of information
        in the directory by appending the appropriate next dir structures like:
        - <intent_name>.json, for the Intent object metadata
        - /trainingPhrases, for the Training Phrases dir
        """
        root_dir = agent_local_path + "/intents"

        intent_paths = []

        for intent_dir in os.listdir(root_dir):
            intent_dir_path = f"{root_dir}/{intent_dir}"
            intent_paths.append(intent_dir_path)

        return intent_paths

    def process_intent_metadata(
            self, intent: types.Intent):
        """Process the metadata file for a single Intent."""
        intent.metadata_file = f"{intent.dir_path}/{intent.display_name}.json"

        try:
            with open(intent.metadata_file, "r", encoding="UTF-8") as meta_file:
                intent.data = json.load(meta_file)
                intent.resource_id = intent.data.get("name", None)
                intent.labels = intent.data.get("labels", None)
                intent.description = intent.data.get("description", None)
                intent.parameters = intent.data.get("parameters", None)

                meta_file.close()

        except FileNotFoundError:
            pass

    def process_language_codes(
            self, intent: types.Intent, stats: types.AgentData):
        """Process all training phrase lang_code files."""

        for lang_code in intent.training_phrases:
            tp_file = intent.training_phrases[lang_code]["file_path"]

            if not self.common.check_lang_code(lang_code, stats):
                continue

            with open(tp_file, "r", encoding="UTF-8") as tps:
                data = json.load(tps)
                data["name"] = f"{stats.agent_id}/intents/{intent.resource_id}"
                data["display_name"] = intent.display_name
                data["labels"] = intent.labels
                data["description"] = intent.description
                data["parameters"] = intent.parameters
                stats.intents.append(data)
                stats.total_training_phrases += len(data["trainingPhrases"])

                tps.close()

        return stats

    def process_training_phrases(
            self, intent: types.Intent, stats: types.AgentData):
        """Process the Training Phrase dir for a single Intent."""
        if "trainingPhrases" in os.listdir(intent.dir_path):
            self.build_lang_code_paths(intent)
            stats = self.process_language_codes(intent, stats)

        return stats

    def process_intent(self, intent: types.Intent, stats: types.AgentData):
        """Process a single Intent directory and associated files."""
        intent.display_name = self.common.parse_filepath(
            intent.dir_path, "intent")
        intent.display_name = self.common.clean_display_name(
            intent.display_name)

        self.process_intent_metadata(intent)
        stats = self.process_training_phrases(intent, stats)
        stats.total_intents += 1

        return stats

    def process_intents_directory(
            self, agent_local_path: str, stats: types.AgentData):
        """Processing the top level Intents Dir in the JSON Package structure.

        The following files/dirs exist under the `intents` dir:
        - <intent_display_name> Directory
          - trainingPhrases
            - <language-code>.json
          - <intent_display_name> Object

        In Dialogflow CX, the Training Phrases of each Intent are stored in
        individual .json files by language code under each Intent Display
        Name. In this method, we will process all Intent dirs, including the
        training phrase files and metadata objects for each Intent.
        """
        # Create a list of all Intent paths to iter through
        intent_paths = self.build_intent_path_list(agent_local_path)
        stats.intents = []

        for intent_path in intent_paths:
            intent = types.Intent()
            intent.dir_path = intent_path

            stats = self.process_intent(intent, stats)
            full_intent_id = f"{stats.agent_id}/intents/{intent.resource_id}"
            stats.intents_map[intent.display_name] = full_intent_id

        return stats
