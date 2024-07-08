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
from unittest.mock import patch
from dfcx_scrapi.core.tools import Tools
from google.cloud.dialogflow_v3alpha1 import types
from google.cloud.dialogflow_v3alpha1 import services

@pytest.fixture
def test_config():
    agent_id = "projects/mock-test/locations/global/agents/a1s2d3f4"
    tool_id = f"{agent_id}/tools/1234"
    display_name = "mock tool"
    return {
        "agent_id": agent_id,
        "tool_id": tool_id,
        "display_name": display_name
        }

@pytest.fixture
def mock_tool_obj(test_config):
    return types.Tool(
        name=test_config["tool_id"],
        display_name=test_config["display_name"],
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

# Test get_tools_map
@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
def test_get_tools_map(mock_client, mock_list_tools_pager, test_config):
    mock_client.return_value.list_tools.return_value = mock_list_tools_pager
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.get_tools_map(agent_id=test_config["agent_id"])

    assert isinstance(res, dict)
    assert test_config["tool_id"] in res
    assert res[test_config["tool_id"]] == test_config["display_name"]

# Test get_tools_map (reversed)
@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
def test_get_tools_map_reversed(
    mock_client, mock_list_tools_pager, test_config):
    mock_client.return_value.list_tools.return_value = mock_list_tools_pager
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.get_tools_map(agent_id=test_config["agent_id"], reverse=True)

    assert isinstance(res, dict)
    assert test_config["display_name"] in res
    assert res[test_config["display_name"]] == test_config["tool_id"]

# Test list_tools
@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
def test_list_tools(mock_client, mock_list_tools_pager, test_config):
    mock_client.return_value.list_tools.return_value = mock_list_tools_pager
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.list_tools(agent_id=test_config["agent_id"])

    assert isinstance(res, list)
    assert isinstance(res[0], types.Tool)

# Test get_tool
@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
def test_get_tool(mock_client, mock_tool_obj, test_config):
    mock_client.return_value.get_tool.return_value = mock_tool_obj
    tools = Tools(agent_id=test_config["agent_id"])
    res = tools.get_tool(tool_id=test_config["tool_id"])

    assert isinstance(res, types.Tool)
    assert res.display_name == test_config["display_name"]

# Test create_tool
@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
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

@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
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
@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
def test_delete_tool_with_tool_id(mock_client, test_config):
    tools = Tools(agent_id=test_config["agent_id"])
    tools.delete_tool(tool_id=test_config["tool_id"])
    mock_client.return_value.delete_tool.assert_called_once_with(
        name=test_config["tool_id"]
        )

# Test delete_tool with obj
@patch("dfcx_scrapi.core.tools.services.tools.ToolsClient")
def test_delete_tool_with_obj(mock_client, mock_tool_obj, test_config):
    tools = Tools(agent_id=test_config["agent_id"])
    tools.delete_tool(obj=mock_tool_obj)
    mock_client.return_value.delete_tool.assert_called_once_with(
        name=test_config["tool_id"]
        )
