"""Test Class for Agent Methods in SCRAPI."""

# pylint: disable=redefined-outer-name

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

import pytest
from unittest.mock import patch

from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1 import services

from dfcx_scrapi.core.agents import Agents

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    display_name = "My Agent Display Name"
    default_id = "00000000-0000-0000-0000-000000000000"
    start_flow = f"{agent_id}/flows/{default_id}"
    start_playbook = f"{agent_id}/playbooks/{default_id}"
    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "display_name": display_name,
        "location_id": location_id,
        "start_flow": start_flow,
        "start_playbooks": start_playbook
    }

@pytest.fixture
def mock_agent_obj_flow(test_config):
    return types.Agent(
        name=test_config["agent_id"],
        display_name=test_config["display_name"],
        default_language_code="en",
        time_zone="America/Chicago",
        start_flow=test_config["start_flow"]
    )

@pytest.fixture
def mock_agent_obj_playbook(test_config):
    return types.Agent(
        name=test_config["agent_id"],
        display_name=test_config["display_name"],
        default_language_code="en",
        time_zone="America/Chicago",
        start_playbook=test_config["start_playbook"]
    )

@pytest.fixture
def mock_agent_obj_kwargs(mock_agent_obj_flow):
    mock_agent_obj_flow.description = "This is a Mock Agent description."
    mock_agent_obj_flow.enable_stackdriver_logging = True

    return mock_agent_obj_flow

@pytest.fixture
def mock_updated_agent_obj(mock_agent_obj_flow):
    mock_agent_obj_flow.display_name = "Updated Agent Display Name"
    return mock_agent_obj_flow

@pytest.fixture
def mock_list_agents_response(mock_agent_obj_flow):
    return types.agent.ListAgentsResponse(agents=[mock_agent_obj_flow])

@pytest.fixture
def mock_list_agents_pager(mock_list_agents_response):
    return services.agents.pagers.ListAgentsPager(
        services.agents.AgentsClient.list_agents,
        types.agent.ListAgentsRequest(),
        mock_list_agents_response,
    )

# Test list_agents with location_id
@patch("dfcx_scrapi.core.agents.Agents._list_agents_client_request")
def test_list_agents_with_location(mock_list_agents_client_request,
                              mock_agent_obj_flow,
                              test_config
                              ):
    mock_list_agents_client_request.return_value = [mock_agent_obj_flow]
    agent = Agents()
    agents = agent.list_agents(
        project_id=test_config["project_id"],
        location_id="global"
    )
    assert isinstance(agents, list)
    assert isinstance(agents[0], types.agent.Agent)
    assert agents[0].name == test_config["agent_id"]

# Test list_agents without location_id
@patch("dfcx_scrapi.core.agents.Agents._list_agents_client_request")
def test_list_agents_without_location(mock_list_agents_client_request,
                              mock_agent_obj_flow,
                              test_config
                              ):
    mock_list_agents_client_request.return_value = [mock_agent_obj_flow]
    agent = Agents()
    agents = agent.list_agents(project_id=test_config["project_id"])
    assert isinstance(agents, list)
    assert isinstance(agents[0], types.agent.Agent)
    assert agents[0].name == test_config["agent_id"]

# Test get_agent
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_get_agent(mock_client, mock_agent_obj_flow, test_config):
    mock_client.return_value.get_agent.return_value = mock_agent_obj_flow
    agent = Agents()
    response = agent.get_agent(test_config["agent_id"])
    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == test_config["display_name"]

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_get_agent_by_display_name_no_location(
    mock_client, mock_agent_obj_flow, mock_list_agents_pager, test_config):
    mock_client.return_value.get_agent_by_display_name.return_value = mock_agent_obj_flow # pylint: disable=C0301
    mock_client.return_value.list_agents.return_value = mock_list_agents_pager
    agent = Agents()
    response = agent.get_agent_by_display_name(
        test_config["project_id"], test_config["display_name"]
        )

    assert response is None

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_get_agent_by_display_name_with_region(
    mock_client, mock_agent_obj_flow, mock_list_agents_pager, test_config):
    mock_client.return_value.get_agent_by_display_name.return_value = mock_agent_obj_flow # pylint: disable=C0301
    mock_client.return_value.list_agents.return_value = mock_list_agents_pager
    agent = Agents()
    response = agent.get_agent_by_display_name(
        project_id=test_config["project_id"],
        display_name=test_config["display_name"],
        region="global"
        )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == test_config["display_name"]

# Test create_agent
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_create_agent_with_kwargs(
    mock_client, mock_agent_obj_flow, test_config):
    mock_client.return_value.create_agent.return_value = mock_agent_obj_flow
    agent = Agents()
    response = agent.create_agent(
        project_id=test_config["project_id"],
        display_name=test_config["display_name"]
    )
    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == test_config["display_name"]

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_create_agent_from_obj(mock_client, mock_agent_obj_flow, test_config):
    mock_client.return_value.create_agent.return_value = mock_agent_obj_flow

    agents = Agents()
    res = agents.create_agent(
        project_id=test_config["project_id"], obj=mock_agent_obj_flow)

    assert isinstance(res, types.Agent)
    assert res.display_name == test_config["display_name"]


@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_create_agent_from_obj_with_kwargs(mock_client, mock_agent_obj_kwargs):
    mock_client.return_value.create_agent.return_value = mock_agent_obj_kwargs

    agents = Agents()
    res = agents.create_agent(
        project_id="mock-project",
        obj=mock_agent_obj_kwargs,
        description="This is a Mock Agent description.",
        enable_stackdriver_logging=True,
    )

    assert isinstance(res, types.Agent)
    assert res.description == "This is a Mock Agent description."

# Test update_agent
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_update_agent_with_obj(mock_client,
                             mock_updated_agent_obj,
                             test_config):
    mock_client.return_value.update_agent.return_value = (
        mock_updated_agent_obj
    )
    agent = Agents()
    response = agent.update_agent(
        agent_id=test_config["agent_id"],
        obj=mock_updated_agent_obj
    )
    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == "Updated Agent Display Name"

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_update_agent_with_kwargs(mock_client,
                             mock_agent_obj_flow,
                             test_config):
    mock_client.return_value.get_agent.return_value = mock_agent_obj_flow
    mock_client.return_value.update_agent.return_value = mock_agent_obj_flow
    agent = Agents()
    response = agent.update_agent(
        agent_id=test_config["agent_id"],
        display_name="Updated Agent Display Name"
    )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == "Updated Agent Display Name"

# Test delete_agent
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_delete_agent(test_config):
    agent = Agents()
    response = agent.delete_agent(agent_id=test_config["agent_id"])
    print(response)
    assert (
        response == f"Agent '{test_config['agent_id']}' successfully deleted."
    )

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_create_agent_simple_default_region_no_kwargs(
    mock_client, mock_agent_obj_flow, test_config
):
    mock_client.return_value.create_agent.return_value = mock_agent_obj_flow

    agents = Agents()
    res = agents.create_agent(
        project_id=test_config["project_id"],
        display_name=test_config["display_name"]
    )

    assert isinstance(res, types.Agent)
    assert res.display_name == test_config["display_name"]


@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient")
def test_create_agent_with_extra_kwargs(mock_client, mock_agent_obj_kwargs):
    mock_client.return_value.create_agent.return_value = mock_agent_obj_kwargs

    agents = Agents()
    res = agents.create_agent(
        project_id="mock-project",
        display_name="Mock Agent",
        description="This is a Mock Agent description.",
        enable_stackdriver_logging=True,
    )

    assert isinstance(res, types.Agent)
    assert res == mock_agent_obj_kwargs
