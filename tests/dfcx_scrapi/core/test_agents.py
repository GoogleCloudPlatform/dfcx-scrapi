"""Test Class for Agent Methods in SCRAPI."""

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
from unittest.mock import MagicMock, patch

import pytest
from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1.services.agents import (
    AgentsClient,
    pagers,
)
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core.agents import Agents


@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/a1b2c3d4-e5f6-7890-1234-567890abcdef"
    display_name = "My Agent Display Name"
    default_id = "00000000-0000-0000-0000-000000000000"
    start_flow = f"{agent_id}/flows/{default_id}"
    start_playbook = f"{agent_id}/playbooks/{default_id}"
    bq_dataset = "bq_dataset"
    bq_table = "bq_table"
    bq_table_full_path = f"projects/{project_id}/datasets/{bq_dataset}/tables/{bq_table}"
    return {
        "parent": parent,
        "project_id": project_id,
        "agent_id": agent_id,
        "display_name": display_name,
        "location_id": location_id,
        "start_flow": start_flow,
        "start_playbook": start_playbook,
        "bq_dataset": bq_dataset,
        "bq_table": bq_table,
        "bq_table_full_path": bq_table_full_path
    }

@pytest.fixture
def mock_agent_obj(test_config: Dict[str, str]):
    agent_id = test_config["agent_id"]

    return types.Agent(
        name=agent_id,
        display_name=f"{test_config['display_name']}",
        default_language_code="en",
        time_zone="America/Chicago",
        start_flow=test_config["start_flow"],
        advanced_settings=types.AdvancedSettings(
            logging_settings=types.AdvancedSettings.LoggingSettings(
                enable_stackdriver_logging=False,
                enable_interaction_logging=False
            )
        ),
        bigquery_export_settings=types.BigQueryExportSettings(
            enabled=False
        )
    )

@pytest.fixture
def mock_agent_obj_playbook(test_config: Dict[str, str]):
    return types.Agent(
        name=test_config["agent_id"],
        display_name=test_config["display_name"],
        default_language_code="en",
        time_zone="America/Chicago",
        start_playbook=test_config["start_playbook"]
    )

@pytest.fixture
def mock_agent_obj_kwargs(mock_agent_obj: types.Agent):
    mock_agent_obj.description = "This is a Mock Agent description."
    mock_agent_obj.enable_stackdriver_logging = True

    return mock_agent_obj

@pytest.fixture
def mock_agent_obj_multiple_kwarg_changes(test_config: Dict[str, str]):
    return types.Agent(
        name=test_config["agent_id"],
        display_name="Updated Agent Display Name",
        default_language_code="es",
        time_zone="America/Chicago",
        start_flow=test_config["start_flow"]
    )

@pytest.fixture
def mock_updated_agent_obj(test_config: Dict[str, str]):
    return types.Agent(
        name=test_config["agent_id"],
        display_name="Updated Agent Display Name",
        default_language_code="en",
        time_zone="America/Chicago",
        start_flow=test_config["start_flow"],
        advanced_settings=types.AdvancedSettings(
            logging_settings=types.AdvancedSettings.LoggingSettings(
                enable_stackdriver_logging=False,
                enable_interaction_logging=False
            )
        ),
        bigquery_export_settings=types.BigQueryExportSettings(
            enabled=False
        )
    )

@pytest.fixture
def mock_updated_agent_obj_bq_settings(test_config: Dict[str, str]):
    agent_id = test_config["agent_id"]
    bq_table_full_path = test_config["bq_table_full_path"]

    return types.Agent(
        name=agent_id,
        display_name=f"{test_config['display_name']}",
        default_language_code="en",
        time_zone="America/Chicago",
        start_flow=test_config["start_flow"],
        advanced_settings=types.AdvancedSettings(
            logging_settings=types.AdvancedSettings.LoggingSettings(
                enable_stackdriver_logging=True,
                enable_interaction_logging=True
            )
        ),
        bigquery_export_settings=types.BigQueryExportSettings(
            enabled=True,
            bigquery_table=bq_table_full_path
        )
    )

