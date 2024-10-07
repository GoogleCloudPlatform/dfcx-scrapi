"""Unit Tests for Playbooks."""

# pylint: disable=redefined-outer-name
# pylint: disable=protected-access


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
from unittest.mock import patch, MagicMock
from dfcx_scrapi.core.playbooks import Playbooks
from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1 import services
from google.protobuf import field_mask_pb2

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    playbook_id = f"{agent_id}/playbooks/1234"
    goal = """You are a Google caliber software engineer that helps users write
        code."""
    instructions_list = [
        "Help the users write code snippets in python.",
        "Use ${TOOL: PLACEHOLDER} to help write code!"
        ]
    instructions_str = """
- Step 1
  - Step 1.1
- Step 2
  - Step 2.1
    - Step 2.1.1
    - Step 2.1.2
     - Step 2.1.2.1
- Step 3
"""
    instructions_proto_from_list = types.Playbook.Instruction(
        steps=[
        types.Playbook.Step(
            text="Help the users write code snippets in python."
            ),
        types.Playbook.Step(
            text="Use ${TOOL: PLACEHOLDER} to help write code!"
            )
            ]
        )

    # Note that we don't want any leading `-` in the final proto text because
    # the UI / console automatically adds this in. If you include the `-` then
    # you will end up with double leading `- -` in the console.
    instructions_proto_from_str = types.Playbook.Instruction(
        steps=[
            types.Playbook.Step(
                text="Step 1",
                steps=[
                    types.Playbook.Step(
                        text="Step 1.1"
                    )
                ]
            ),
            types.Playbook.Step(
                text="Step 2",
                steps=[
                    types.Playbook.Step(
                        text="Step 2.1",
                        steps=[
                            types.Playbook.Step(
                                text="Step 2.1.1"
                            ),
                            types.Playbook.Step(
                                text="Step 2.1.2",
                                steps=[
                                    types.Playbook.Step(
                                        text="Step 2.1.2.1"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            types.Playbook.Step(
                text="Step 3"
            )
        ]
    )

    playbook_version_description = "v1.0"

    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "playbook_id": playbook_id,
        "goal": goal,
        "instructions_list": instructions_list,
        "instructions_str": instructions_str,
        "instructions_proto_from_list": instructions_proto_from_list,
        "instructions_proto_from_str": instructions_proto_from_str,
        "playbook_version_description": playbook_version_description
    }

@pytest.fixture
def mock_playbook_obj_empty_instructions(test_config):
    return types.Playbook(
        name=test_config["playbook_id"],
        display_name="mock playbook",
        goal=test_config["goal"]
    )

@pytest.fixture
def mock_playbook_obj_list(test_config):
    return types.Playbook(
        name=test_config["playbook_id"],
        display_name="mock playbook",
        goal=test_config["goal"],
        instruction=test_config["instructions_proto_from_list"]
    )

@pytest.fixture
def mock_playbook_obj_str(test_config):
    return types.Playbook(
        name=test_config["playbook_id"],
        display_name="mock playbook",
        goal=test_config["goal"],
        instruction=test_config["instructions_proto_from_str"]
    )

@pytest.fixture
def mock_playbook_version_obj_no_description(
    test_config, mock_playbook_obj_empty_instructions):
    return types.PlaybookVersion(
        name=test_config["playbook_id"],
        playbook=mock_playbook_obj_empty_instructions,
    )

@pytest.fixture
def mock_playbook_version_obj_with_description(
    test_config, mock_playbook_obj_empty_instructions):
    return types.PlaybookVersion(
        name=test_config["playbook_id"],
        description=test_config["playbook_version_description"],
        playbook=mock_playbook_obj_empty_instructions,
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
def mock_updated_playbook_obj(mock_playbook_obj_list):
    mock_playbook_obj_list.display_name = "mock playbook updated"
    return mock_playbook_obj_list


@pytest.fixture
def mock_list_playbooks_pager(mock_playbook_obj_list):
    return services.playbooks.pagers.ListPlaybooksPager(
        services.playbooks.PlaybooksClient.list_playbooks,
        types.playbook.ListPlaybooksRequest(),
        types.playbook.ListPlaybooksResponse(
            playbooks=[mock_playbook_obj_list]),
    )


@pytest.fixture(autouse=True)
def mock_client(test_config):
    """Fixture to create a mocked PlaybooksClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient") as mock_client, \
        patch("dfcx_scrapi.core.agents.Agents.__init__") as mock_agents_init:

        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()
        mock_agents_init.return_value = None

        yield mock_client 

@pytest.fixture
def mock_agents_client(test_config):
    """Fixture to create a mocked AgentsClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.agents.services.agents.AgentsClient") as mock_client:
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client # Return control to test method

# Test get_playbooks_map
def test_get_playbooks_map(mock_client, mock_list_playbooks_pager, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.list_playbooks.return_value = mock_list_playbooks_pager # pylint: disable=C0301
    res = pb.get_playbooks_map(agent_id=test_config["agent_id"])

    assert isinstance(res, dict)
    assert test_config["playbook_id"] in res
    assert res[test_config["playbook_id"]] == "mock playbook"


# Test list_playbooks
def test_list_playbooks(mock_client, mock_list_playbooks_pager, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.list_playbooks.return_value = mock_list_playbooks_pager # pylint: disable=C0301
    res = pb.list_playbooks()

    assert isinstance(res, list)
    assert isinstance(res[0], types.Playbook)


# Test get_playbook
def test_get_playbook(mock_client, mock_playbook_obj_list, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.get_playbook.return_value = mock_playbook_obj_list
    res = pb.get_playbook(playbook_id=test_config["playbook_id"])

    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook"


# Test create_playbook
def test_create_playbook_from_kwargs_instruction_list(
        mock_client, mock_playbook_obj_list, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.create_playbook.return_value = mock_playbook_obj_list # pylint: disable=C0301
    res = pb.create_playbook(
        agent_id=test_config["agent_id"],
        display_name="mock playbook",
        goal=test_config["goal"],
        instructions=test_config["instructions_list"]
    )
    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook"
    assert res.instruction == test_config["instructions_proto_from_list"]

def test_create_playbook_from_kwargs_instruction_str(
    mock_client, mock_playbook_obj_str, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.create_playbook.return_value = mock_playbook_obj_str # pylint: disable=C0301
    res = pb.create_playbook(
        agent_id=test_config["agent_id"],
        display_name="mock playbook",
        goal=test_config["goal"],
        instructions=test_config["instructions_str"]
    )
    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook"
    assert res.instruction == test_config["instructions_proto_from_str"]

def test_create_playbook_from_proto_object(
    mock_client, mock_playbook_obj_list, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.create_playbook.return_value = mock_playbook_obj_list # pylint: disable=C0301
    res = pb.create_playbook(
        agent_id=test_config["agent_id"],
        obj=mock_playbook_obj_list
    )
    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook"


# Test update_playbook
def test_update_playbook_with_obj(
    mock_client, mock_updated_playbook_obj, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.update_playbook.return_value = (
        mock_updated_playbook_obj
    )
    res = pb.update_playbook(
        playbook_id=test_config["playbook_id"],
        obj=mock_updated_playbook_obj
    )

    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook updated"


def test_update_playbook_with_kwargs(
    mock_client, mock_playbook_obj_list, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_client.return_value.get_playbook.return_value = mock_playbook_obj_list
    mock_client.return_value.update_playbook.return_value = mock_playbook_obj_list # pylint: disable=C0301
    res = pb.update_playbook(
        playbook_id=test_config["playbook_id"],
        display_name="mock playbook updated"
    )

    assert isinstance(res, types.Playbook)
    assert res.display_name == "mock playbook updated"

# Test the playbook kwarg processing helper methods
def test_process_playbook_kwargs_display_name(
        mock_playbook_obj_str, mock_updated_playbook_obj, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    kwargs = {"display_name": "mock playbook updated"}

    expected_mask = field_mask_pb2.FieldMask(paths=["display_name"])
    playbook, mask = pb.process_playbook_kwargs(mock_playbook_obj_str, **kwargs)

    assert mock_updated_playbook_obj.display_name == playbook.display_name
    assert expected_mask == mask

def test_process_playbook_kwargs_instruction_list(
        mock_playbook_obj_empty_instructions,
        mock_playbook_obj_list, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])

    # patch the object so we can track the internal method call
    with patch.object(
        pb, "build_instructions_from_list",
        wraps=pb.build_instructions_from_list) as mock_build_instructions:

        kwargs = {"instructions": test_config["instructions_list"]}
        expected_mask = field_mask_pb2.FieldMask(paths=["instruction"])

        playbook, mask = pb.process_playbook_kwargs(
            mock_playbook_obj_empty_instructions, **kwargs)

        assert mock_playbook_obj_list.instruction == playbook.instruction
        assert expected_mask == mask
        mock_build_instructions.assert_called_once_with(
            test_config["instructions_list"])

def test_process_playbook_kwargs_instruction_str(
        mock_playbook_obj_empty_instructions,
        mock_playbook_obj_str, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])

    # patch the object so we can track the internal method call
    with patch.object(
        pb, "build_instructions_from_string",
        wraps=pb.build_instructions_from_string) as mock_build_instructions:

        kwargs = {"instructions": test_config["instructions_str"]}
        expected_mask = field_mask_pb2.FieldMask(paths=["instruction"])

        playbook, mask = pb.process_playbook_kwargs(
            mock_playbook_obj_empty_instructions, **kwargs)

        assert mock_playbook_obj_str.instruction == playbook.instruction
        assert expected_mask == mask
        mock_build_instructions.assert_called_once_with(
            test_config["instructions_str"]
        )

def test_process_playbook_kwargs_instruction_obj(
        mock_playbook_obj_empty_instructions,
        mock_playbook_obj_str, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    kwargs = {"instructions": test_config["instructions_proto_from_str"]}
    expected_mask = field_mask_pb2.FieldMask(paths=["instruction"])

    playbook, mask = pb.process_playbook_kwargs(
        mock_playbook_obj_empty_instructions, **kwargs)

    assert mock_playbook_obj_str.instruction == playbook.instruction
    assert expected_mask == mask

# Test delete_playbook
def test_delete_playbook(mock_client, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    pb.delete_playbook(playbook_id=test_config["playbook_id"])
    mock_client.return_value.delete_playbook.assert_called()

# Test set_default_playbook
def test_set_default_playbook(mock_agents_client, mock_agent_obj, test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    mock_agents_client.return_value.get_agent.return_value = mock_agent_obj
    mock_agents_client.return_value.update_agent.return_value = mock_agent_obj
    pb.set_default_playbook(playbook_id=test_config["playbook_id"])

    assert mock_agent_obj.start_playbook == test_config["playbook_id"]

# Test build instruction helpers
def test_build_instructions_from_list(test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.build_instructions_from_list(
        instructions=test_config["instructions_list"])

    assert res == test_config["instructions_proto_from_list"]

def test_build_instructions_from_str(test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])
    res = pb.build_instructions_from_string(
        instructions=test_config["instructions_str"])

    assert res == test_config["instructions_proto_from_str"]

def test_parse_steps_simple_list(test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])

    lines = [
        "Step 1",
        "Step 2",
        "Step 3"
    ]

    expected_steps = [
        types.Playbook.Step(text="Step 1"),
        types.Playbook.Step(text="Step 2"),
        types.Playbook.Step(text="Step 3")
    ]

    steps, next_index = pb.parse_steps(lines, 0, 0)
    assert steps == expected_steps
    assert next_index == 3

def test_parse_steps_nested_list(test_config):
    pb = Playbooks(agent_id=test_config["agent_id"])

    lines = [
        "- Step 1",
        "  - Step 1.1",
        "- Step 2",
        "  - Step 2.1",
        "    - Step 2.1.1",
        "    - Step 2.1.2",
        "     - Step 2.1.2.1",
        "- Step 3"
        ]

    steps, next_index = pb.parse_steps(lines, 0, 0)
    assert steps == test_config["instructions_proto_from_str"].steps
    assert next_index == 8

def test_create_playbook_version_no_description(
        mock_client, test_config, mock_playbook_version_obj_no_description):
    pb = Playbooks(agent_id=test_config["agent_id"])

    mock_client.return_value.create_playbook_version.return_value = mock_playbook_version_obj_no_description

    res = pb.create_playbook_version(playbook_id=test_config["playbook_id"])

    mock_client.return_value.create_playbook_version.assert_called()
    assert isinstance(res, types.PlaybookVersion)
    assert res.playbook.name == test_config["playbook_id"]
    assert res.description == ""

def test_create_playbook_version_with_description(
        mock_client, test_config, mock_playbook_version_obj_with_description):
    pb = Playbooks(agent_id=test_config["agent_id"])

    mock_client.return_value.create_playbook_version.return_value = mock_playbook_version_obj_with_description

    res = pb.create_playbook_version(playbook_id=test_config["playbook_id"])

    mock_client.return_value.create_playbook_version.assert_called()
    assert isinstance(res, types.PlaybookVersion)
    assert res.playbook.name == test_config["playbook_id"]
    assert res.description == test_config["playbook_version_description"]
