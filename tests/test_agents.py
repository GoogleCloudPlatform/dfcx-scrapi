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

import time
from datetime import datetime
# from typing import List, Dict

import pytest
import google.cloud.dialogflowcx_v3beta1.types as types
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.operations import Operations

DEV = True  # Set flag to disable some tests while in development

today_time = datetime.now().strftime("%d%m%Y_%H%M%S")
AGENT_NAME = "DFCX SCRAPI - TEMP TEST AGENT {}".format(today_time)
CREDS_PATH = None
PROJECT_ID = None


@pytest.fixture(name="cx_vars", scope="class")
def cx_vars_fixture():
    """Fixture method to setup shared vars across test runs."""
    class CxVars:
        """Class to hold shared vars across test runs."""
        def __init__(self, CREDS_PATH): # pylint: disable=W0621
            self.agents = Agents(CREDS_PATH)
            self.ops = Operations(CREDS_PATH)
            self.gcs_bucket_uri = "gs://dfcx_scrapi/api_test_agent.json"

    return CxVars(CREDS_PATH)


class TestAgents:
    """Main class to test all SCRAPI agent methods."""
    def test_create_agents(self, cx_vars):
        """Tests the SCRAPI method create_agent from core/agents.py"""
        if DEV:
            cx_vars.temp_agent = cx_vars.agents.create_agent(
                PROJECT_ID, AGENT_NAME
            )

            assert isinstance(cx_vars.temp_agent, types.Agent)
            assert cx_vars.temp_agent.display_name == AGENT_NAME

    def test_restore_agent(self, cx_vars):
        """Tests the SCRAPI method restore_agent from core/agents.py"""
        lro = cx_vars.agents.restore_agent(
            cx_vars.temp_agent.name, gcs_bucket_uri=cx_vars.gcs_bucket_uri
        )

        time.sleep(4)
        res = cx_vars.ops.get_lro(lro)
        print(res)

        assert res["done"]

    def test_get_agent(self, cx_vars):
        """Tests the SCRAPI method get_agent from core/agents.py"""
        agent = cx_vars.agents.get_agent(cx_vars.temp_agent.name)

        assert isinstance(agent, types.Agent)
        assert cx_vars.temp_agent.display_name == AGENT_NAME

    def test_export_agent(self, cx_vars):
        """Tests the SCRAPI method export_agent from core/agents.py"""
        lro = cx_vars.agents.export_agent(
            cx_vars.temp_agent.name,
            "{}/testing_export.json".format(cx_vars.gcs_bucket_uri),
        )

        time.sleep(4)

        assert cx_vars.ops.get_lro(lro)["done"]

    def test_update_agent(self, cx_vars):
        """Tests the SCRAPI method update_agent from core/agents.py"""
        temp_name = AGENT_NAME + "_UPDATED"
        res = cx_vars.agents.update_agent(
            cx_vars.temp_agent.name, display_name=temp_name
        )

        assert res.display_name == temp_name

    def test_delete_agent(self, cx_vars):
        """Tests the SCRAPI method delete_agent from core/agents.py"""
        res = cx_vars.agents.delete_agent(cx_vars.temp_agent.name)

        print(res)

        assert cx_vars.temp_agent.name in res

    def test_list_agents(self, cx_vars):
        """Tests the SCRAPI method list_agents from core/agents.py"""
        location_id = "projects/%s/locations/global", PROJECT_ID
        agents = cx_vars.agents.list_agents(location_id)

        assert isinstance(agents[0], types.Agent)
