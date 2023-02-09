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

import logging
import pytest
import time
from datetime import datetime

from google.cloud.dialogflowcx_v3beta1 import types
from src.dfcx_scrapi.core import agents
from src.dfcx_scrapi.core import operations

today_time = datetime.now().strftime("%d%m%Y_%H%M%S")
AGENT_NAME = f"DFCX SCRAPI - TEMP TEST AGENT {today_time}"

pytest.temp_agent = None

@pytest.mark.unit
def test_create_agent(creds, project_id):
    """Tests the SCRAPI method create_agent from core/agents.py"""
    a = agents.Agents(creds_path=creds)
    pytest.temp_agent = a.create_agent(
        project_id, AGENT_NAME
    )

    assert isinstance(pytest.temp_agent, types.Agent)
    assert pytest.temp_agent.display_name == AGENT_NAME

    return pytest.temp_agent

@pytest.mark.unit
def test_restore_agent(creds, gcs_bucket):
    """Tests the SCRAPI method restore_agent from core/agents.py"""
    a = agents.Agents(creds_path=creds)
    ops = operations.Operations(creds_path=creds)

    lro = a.restore_agent(
        pytest.temp_agent.name,
        gcs_bucket_uri=f"gs://{gcs_bucket}/sample_agent.blob"
    )

    time.sleep(4)
    res = ops.get_lro(lro)
    print(res)

    assert res["done"]

@pytest.mark.unit
def test_get_agent(creds):
    """Tests the SCRAPI method get_agent from core/agents.py"""
    a = agents.Agents(creds_path=creds)
    agent = a.get_agent(pytest.temp_agent.name)

    assert isinstance(agent, types.Agent)
    assert pytest.temp_agent.display_name == AGENT_NAME

@pytest.mark.unit
def test_get_agent_by_display_name(creds, project_id):
    """Test that we can retrieve agent by display name"""
    a = agents.Agents(creds_path=creds)
    region = pytest.temp_agent.name.split("/")[3]
    agent = a.get_agent_by_display_name(
        project_id=project_id,
        display_name=pytest.temp_agent.display_name,
        region=region
    )

    assert isinstance(agent, types.Agent)
    assert agent.display_name == AGENT_NAME

@pytest.mark.unit
def test_get_agent_by_display_name_dupe(creds, project_id, caplog):
    """Test this function when providing a display name that is ambiguous and
    exists in multiple regions"""
    a = agents.Agents(creds_path=creds)
    with caplog.at_level(logging.WARNING):
        a.get_agent_by_display_name(
            project_id=project_id,
            display_name="SCRAPI - CI Duplicate")

    assert "Found multiple agents with the display name" in caplog.text

@pytest.mark.unit
def test_get_agent_by_display_name_approx(creds, project_id, caplog):
    """test this function with approximate matching of agent name."""
    a = agents.Agents(creds_path=creds)
    with caplog.at_level(logging.WARNING):
        a.get_agent_by_display_name(
            project_id=project_id,
            display_name="sCRAPI - CI Duplicate"
        )

    assert "display_name is case-sensitive" in caplog.text

@pytest.mark.unit
def test_export_agent(creds, gcs_bucket):
    """Tests the SCRAPI method export_agent from core/agents.py"""
    a = agents.Agents(creds_path=creds)
    ops = operations.Operations(creds_path=creds)
    lro = a.export_agent(
        pytest.temp_agent.name,
        f"gs://{gcs_bucket}/testing_export.json"
    )

    time.sleep(4)

    assert ops.get_lro(lro)["done"]

@pytest.mark.unit
def test_update_agent(creds):
    """Tests the SCRAPI method update_agent from core/agents.py"""
    a = agents.Agents(creds_path=creds)
    temp_name = AGENT_NAME + "_UPDATED"
    res = a.update_agent(
        pytest.temp_agent.name, display_name=temp_name
    )

    assert res.display_name == temp_name

@pytest.mark.unit
def test_delete_agent(creds):
    """Tests the SCRAPI method delete_agent from core/agents.py"""
    a = agents.Agents(creds_path=creds)
    res = a.delete_agent(pytest.temp_agent.name)

    print(res)

    assert pytest.temp_agent.name in res

@pytest.mark.unit
def test_list_agents(creds, project_id):
    """Tests the SCRAPI method list_agents from core/agents.py"""
    a = agents.Agents(creds_path=creds)
    location_id = f"projects/{project_id}/locations/global"
    all_agents = a.list_agents(location_id)

    assert isinstance(all_agents[0], types.agent.Agent)
