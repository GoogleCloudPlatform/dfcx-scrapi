"""Unit Tests for Tools."""

# pylint: disable=redefined-outer-name
# pylint: disable=protected-access


# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from unittest.mock import patch, MagicMock
from dfcx_scrapi.core.tools import Tools
from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1 import services

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    tool_id = f"{agent_id}/tools/1234"
    display_name = "mock tool"
    description = "This is a mock tool."
    updated_description = "This is an updated mock tool."
    open_api_spec = """
    openapi: 3.0.0
    info:
    title: get_weather
    version: 1.0.0

    servers:
    - url: https://example.com

    paths:
    /get_weather_grid:
        get:
        summary: Returns the current grid information for a city and state
        operationId: get_weather_grid
        parameters:
            - name: latitude
            in: query
            required: true
            schema:
                type: string
            - name: longitude
            in: query
            required: true
            schema:
                type: string
        responses:
            '200':
            description: OK
            content:
                application/json:
                schema:
                    type: object
                    properties:
                    data:
                        type: string
    """

    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "tool_id": tool_id,
        "display_name": display_name,
        "description": description,
        "updated_description": updated_description,
        "open_api_spec": open_api_spec
        }

@pytest.fixture
def open_api_tool(test_config):
    return types.Tool.OpenApiTool(
        text_schema=test_config["open_api_spec"]
    )

@pytest.fixture
def mock_tool_obj(test_config, open_api_tool):
    return types.Tool(
        name=test_config["tool_id"],
        display_name=test_config["display_name"],
        description=test_config["description"],
        open_api_spec=open_api_tool
        )

@pytest.fixture
def mock_tool_obj_updated(test_config, open_api_tool):
    return types.Tool(
        name=test_config["tool_id"],
        display_name=test_config["display_name"],
        description=test_config["updated_description"],
        open_api_spec=open_api_tool
        )

@pytest.fixture
def mock_list_tools_pager(mock_tool_obj):
    return services.tools.pagers.ListToolsPager(
        services.tools.ToolsClient.list_tools,
        types.tool.ListToolsRequest(),
        types.tool.ListToolsResponse(tools=[mock_tool_obj]),
    )

@pytest.fixture
def mock_list_playbooks_pager(mock_playbook_obj):
    return services.playbooks.pagers.ListPlaybooksPager(
        services.playbooks.PlaybooksClient.list_playbooks,
        types.playbook.ListPlaybooksRequest(),
        types.playbook.ListPlaybooksResponse(playbooks=[mock_playbook_obj]),
    )

@pytest.fixture(autouse=True)
def mock_client(test_config):
    """Fixture to create a mocked ToolsClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.tools.services.tools.ToolsClient") as mock_client:

        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client 

# Test get_tools_map
def test_get_tools_map(mock_client, mock_list_tools_pager, test_config):
    mock_client.return_value.list_tools.return_value = mock_list_tools_pager
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.get_tools_map(agent_id=test_config["agent_id"])

    assert isinstance(res, dict)
    assert test_config["tool_id"] in res
    assert res[test_config["tool_id"]] == test_config["display_name"]

# Test get_tools_map (reversed)
def test_get_tools_map_reversed(
    mock_client, mock_list_tools_pager, test_config):
    mock_client.return_value.list_tools.return_value = mock_list_tools_pager
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.get_tools_map(agent_id=test_config["agent_id"], reverse=True)

    assert isinstance(res, dict)
    assert test_config["display_name"] in res
    assert res[test_config["display_name"]] == test_config["tool_id"]

# Test list_tools
def test_list_tools(mock_client, mock_list_tools_pager, test_config):
    mock_client.return_value.list_tools.return_value = mock_list_tools_pager
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.list_tools(agent_id=test_config["agent_id"])

    assert isinstance(res, list)
    assert isinstance(res[0], types.Tool)

# Test get_tool
def test_get_tool(mock_client, mock_tool_obj, test_config):
    mock_client.return_value.get_tool.return_value = mock_tool_obj
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.get_tool(tool_id=test_config["tool_id"])

    assert isinstance(res, types.Tool)
    assert res.display_name == test_config["display_name"]

# Test create_tool
def test_create_tool_from_kwargs(
    mock_client, mock_tool_obj, test_config):
    mock_client.return_value.create_tool.return_value = mock_tool_obj
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.create_tool(
        agent_id=test_config["agent_id"],
        display_name=test_config["display_name"]
        )
    assert isinstance(res, types.Tool)
    assert res.display_name == test_config["display_name"]

def test_create_tool_from_proto_object(
    mock_client, mock_tool_obj, test_config):
    mock_client.return_value.create_tool.return_value = mock_tool_obj
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.create_tool(
        agent_id=test_config["agent_id"],
        obj=mock_tool_obj
        )
    assert isinstance(res, types.Tool)
    assert res.display_name == test_config["display_name"]

# Test delete_tool with tool_id
def test_delete_tool_with_tool_id(mock_client, test_config):
    tools = Tools(agent_id=test_config["agent_id"])
    tools.delete_tool(tool_id=test_config["tool_id"])
    mock_client.return_value.delete_tool.assert_called_once_with(
        name=test_config["tool_id"]
        )

# Test delete_tool with obj
def test_delete_tool_with_obj(mock_client, mock_tool_obj, test_config):
    tools = Tools(agent_id=test_config["agent_id"])
    tools.delete_tool(obj=mock_tool_obj)
    mock_client.return_value.delete_tool.assert_called_once_with(
        name=test_config["tool_id"]
        )

# Test update_tool with kwargs
def test_update_tool_with_kwargs(
    mock_client, mock_tool_obj_updated, test_config):
    mock_client.return_value.update_tool.return_value = mock_tool_obj_updated
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.update_tool(
        tool_id=test_config["tool_id"],
        description=test_config["updated_description"]
        )

    assert isinstance(res, types.Tool)
    assert res.description == test_config["updated_description"]

# Test building tool objects
def test_build_open_api_tool_no_description(test_config):
    tools = Tools(agent_id=test_config["agent_id"])
    tool = tools.build_open_api_tool(
        display_name=test_config["display_name"],
        spec=test_config["open_api_spec"],
    )

    assert isinstance(tool, types.Tool)
    assert tool.display_name == test_config["display_name"]
    assert tool.description == ""

def test_build_open_api_tool_with_description(test_config):
    tools = Tools(agent_id=test_config["agent_id"])
    tool = tools.build_open_api_tool(
        display_name=test_config["display_name"],
        spec=test_config["open_api_spec"],
        description=test_config["description"]
    )

    assert isinstance(tool, types.Tool)
    assert tool.display_name == test_config["display_name"]
    assert tool.description == test_config["description"]
