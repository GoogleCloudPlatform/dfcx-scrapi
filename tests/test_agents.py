"""Test Class for Agent Functions in SCRAPI lib."""

# Copyright 2021 Google LLC
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

import logging
import time
from datetime import datetime
# from typing import List, Dict

import pytest
import google.cloud.dialogflowcx_v3beta1.types as types

DEV = True  # Set flag to disable some tests while in development

today_time = datetime.now().strftime("%d%m%Y_%H%M%S")
AGENT_NAME = "DFCX SCRAPI - TEMP TEST AGENT {}".format(today_time)
CREDS_PATH = None
PROJECT_ID = None

pytest.temp_agent = None

def test_create_agent(agents, project):
    """Tests the SCRAPI method create_agent from core/agents.py"""
    # agents = Agents(creds_path=creds)
    pytest.temp_agent = agents.create_agent(
        project, AGENT_NAME
    )

    assert isinstance(pytest.temp_agent, types.Agent)
    assert pytest.temp_agent.display_name == AGENT_NAME

    return pytest.temp_agent


def test_restore_agent(agents, ops, gcs_bucket):
    """Tests the SCRAPI method restore_agent from core/agents.py"""
    lro = agents.restore_agent(
        pytest.temp_agent.name,
        gcs_bucket_uri="gs://{}/sample_agent.blob".format(gcs_bucket)
    )

    time.sleep(4)
    res = ops.get_lro(lro)
    print(res)

    assert res["done"]


def test_get_agent(agents):
    """Tests the SCRAPI method get_agent from core/agents.py"""
    agent = agents.get_agent(pytest.temp_agent.name)

    assert isinstance(agent, types.Agent)
    assert pytest.temp_agent.display_name == AGENT_NAME

def test_get_agent_by_display_name(agents, project):
    """Test that we can retrieve agent by display name"""
    region = pytest.temp_agent.name.split("/")[3]
    agent = agents.get_agent_by_display_name(
        project_id=project,
        display_name=pytest.temp_agent.display_name,
        region=region
    )

    assert isinstance(agent, types.Agent)
    assert agent.display_name == AGENT_NAME

def test_get_agent_by_display_name_dupe(agents, project, caplog):
    """Test this function when providing a display name that is ambiguous and
    exists in multiple regions"""
    with caplog.at_level(logging.WARNING):
        agents.get_agent_by_display_name(
            project_id=project,
            display_name="SCRAPI - CI Duplicate")

    assert "Found multiple agents with the display name" in caplog.text

def test_get_agent_by_display_name_approx(agents, project, caplog):
    """test this function with approximate matching of agent name."""
    with caplog.at_level(logging.WARNING):
        agents.get_agent_by_display_name(
            project_id=project,
            display_name="sCRAPI - CI Duplicate"
        )

    assert "display_name is case-sensitive" in caplog.text

def test_export_agent(agents, ops, gcs_bucket):
    """Tests the SCRAPI method export_agent from core/agents.py"""
    lro = agents.export_agent(
        pytest.temp_agent.name,
        "gs://{}/testing_export.json".format(gcs_bucket),
    )

    time.sleep(4)

    assert ops.get_lro(lro)["done"]


def test_update_agent(agents):
    """Tests the SCRAPI method update_agent from core/agents.py"""
    temp_name = AGENT_NAME + "_UPDATED"
    res = agents.update_agent(
        pytest.temp_agent.name, display_name=temp_name
    )

    assert res.display_name == temp_name


def test_delete_agent(agents):
    """Tests the SCRAPI method delete_agent from core/agents.py"""
    res = agents.delete_agent(pytest.temp_agent.name)

    print(res)

    assert pytest.temp_agent.name in res

def test_list_agents(agents, project):
    """Tests the SCRAPI method list_agents from core/agents.py"""
    location_id = "projects/{}/locations/global".format(project)
    agents = agents.list_agents(location_id)

    assert isinstance(agents[0], types.agent.Agent)
