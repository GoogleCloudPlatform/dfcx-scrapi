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

from typing import Dict

from google.cloud.dialogflowcx_v3beta1 import services, types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import scrapi_base


class Tools(scrapi_base.ScrapiBase):
    """Core Class for Tools Resource methods."""
    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
        tool_id: str = None,
        tools_map: Dict[str, str] = None
    ):
        super().__init__(
            creds_path=creds_path, creds_dict=creds_dict,
            creds=creds, scope=scope
        )

        self.agent_id = agent_id
        self.tool_id = tool_id
        self.tools_map = tools_map

    @staticmethod
    def build_open_api_tool(
        display_name: str, spec: str, description: str = None):
        """Helper method to build OpenAPI tool specs."""
        return types.Tool(
            display_name=display_name,
            description=description,
            open_api_spec=types.Tool.OpenApiTool(text_schema=spec)
            )

    @scrapi_base.api_call_counter_decorator
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

    @scrapi_base.api_call_counter_decorator
    def list_tools(self, agent_id: str):
        """Returns a list of tools for a given agent"""
        request = types.tool.ListToolsRequest(parent=agent_id)
        client_options = self._set_region(agent_id)
        client = services.tools.ToolsClient(
            client_options=client_options, credentials=self.creds
        )
        response = client.list_tools(request=request)

        return list(response)

    @scrapi_base.api_call_counter_decorator
    def get_tool(self, tool_id: str):
        """Get the specified Tool ID."""
        request = types.tool.GetToolRequest(name=tool_id)
        client_options = self._set_region(tool_id)
        client = services.tools.ToolsClient(
            client_options=client_options, credentials=self.creds
        )

        return client.get_tool(request=request)

    @scrapi_base.api_call_counter_decorator
    def create_tool(self, agent_id: str, obj: types.Tool = None, **kwargs):
        """Create an Agent Tool."""

        request = types.tool.CreateToolRequest()

        if obj:
            tool_obj = obj
            tool_obj.name = ""
        else:
            tool_obj = types.Tool()

            # set optional args as tool attributes
            for key, value in kwargs.items():
                setattr(tool_obj, key, value)

        request.parent = agent_id
        request.tool = tool_obj

        client_options = self._set_region(agent_id)
        client = services.tools.ToolsClient(
            client_options=client_options, credentials=self.creds
        )

        response = client.create_tool(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def update_tool(self, tool_id: str, obj: types.Tool = None, **kwargs):
        """Update a single Tool with the specific object or kwargs."""
        if obj:
            tool = obj
            tool.name = tool_id
        else:
            tool = self.get_tool(tool_id)

        # set optional tool attributes
        for key, value in kwargs.items():
            setattr(tool, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(tool_id)
        client = services.tools.ToolsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.update_tool(tool=tool, update_mask=mask)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_tool(self, tool_id: str = None, obj: types.Tool = None):
        """Deletes a single Agent Tool resource."""
        if not tool_id:
            tool_id = self.tool_id

        if obj:
            tool_id = obj.name

        client_options = self._set_region(tool_id)
        client = services.tools.ToolsClient(
            client_options=client_options, credentials=self.creds
        )

        client.delete_tool(name=tool_id)
