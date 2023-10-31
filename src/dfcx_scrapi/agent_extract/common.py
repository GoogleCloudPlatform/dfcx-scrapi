"""Common methods and helper functions used throughout library."""

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
import re
from dfcx_scrapi.agent_extract import types

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

class Common:
    """Common methods and helper functions used throughout library."""

    @staticmethod
    def parse_filepath(in_path: str, resource_type: str) -> str:
        """Parse file path to provide quick reference for resource."""

        regex_map = {
            "flow": r".*\/flows\/([^\/]*)",
            "page": r".*\/pages\/([^\/]*)\.",
            "entity_type": r".*\/entityTypes\/([^\/]*)",
            "intent": r".*\/intents\/([^\/]*)",
            "route_group": r".*\/transitionRouteGroups\/([^\/]*)",
            "webhook": r".*\/webhooks\/([^\/]*)\."
        }
        resource_name = re.match(regex_map[resource_type], in_path).groups()[0]

        return resource_name

    @staticmethod
    def clean_display_name(display_name: str):
        """Replace cspecial haracters from map for the given display name."""
        patterns = {
            "%22": '"',
            "%23": "#",
            "%24": "$",
            "%26": "&",
            "%27": "'",
            "%28": "(",
            "%29": ")",
            "%2b": "+",
            "%2c": ",",
            "%2f": "/",
            "%3a": ":",
            "%3c": "<",
            "%3d": "=",
            "%3e": ">",
            "%3f": "?",
            "%5b": "[",
            "%5d": "]",
            "%e2%80%9c": "“",
            "%e2%80%9d": "”",
        }

        for key, value in patterns.items():
            if key in display_name:
                display_name = display_name.replace(key, value)

        return display_name

    @staticmethod
    def check_lang_code(lang_code: str, stats: types.AgentData):
        """Check to see if file lang_code matches user input lang_code."""
        return stats.lang_code == lang_code