@pytest.fixture
def mock_list_agents_response(mock_agent_obj: types.Agent):
    return types.agent.ListAgentsResponse(agents=[mock_agent_obj])

@pytest.fixture
def mock_list_agents_pager(mock_list_agents_response: types.ListAgentsResponse):
    return pagers.ListAgentsPager(
        AgentsClient.list_agents,
        types.agent.ListAgentsRequest(),
        mock_list_agents_response,
    )

@pytest.fixture(autouse=True)
def mock_creds(test_config: Dict[str, str]):
    """Setup fixture for Agents Class to be used with all tests."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request:
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_creds

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.list_agents")
def test_list_agents_with_location(
        mock_list_agents: MagicMock,
        mock_list_agents_pager: pagers.ListAgentsPager,
        test_config: Dict[str, str]):
    mock_list_agents.return_value = mock_list_agents_pager
    expected_request = types.ListAgentsRequest(parent=test_config["parent"])

    agent = Agents()
    agents = agent.list_agents(
        project_id=test_config["project_id"],
        location_id="global"
    )
    assert isinstance(agents, list)
    assert isinstance(agents[0], types.agent.Agent)
    assert agents[0].name == test_config["agent_id"]
    mock_list_agents.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.list_agents")
def test_list_agents_without_location(
        mock_list_agents: MagicMock,
        mock_list_agents_pager: pagers.ListAgentsPager,
        test_config: Dict[str, str]):
    mock_list_agents.return_value = mock_list_agents_pager
    expected_regions = [
        "global", "us-central1", "us-east1", "us-west1", "asia-northeast1", 
        "asia-south1", "australia-southeast1", "northamerica-northeast1", 
        "europe-west1", "europe-west2"
    ]

    agent = Agents()
    agents = agent.list_agents(project_id=test_config["project_id"])
    assert isinstance(agents, list)
    assert isinstance(agents[0], types.agent.Agent)
    assert agents[0].name == test_config["agent_id"]
    assert mock_list_agents.call_count == 10
    for region in expected_regions:
        expected_request = types.ListAgentsRequest(
            parent=f"projects/{test_config['project_id']}/locations/{region}"
        )
        mock_list_agents.assert_any_call(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.get_agent")
def test_get_agent(
        mock_get_agent: MagicMock,
        mock_agent_obj: types.Agent,
        test_config: Dict[str, str]):
    mock_get_agent.return_value = mock_agent_obj
    expected_request = types.GetAgentRequest(name=test_config["agent_id"])

    agent = Agents()
    response = agent.get_agent(test_config["agent_id"])

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == test_config["display_name"]
    mock_get_agent.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.list_agents")
def test_get_agent_by_display_name_no_location(
        mock_list_agents: MagicMock,
        test_config: Dict[str, str]):
    expected_regions = [
        "global", "us-central1", "us-east1", "us-west1", "asia-northeast1",
        "asia-south1", "australia-southeast1", "northamerica-northeast1",
        "europe-west1", "europe-west2"
    ]
    parent_stub = f"projects/{test_config['project_id']}/locations"
    agent_uuid = "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    agent_objects = [
        types.Agent(
            name=f"{parent_stub}/{region}/agents/{agent_uuid}",
            display_name=f"{test_config['display_name']} {region}") 
        for region in expected_regions
    ]

    mock_list_agents.side_effect = [
        pagers.ListAgentsPager(
            AgentsClient.list_agents,
            types.agent.ListAgentsRequest(),
            types.agent.ListAgentsResponse(agents=[agent_obj]),
        ) for agent_obj in agent_objects
    ]

    agent = Agents()
    response = agent.get_agent_by_display_name(
        test_config["project_id"],
        f"{test_config['display_name']} global"
        )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == f"{test_config['display_name']} global"
    assert mock_list_agents.call_count == 10
    for region in expected_regions:
        expected_request = types.ListAgentsRequest(
            parent=f"projects/{test_config['project_id']}/locations/{region}"
        )
        mock_list_agents.assert_any_call(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.list_agents")
def test_get_agent_by_display_name_with_region(
        mock_list_agents: MagicMock,
        mock_list_agents_pager: pagers.ListAgentsPager,
        test_config: Dict[str, str]):
    mock_list_agents.return_value = mock_list_agents_pager
    expected_request = types.ListAgentsRequest(parent=test_config["parent"])

    agent = Agents()
    response = agent.get_agent_by_display_name(
        project_id=test_config["project_id"],
        display_name=test_config["display_name"],
        region="global"
        )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == test_config["display_name"]
    mock_list_agents.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.create_agent")
def test_create_agent_with_kwargs(
        mock_create_agent: MagicMock,
        mock_agent_obj: types.Agent,
        test_config: Dict[str, str]):
    mock_create_agent.return_value = mock_agent_obj
    expected_agent = types.Agent(
        display_name=test_config["display_name"],
        default_language_code="en",
        time_zone="America/Chicago"
    )
    expected_request = types.CreateAgentRequest(
        parent=test_config["parent"],
        agent=expected_agent)

    agent = Agents()
    response = agent.create_agent(
        project_id=test_config["project_id"],
        display_name=test_config["display_name"]
    )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == test_config["display_name"]
    mock_create_agent.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.create_agent")
def test_create_agent_from_obj(
        mock_create_agent: MagicMock,
        mock_agent_obj: types.Agent,
        test_config: Dict[str, str]):
    mock_create_agent.return_value = mock_agent_obj
    expected_agent = types.Agent(
        display_name=test_config["display_name"],
        default_language_code="en",
        time_zone="America/Chicago"
    )
    expected_request = types.CreateAgentRequest(
        parent=test_config["parent"],
        agent=expected_agent)

    agents = Agents()
    response = agents.create_agent(
        project_id=test_config["project_id"], obj=expected_agent)

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == test_config["display_name"]
    mock_create_agent.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.create_agent")
def test_create_agent_from_obj_with_kwargs(
        mock_create_agent: MagicMock,
        mock_agent_obj_kwargs: types.Agent,
        test_config: Dict[str, str]):
    mock_create_agent.return_value = mock_agent_obj_kwargs
    expected_agent = types.Agent(
        display_name=test_config["display_name"],
        default_language_code="en",
        time_zone="America/Chicago",
        description="This is a Mock Agent description.",
        enable_stackdriver_logging=True,
    )
    expected_request = types.CreateAgentRequest(
        parent=test_config["parent"],
        agent=expected_agent)

    agents = Agents()
    response = agents.create_agent(
        project_id=test_config["project_id"],
        obj=expected_agent,
        description="This is a Mock Agent description.",
        enable_stackdriver_logging=True,
    )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.description == "This is a Mock Agent description."
    mock_create_agent.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.update_agent")
def test_update_agent_with_obj_no_kwargs(
        mock_update_agent: MagicMock,
        mock_agent_obj: types.Agent,
        mock_updated_agent_obj: types.Agent,
        test_config: Dict[str, str]):
    """Test to ensure no updates are made without kwargs.

    This test will pass, but to the user it might seem like it will "fail" in
    the sense that the target Agent wasn't updated with their agent proto. This
    is because it is a _requirement_ to provide the exact kwargs you want to
    update on the Agent. If you only provide the object, there's no way to know
    exactly which items you want updated without explicitly passing them in
    kwargs.
    """
    mock_update_agent.return_value = mock_agent_obj

    # The request will be sent with the 'updated' obj the user provides
    # however, the actual response will be noop
    expected_request = types.UpdateAgentRequest(
        agent=mock_updated_agent_obj,
        update_mask=field_mask_pb2.FieldMask(paths=None)
        )

    agent = Agents()
    response = agent.update_agent(
        agent_id=test_config["agent_id"],
        obj=mock_updated_agent_obj
    )
    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name != "Updated Agent Display Name"
    mock_update_agent.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.update_agent")
def test_update_agent_with_obj_and_kwargs(
        mock_update_agent: MagicMock,
        mock_updated_agent_obj: types.Agent,
        mock_agent_obj_multiple_kwarg_changes: types.Agent,
        test_config: Dict[str, str]):
    """Test to ensure obj + kwargs results in updates.
    
    This test is a continuation of the test above, which check to ensure that
    when an obj + kwargs are provided, the kwargs are updated properly, and
    ONLY the kwargs provided are updated.
    """
    mock_update_agent.return_value = mock_updated_agent_obj

    # The user can send an object where multiple fields are changed but we will
    # only update the fields provided in the method input kwargs.
    expected_request = types.UpdateAgentRequest(
        agent=mock_agent_obj_multiple_kwarg_changes,
        update_mask=field_mask_pb2.FieldMask(paths=["display_name"])
        )

    agent = Agents()
    response = agent.update_agent(
        agent_id=test_config["agent_id"],
        obj=mock_agent_obj_multiple_kwarg_changes,
        display_name="Updated Agent Display Name"
    )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == "Updated Agent Display Name"
    mock_update_agent.assert_called_once_with(expected_request)

    # Ensure lang code was not changed despite obj having changes
    assert response.default_language_code != "es"
    assert response.default_language_code == "en"

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.get_agent")
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.update_agent")
def test_update_agent_kwargs_only(
        mock_update_agent: MagicMock,
        mock_get_agent: MagicMock,
        mock_agent_obj: types.Agent,
        mock_updated_agent_obj: types.Agent,
        test_config: Dict[str, str]):
    mock_update_agent.return_value = mock_updated_agent_obj
    mock_get_agent.return_value = mock_agent_obj

    # Since the user doesn't provide the agent_obj, we'll also need to get the
    # agent for them before we update it, so we'll have 2 requests in this test
    get_request = types.GetAgentRequest(name=test_config["agent_id"])
    update_request = types.UpdateAgentRequest(
        agent=mock_updated_agent_obj,
        update_mask=field_mask_pb2.FieldMask(paths=["display_name"])
        )

    agent = Agents()
    response = agent.update_agent(
        agent_id=test_config["agent_id"],
        display_name="Updated Agent Display Name"
    )

    assert isinstance(response, types.Agent)
    assert response.name == test_config["agent_id"]
    assert response.display_name == "Updated Agent Display Name"
    mock_get_agent.assert_called_once_with(get_request)
    mock_update_agent.assert_called_once_with(update_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.delete_agent")
def test_delete_agent(
    mock_delete_agent: MagicMock,
    test_config: Dict[str, str]):
    res_str = f"Agent '{test_config['agent_id']}' successfully deleted."
    mock_delete_agent.return_value = res_str

    expected_request = types.DeleteAgentRequest(name=test_config["agent_id"])

    agent = Agents()
    response = agent.delete_agent(agent_id=test_config["agent_id"])

    assert response == res_str
    mock_delete_agent.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.get_agent")
def test_get_bq_settings(
    mock_get_agent: MagicMock,
    mock_agent_obj: types.Agent,
    test_config: Dict[str, str],
    mock_creds: MagicMock):
    mock_get_agent.return_value = mock_agent_obj
    expected_request = types.GetAgentRequest(name=test_config["agent_id"])

    agent = Agents(creds=mock_creds)
    response = agent.get_bq_settings(test_config["agent_id"])

    mock_get_agent.assert_called_once_with(expected_request)

    assert isinstance(response, dict)
    assert "advanced_settings" in response
    assert "logging_settings" in response["advanced_settings"]
    assert "enable_stackdriver_logging" in response["advanced_settings"]["logging_settings"]
    assert "enable_interaction_logging" in response["advanced_settings"]["logging_settings"]
    assert "bigquery_export_settings" in response
    assert "enabled" in response["bigquery_export_settings"]
    assert "bigquery_table" in response["bigquery_export_settings"]

@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.update_agent")
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.get_agent")
def test_update_bq_settings_with_bq_settings(
    mock_get_agent: MagicMock,
    mock_update_agent: MagicMock,
    test_config: Dict[str, str],
    mock_agent_obj: MagicMock,
    mock_updated_agent_obj_bq_settings: MagicMock):
    
    mock_get_agent.return_value = mock_agent_obj
    mock_update_agent.return_value = mock_updated_agent_obj_bq_settings
    update_request = types.UpdateAgentRequest(
        agent=mock_updated_agent_obj_bq_settings,
        update_mask=field_mask_pb2.FieldMask(
            paths=["advanced_settings", "bigquery_export_settings"]
            )
        )

    bq_settings = {
        "advanced_settings": {
            "logging_settings": {
                "enable_stackdriver_logging": True,
                "enable_interaction_logging": True
            }
        },
        "bigquery_export_settings": {
            "enabled": True,
            "bigquery_table": test_config["bq_table_full_path"]
        }
    }

    agent = Agents()
    response = agent.update_bq_settings(
        agent_id=test_config["agent_id"],
        bq_settings=bq_settings
    )

    assert isinstance(response, types.Agent)
    assert response.advanced_settings.logging_settings.enable_stackdriver_logging
    assert response.advanced_settings.logging_settings.enable_interaction_logging
    assert response.bigquery_export_settings.enabled
    assert response.bigquery_export_settings.bigquery_table == test_config["bq_table_full_path"]

    mock_update_agent.assert_called_once_with(update_request)

@patch("google.cloud.bigquery.Client")
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.update_agent")
@patch("dfcx_scrapi.core.agents.services.agents.AgentsClient.get_agent")
def test_update_bq_settings_with_kwargs(
    mock_get_agent: MagicMock,
    mock_update_agent: MagicMock,
    mock_bigquery_client: MagicMock,
    test_config: Dict[str, str],
    mock_agent_obj: MagicMock,
    mock_updated_agent_obj_bq_settings: MagicMock):
    
    mock_bq_client = mock_bigquery_client.return_value
    mock_dataset = MagicMock()
    mock_dataset.dataset_id = test_config["bq_dataset"]
    mock_table = MagicMock()
    mock_table.table_id = test_config["bq_table"]

    mock_bq_client.list_datasets.return_value = [mock_dataset]
    mock_bq_client.list_tables.return_value = [mock_table]
    
    mock_get_agent.return_value = mock_agent_obj
    mock_update_agent.return_value = mock_updated_agent_obj_bq_settings
    update_request = types.UpdateAgentRequest(
        agent=mock_updated_agent_obj_bq_settings,
        update_mask=field_mask_pb2.FieldMask(
            paths=["advanced_settings", "bigquery_export_settings"]
            )
        )

    agent = Agents()
    response = agent.update_bq_settings(
        agent_id=test_config["agent_id"],
        enable_stackdriver_logging=True,
        enable_interaction_logging=True,
        bigquery_enabled=True,
        bigquery_table=test_config["bq_table"]
    )

    assert isinstance(response, types.Agent)
    assert response.advanced_settings.logging_settings.enable_stackdriver_logging
    assert response.advanced_settings.logging_settings.enable_interaction_logging
    assert response.bigquery_export_settings.enabled
    assert response.bigquery_export_settings.bigquery_table == test_config["bq_table_full_path"]

    mock_update_agent.assert_called_once_with(update_request)

def test_update_bq_settings_no_args(test_config: Dict[str, str]):
    agent = Agents()

    with pytest.raises(ValueError) as e:
        agent.update_bq_settings(
            agent_id=test_config["agent_id"]
        )

    assert str(e.value) == "At least one setting must be provided if 'bq_settings' is not used."
