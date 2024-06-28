"""Tools class for Generative Agents."""

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

from dfcx_scrapi.core import scrapi_base
from typing import Dict

# TODO (pmarlow) Pending Bug fix to remove visibility on v3beta1 service

# from google.cloud.dialogflowcx_v3beta1 import services
# from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflow_v3alpha1 import services
from google.cloud.dialogflow_v3alpha1 import types

class Tools(scrapi_base.ScrapiBase):
    """Core Class for Tools Resource methods."""
    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        scope=False,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path, creds_dict=creds_dict, scope=scope
        )

    def get_tools_map(self, agent_id: str, reverse: bool = False):
        """Returns a map of tool names to tool IDs"""
        if reverse:
            tool_map = {
                tool.display_name: tool.name
                for tool in self.list_tools(agent_id)
            }

        else:
            tool_map = {
                tool.name: tool.display_name
                for tool in self.list_tools(agent_id)
            }

        return tool_map

    def list_tools(self, agent_id: str):
        """Returns a list of tools for a given agent"""
        request = types.tool.ListToolsRequest(parent=agent_id)
        client_options = self._set_region(agent_id)
        client = services.tools.ToolsClient(
            client_options=client_options, credentials=self.creds
        )
        response = client.list_tools(request=request)

        return list(response)
