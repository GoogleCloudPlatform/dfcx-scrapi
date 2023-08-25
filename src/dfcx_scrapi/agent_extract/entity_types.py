"""Entity Type processing methods and functions."""

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

from typing import Dict

from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types

class EntityTypes:
    """Entity Type processing methods and functions."""

    def __init__(self):
        self.common = common.Common()

    @staticmethod
    def build_entity_type_path_list(agent_local_path: str):
        """Builds a list of dirs, each representing an Entity Type directory.

        Ex: /path/to/agent/entityTypes/<entity_type_dir>

        This dir path can then be used to find the next level of information
        in the directory by appending the appropriate next dir structures like:
        - <entity_type_name>.json, for the Entity Type object
        - /entities, for the Entities dir
        """
        root_dir = agent_local_path + "/entityTypes"

        entity_type_paths = []

        for entity_type_dir in os.listdir(root_dir):
            entity_type_dir_path = f"{root_dir}/{entity_type_dir}"
            entity_type_paths.append(entity_type_dir_path)

        return entity_type_paths

    @staticmethod
    def build_lang_code_paths(etype: types.EntityType):
        """Builds dict of lang codes and file locations.

        The language_codes and paths for each file are stored in a dictionary
        inside of the Entity Type dataclass. This dict is accessed later to
        lint each file and provide reporting based on each language code.
        """
        root_dir = etype.dir_path + "/entities"

        for lang_file in os.listdir(root_dir):
            lang_code = lang_file.split(".")[0]
            lang_code_path = f"{root_dir}/{lang_file}"
            etype.entities[lang_code] = {"file_path": lang_code_path}

    @staticmethod
    def build_excluded_phrases_path(etype: types.EntityType, lang_code: str):
        """Builds a dict of excluded phrases and file locations."""
        root_dir = etype.dir_path + "/excludedPhrases"
        lang_code_path = f"{root_dir}/{lang_code}.json"

        return lang_code_path

    @staticmethod
    def process_entity_type_metadata(etype: types.EntityType):
        """Extract metadata for Entity Type for later processing."""
        metadata_file = etype.dir_path + f"/{etype.display_name}.json"

        with open(metadata_file, "r", encoding="UTF-8") as etype_file:
            etype.data = json.load(etype_file)
            etype.resource_id = etype.data.get("name", None)
            etype.kind = etype.data.get("kind", None)
            etype.auto_expansion = etype.data.get("autoExpansionMode", None)
            etype.fuzzy_extraction = etype.data.get(
                "enableFuzzyExtraction", False)

            etype_file.close()

    def process_excluded_phrases_language_codes(
            self, data: Dict[str, str], lang_code_path: str):
        """Process all ecluded phrases lang_code files."""
        with open(lang_code_path, "r", encoding="UTF-8") as ent_file:
            new_data = json.load(ent_file)
            data["excluded_phrases"] = new_data.get("excludedPhrases", None)

        return data

    def process_excluded_phrases(self, etype: types.EntityType, lang_code: str,
                                 data: Dict[str, str]):
        """Process the excluded phrases if they exist."""
        if "excludedPhrases" in os.listdir(etype.dir_path):
            lang_code_path = self.build_excluded_phrases_path(etype, lang_code)
            data = self.process_excluded_phrases_language_codes(
                data, lang_code_path)

        return data

    def process_language_codes(
            self, etype: types.EntityType, stats: types.AgentData):
        """Process all Entity Type lang_code files."""
        for lang_code in etype.entities:
            ent_file_path = etype.entities[lang_code]["file_path"]

            if not self.common.check_lang_code(lang_code, stats):
                continue

            with open(ent_file_path, "r", encoding="UTF-8") as ent_file:
                data = json.load(ent_file)
                data["name"] = f"{stats.agent_id}/entityTypes/"\
                    f"{etype.resource_id}"
                data["display_name"] = etype.display_name
                data["kind"] = etype.kind
                data["entities"] = data.get("entities", None)
                data = self.process_excluded_phrases(etype, lang_code, data)
                stats.entity_types.append(data)

                ent_file.close()

        return stats

    def process_entities(self, etype: types.EntityType, stats: types.AgentData):
        """Process the Entity files inside of an Entity Type."""
        if "entities" in os.listdir(etype.dir_path):
            self.build_lang_code_paths(etype)
            stats = self.process_language_codes(etype, stats)

        return stats

    def process_entity_type(
            self, etype: types.EntityType, stats: types.AgentData):
        """Process a Single Entity Type dir and all subdirectories."""

        etype.display_name = self.common.parse_filepath(
            etype.dir_path, "entity_type")
        etype.display_name = self.common.clean_display_name(etype.display_name)

        self.process_entity_type_metadata(etype)
        stats = self.process_entities(etype, stats)
        stats.total_entity_types += 1

        return stats

    def process_entity_types_directory(
            self, agent_local_path: str, stats: types.AgentData):
        """Processing the Entity Types dir in the JSON Package structure."""
        # Create a list of all Entity Type paths to iter through
        entity_type_paths = self.build_entity_type_path_list(agent_local_path)

        for entity_type_path in entity_type_paths:
            etype = types.EntityType()
            etype.dir_path = entity_type_path

            stats = self.process_entity_type(etype, stats)
            full_etype_id = f"{stats.agent_id}/entityTypes/{etype.resource_id}"
            stats.entity_types_map[etype.display_name] = full_etype_id

        return stats
