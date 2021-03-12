import pytest
import google.cloud.dialogflowcx_v3beta1.types as types
from datetime import datetime
from typing import List, Dict
from dfcx.core.agents import Agents
from dfcx.core.operations import Operations

# TODO (pmarlow@) Create SA for Gitlab CICD and configure as ENV VAR
CREDS_PATH = '/home/pmarlow/engineering/creds/nj-pods-dev.json'
DEV = True # Set flag to disable some tests while in development

today_time = datetime.now().strftime("%d%m%Y_%H%M%S")
AGENT_NAME = 'DFCX SAPI - TEMP TEST AGENT {}'.format(today_time)

class TestAgents:
    def __init__(self, CREDS_PATH):
        self.agents = Agents(CREDS_PATH)
        self.ops = Operations(CREDS_PATH)
        self.gcs_bucket_uri = 'gs://dfcx_scrapi/api_test_agent.json'

    def test_create_agents(self):
        if DEV:
            self.temp_agent = self.agents.create_agent('nj-pods-dev',AGENT_NAME)

            assert isinstance(self.temp_agent, types.Agent)
            assert self.temp_agent.display_name == AGENT_NAME

    def test_restore_agent(self):
        lro = self.agents.restore_agent(
            self.temp_agent.name, gcs_bucket_uri=self.gcs_bucket_uri)

        assert self.ops.get_lro(lro)['done']

    def test_get_agent(self):
        agent = self.agents.get_agent(self.temp_agent)

        assert isinstance(agent, types.Agent)
        assert self.temp_agent.display_name == AGENT_NAME

    def test_export_agent(self):
        lro = self.agents.export_agent(
            self.temp_agent, '{}/testing_export.json'.format(
                self.gcs_bucket_uri))

        assert self.ops.get_lro(lro)['done']

    def test_update_agent(self):
        temp_name = AGENT_NAME + '_UPDATED'
        res = self.agents.update_agent(
            self.temp_agent.name, display_name=temp_name)
        
        assert res.display_name == temp_name

    

    def test_list_agents(self):
        location_id =  'projects/nj-pods-dev/locations/global'
        agents = self.agents.list_agents(location_id)

        assert isinstance(agents[0], types.Agent)

    # TODO (pmarlow@)
    # def test_validate

    # def test_get_validation_result




# What do we really care about right now for testing?
# Maybe not check for content, but check for length
# should this export 10 intents? Are we getting 10 intents back?
# make sure we don't touch the agent

# order of operations for test
# - resetting agents to a known state

# Check out BEFORE ALL in pytest
# utility functions like "agent reset"

# spin up new agent
# run all tests
# tear down agent
# report results

# Put this in Gitlab and run it on a commit hook (pre/post?)
# setup CICD in Gitlab

# creds.EXAMPLE ?
# rename file
# gitlab SA for automated testing?