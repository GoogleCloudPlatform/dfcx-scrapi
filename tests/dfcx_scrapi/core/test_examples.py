"""Unit Tests for Examples."""

# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
# pylint: disable=missing-function-docstring

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
from dfcx_scrapi.core.examples import Examples
from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1 import services

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    playbook_id = f"{agent_id}/playbooks/1234"
    example_id = f"{playbook_id}/examples/9876"
    tool_id = f"{agent_id}/tools/4321"
    display_name = "test_example"
    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "playbook_id": playbook_id,
        "example_id": example_id,
        "tool_id": tool_id,
        "display_name": display_name
        }

@pytest.fixture
def mock_example_obj(test_config):
    tool_use = types.ToolUse()
    tool_use.tool = test_config["tool_id"]
    tool_use.action = "places_search_tool"
    tool_use.input_action_parameters = {
        "preferences": "dim sum restaurant",
        "city": "Hoboken"
        }
    tool_use.output_action_parameters = {
    "results": [
        {
        "address": "512 Washington St, Hoboken, NJ 07030, United States",
        "name": "South Lions Dim Sum & Tea",
        "user_ratings_total": 141,
        },
        {
        "name": "Precious Chinese & Japanese Cuisine",
        "address": "128 Washington St, Hoboken, NJ 07030, United States",
        "user_ratings_total": 278,
        },
        {
        "name": "Keming",
        "user_ratings_total": 224,
        "address": "1006 Washington St, Hoboken, NJ 07030, United States"
        }
    ]
    }
    action = types.Action()
    action.tool_use = tool_use

    return types.Example(
        name=test_config["example_id"],
        display_name=test_config["display_name"],
        actions=[action]
        )

@pytest.fixture
def mock_updated_example_obj(mock_example_obj):
    mock_example_obj.display_name = "updated_test_example"
    return mock_example_obj

@pytest.fixture
def mock_list_examples_pager(mock_example_obj):
    return services.examples.pagers.ListExamplesPager(
        services.examples.ExamplesClient.list_examples,
        types.example.ListExamplesRequest(),
        types.example.ListExamplesResponse(examples=[mock_example_obj]),
        )

@pytest.fixture(autouse=True)
def mock_client(test_config):
    """Fixture to create mocked ExamplesClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.examples.services.examples.ExamplesClient") as mock_client, \
        patch("dfcx_scrapi.core.playbooks.Playbooks.__init__") as mock_playbooks_init, \
        patch("dfcx_scrapi.core.tools.Tools.__init__") as mock_tools_init:

        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()
        mock_playbooks_init.return_value = None
        mock_tools_init.return_value = None

        yield mock_client 

# Test get_examples_map
def test_get_examples_map(mock_client, mock_list_examples_pager, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    mock_client.return_value.list_examples.return_value = (
        mock_list_examples_pager
        )
    res = ex.get_examples_map(playbook_id=test_config["playbook_id"])

    assert isinstance(res, dict)
    assert test_config["example_id"] in res
    assert res[test_config["example_id"]] == test_config["display_name"]

    print(mock_client.mock_calls)

# Test list_examples
def test_list_examples(mock_client, mock_list_examples_pager, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    mock_client.return_value.list_examples.return_value = (
    mock_list_examples_pager
    )
    res = ex.list_examples(playbook_id=test_config["playbook_id"])

    assert isinstance(res, list)
    assert isinstance(res[0], types.Example)

# Test get_example
def test_get_example(mock_client, mock_example_obj, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    mock_client.return_value.get_example.return_value = mock_example_obj
    res = ex.get_example(example_id=test_config["example_id"])

    assert isinstance(res, types.Example)
    assert res.display_name == test_config["display_name"]

# Test create_example
def test_create_example_from_kwargs(
    mock_client, mock_example_obj, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    mock_client.return_value.create_example.return_value = mock_example_obj
    res = ex.create_example(
    playbook_id=test_config["playbook_id"],
    display_name=test_config["display_name"]
    )
    assert isinstance(res, types.Example)
    assert res.display_name == test_config["display_name"]

def test_create_example_from_proto_object(
    mock_client, mock_example_obj, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    mock_client.return_value.create_example.return_value = mock_example_obj
    res = ex.create_example(
    playbook_id=test_config["playbook_id"],
    obj=mock_example_obj
    )
    assert isinstance(res, types.Example)
    assert res.display_name == test_config["display_name"]

# Test update_example
def test_update_example_with_obj(
    mock_client, mock_updated_example_obj, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    mock_client.return_value.update_example.return_value = (
    mock_updated_example_obj
    )
    res = ex.update_example(
    example_id=test_config["example_id"],
    obj=mock_updated_example_obj
    )

    assert isinstance(res, types.Example)
    assert res.display_name == "updated_test_example"

def test_update_example_with_kwargs(
    mock_client, mock_example_obj, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    mock_client.return_value.get_example.return_value = mock_example_obj
    mock_client.return_value.update_example.return_value = mock_example_obj
    res = ex.update_example(
        example_id=test_config["example_id"],
        display_name="updated_test_example"
        )

    assert isinstance(res, types.Example)
    assert res.display_name == "updated_test_example"

# Test delete_example
def test_delete_example(mock_client, test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    ex.delete_example(example_id=test_config["example_id"])
    mock_client.return_value.delete_example.assert_called()

# Test get_playbook_state
def test_get_playbook_state(test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    assert ex.get_playbook_state("OK") == 1
    assert ex.get_playbook_state("CANCELLED") == 2
    assert ex.get_playbook_state("FAILED") == 3
    assert ex.get_playbook_state("ESCALATED") == 4
    assert ex.get_playbook_state("PENDING") == 5
    assert ex.get_playbook_state(None) == 0

# Test build_example_from_action_list_dict
def test_build_example_from_action_list(test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    action_list = [
    {"user_utterance": "hello"},
    {"agent_utterance": "hi there"},
    ]
    example = ex.build_example_from_action_list(
        display_name="test_example", action_list=action_list
        )
    assert isinstance(example, types.Example)
    assert example.display_name == "test_example"
    assert len(example.actions) == 2

# Test build_playbook_invocation
def test_build_playbook_invocation(test_config):
    ex = Examples(agent_id=test_config["agent_id"])
    ex.playbooks_map = {"test_playbook": test_config["playbook_id"]}

    action = {"playbook_name": "test_playbook"}
    pb_inv = ex.build_playbook_invocation(action)
    assert isinstance(pb_inv, types.PlaybookInvocation)
    assert pb_inv.playbook == test_config["playbook_id"]
