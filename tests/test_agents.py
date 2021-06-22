"""
Copyright 2021 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import pytest
import time
import google.cloud.dialogflowcx_v3beta1.types as types
from dfcx_sapi.core.agents import Agents
from dfcx_sapi.core.operations import Operations
from datetime import datetime
from typing import List, Dict

# TODO Create SA for Gitlab CICD and configure as ENV VAR

DEV = True # Set flag to disable some tests while in development

today_time = datetime.now().strftime("%d%m%Y_%H%M%S")
AGENT_NAME = 'DFCX SAPI - TEMP TEST AGENT {}'.format(today_time)
CREDS_PATH = None

@pytest.fixture(name='cx_vars', scope='class')
def cx_vars_fixture():

    class CxVars:
        def __init__(self, CREDS_PATH):
            self.agents = Agents(CREDS_PATH)
            self.ops = Operations(CREDS_PATH)
            self.gcs_bucket_uri = 'gs://dfcx_scrapi/api_test_agent.json'

    return CxVars(CREDS_PATH)

class TestAgents:
    def test_create_agents(self, cx_vars):
        if DEV:
            cx_vars.temp_agent = cx_vars.agents.create_agent('nj-pods-dev',AGENT_NAME)

            assert isinstance(cx_vars.temp_agent, types.Agent)
            assert cx_vars.temp_agent.display_name == AGENT_NAME

    def test_restore_agent(self, cx_vars):
        lro = cx_vars.agents.restore_agent(
            cx_vars.temp_agent.name, gcs_bucket_uri=cx_vars.gcs_bucket_uri)

        time.sleep(4)
        res = cx_vars.ops.get_lro(lro)
        print(res)

        assert res['done']

    def test_get_agent(self, cx_vars):
        agent = cx_vars.agents.get_agent(cx_vars.temp_agent.name)

        assert isinstance(agent, types.Agent)
        assert cx_vars.temp_agent.display_name == AGENT_NAME

    def test_export_agent(self, cx_vars):
        lro = cx_vars.agents.export_agent(
            cx_vars.temp_agent.name, '{}/testing_export.json'.format(
                cx_vars.gcs_bucket_uri))

        time.sleep(4)

        assert cx_vars.ops.get_lro(lro)['done']

    def test_update_agent(self, cx_vars):
        temp_name = AGENT_NAME + '_UPDATED'
        res = cx_vars.agents.update_agent(
            cx_vars.temp_agent.name, display_name=temp_name)
        
        assert res.display_name == temp_name

    def test_delete_agent(self, cx_vars):
        res = cx_vars.agents.delete_agent(
            cx_vars.temp_agent.name)

        print(res)

        assert cx_vars.temp_agent.name in res

    def test_list_agents(self, cx_vars):
        location_id =  'projects/nj-pods-dev/locations/global'
        agents = cx_vars.agents.list_agents(location_id)

        assert isinstance(agents[0], types.Agent)

    # TODO
    # def test_validate

    # def test_get_validation_result