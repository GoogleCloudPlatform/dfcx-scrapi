# pylint: disable=redefined-outer-name
# pylint: disable=protected-access

import pytest
from unittest.mock import patch
from dfcx_scrapi.core.playbooks import Playbooks
from google.cloud.dialogflow_v3alpha1 import types
from google.cloud.dialogflow_v3alpha1 import services

@pytest.fixture
def test_config():
    agent_id = "projects/mock-test/locations/global/agents/a1s2d3f4"
    playbook_id = f"{agent_id}/playbooks/1234"
    goal = """You are a Google caliber software engineer that helps users write
        code."""
    steps = "Help the users write code snippets in python."
    return {
        "agent_id": agent_id,
        "playbook_id": playbook_id,
        "goal": goal,
        "steps": steps
    }

@pytest.fixture
def mock_playbook_obj(test_config):
    return types.Playbook(
        name=test_config["playbook_id"],
        display_name="mock playbook",
        goal=test_config["goal"],
        steps=test_config["steps"]
    )


@pytest.fixture
def mock_agent_obj(test_config):
    return types.Agent(
        name=test_config["agent_id"],
        display_name="mock agent",
        default_language_code="en",
        time_zone="America/Chicago"
    )

@pytest.fixture
def mock_updated_playbook_obj(mock_playbook_obj):
    mock_playbook_obj.display_name = "mock playbook updated"
    return mock_playbook_obj


@pytest.fixture
def mock_list_playbooks_pager(mock_playbook_obj):
    return services.playbooks.pagers.ListPlaybooksPager(
        services.playbooks.PlaybooksClient.list_playbooks,
        types.playbook.ListPlaybooksRequest(),
        types.playbook.ListPlaybooksResponse(playbooks=[mock_playbook_obj]),
    )

# Test get_playbooks_map
@patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient")
def test_get_playbooks_map(mock_client, mock_list_playbooks_pager, test_config):
    mock_client.return_value.list_playbooks.return_value = mock_list_playbooks_pager
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.get_playbooks_map(agent_id=test_config["agent_id"])

    assert isinstance(res, dict)
    assert test_config["playbook_id"] in res
    assert res[test_config["playbook_id"]] == "mock playbook"


# Test list_playbooks
@patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient")
def test_list_playbooks(mock_client, mock_list_playbooks_pager, test_config):
    mock_client.return_value.list_playbooks.return_value = mock_list_playbooks_pager
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.list_playbooks()

    assert isinstance(res, list)
    assert isinstance(res[0], types.Playbook)


# Test get_playbook
@patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient")
def test_get_playbook(mock_client, mock_playbook_obj, test_config):
    mock_client.return_value.get_playbook.return_value = mock_playbook_obj
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.get_playbook(playbook_id=test_config["playbook_id"])

    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook"


# Test create_playbook
@patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient")
def test_create_playbook(mock_client, mock_playbook_obj, test_config):
    mock_client.return_value.create_playbook.return_value = mock_playbook_obj
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.create_playbook(
        agent_id=test_config["agent_id"],
        display_name="mock playbook",
        goal=test_config["goal"],
        steps=test_config["steps"]
    )
    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook"


# Test update_playbook
@patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient")
def test_update_playbook_with_obj(
    mock_client, mock_updated_playbook_obj, test_config):
    mock_client.return_value.update_playbook.return_value = (
        mock_updated_playbook_obj
    )
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.update_playbook(
        playbook_id=test_config["playbook_id"],
        obj=mock_updated_playbook_obj
    )

    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook updated"


@patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient")
def test_update_playbook_with_kwargs(
    mock_client, mock_playbook_obj, test_config):
    mock_client.return_value.get_playbook.return_value = mock_playbook_obj
    mock_client.return_value.update_playbook.return_value = mock_playbook_obj
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.update_playbook(
        playbook_id=test_config["playbook_id"],
        display_name="mock playbook updated"
    )

    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook updated"


# Test delete_playbook
@patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient")
def test_delete_playbook(mock_client, mock_playbook_obj, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    pb.delete_playbook(playbook_id=test_config["playbook_id"])
    mock_client.assert_called_once_with(
        name=test_config["playbook_id"]
    )


# Test set_default_playbook
@patch("dfcx_scrapi.core.playbooks.services.agents.AgentsClient")
def test_set_default_playbook(mock_client, mock_agent_obj, test_config):
    mock_client.return_value.get_agent.return_value = mock_agent_obj
    mock_client.return_value.update_agent.return_value = mock_agent_obj
    pb = Playbooks(agent_id=test_config["agent_id"])
    pb.set_default_playbook(playbook_id=test_config["playbook_id"])
    assert mock_agent_obj.start_playbook == test_config["playbook_id"]
