import pytest
import google.cloud.dialogflowcx_v3beta1.types as types
from typing import List, Dict
from dfcx.core.agents import Agents

class TestAgents:
    dev_creds = '/home/pmarlow/engineering/creds/nj-pods-dev.json'
    agents = Agents(dev_creds)

    def test_export_agent(self):
        pmarlow = 'projects/nj-pods-dev/locations/global/agents/cf592326-49ab-421a-bab8-9bbca4d396ba'
        lro = self.agents.export_agent(pmarlow, 'gs://pmarlow_dev_agents/testing_export.json')
        assert type(lro) is str

    def test_list_agents(self):
        location_id =  'projects/nj-pods-dev/locations/global'
        agents = self.agents.list_agents(location_id)
        assert isinstance(agents[0], types.Agent)


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