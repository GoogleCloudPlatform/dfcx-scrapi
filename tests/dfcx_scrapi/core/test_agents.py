"""Test Class for Agent Functions in SCRAPI lib."""

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

import time
import logging
import pytest
from unittest.mock import patch
from datetime import datetime

from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1.services import test_cases
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.operations import Operations

today_time = datetime.now().strftime("%d%m%Y_%H%M%S")
AGENT_NAME = f"DFCX SCRAPI - TEMP TEST AGENT {today_time}"

pytest.temp_agent = None

@pytest.fixture
def mock_agent_obj():
    return types.Agent(
        name="projects/mock-project/locations/global/agents/mock-agent-1234",
        display_name="Mock Agent",
        default_language_code="en",
        time_zone="America/Chicago"
    )

@pytest.fixture
def mock_agent_obj_kwargs(mock_agent_obj):
    mock_agent_obj.description = "This is a Mock Agent description."
    mock_agent_obj.enable_stackdriver_logging = True

    return mock_agent_obj

@patch('dfcx_scrapi.core.agents.services.agents.AgentsClient')
def test_create_agent_simple_default_region_no_kwargs(
    mock_client, mock_agent_obj):
    mock_client.return_value.create_agent.return_value = mock_agent_obj

    agents = Agents()
    res = agents.create_agent(
        project_id="mock-project", display_name="Mock Agent")

    assert isinstance(res, types.Agent)
    assert res.display_name == "Mock Agent"

@patch('dfcx_scrapi.core.agents.services.agents.AgentsClient')
def test_create_agent_with_extra_kwargs(
    mock_client, mock_agent_obj_kwargs):
    mock_client.return_value.create_agent.return_value = mock_agent_obj_kwargs

    agents = Agents()
    res = agents.create_agent(
        project_id="mock-project", display_name="Mock Agent",
        description="This is a Mock Agent description.",
        enable_stackdriver_logging = True
    )

    assert isinstance(res, types.Agent)
    assert res == mock_agent_obj_kwargs

@patch('dfcx_scrapi.core.agents.services.agents.AgentsClient')
def test_create_agent_from_obj(
    mock_client, mock_agent_obj):
    mock_client.return_value.create_agent.return_value = mock_agent_obj

    agents = Agents()
    res = agents.create_agent(project_id="mock-project", obj=mock_agent_obj)

    assert isinstance(res, types.Agent)
    assert res.display_name == "Mock Agent"

@patch('dfcx_scrapi.core.agents.services.agents.AgentsClient')
def test_create_agent_from_obj_with_kwargs(
    mock_client, mock_agent_obj_kwargs):
    mock_client.return_value.create_agent.return_value = mock_agent_obj_kwargs

    agents = Agents()
    res = agents.create_agent(
        project_id="mock-project", obj=mock_agent_obj_kwargs,
        description="This is a Mock Agent description.",
        enable_stackdriver_logging = True
        )

    assert isinstance(res, types.Agent)
    assert res.description == "This is a Mock Agent description."

# Next, Restore Agent
