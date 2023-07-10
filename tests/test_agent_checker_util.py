"""Unit Tests for Agent Checker Util Class"""
# Copyright 2022 Google LLC
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
import pandas as pd
from src.dfcx_scrapi.tools import agent_checker_util

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Note: Each instantiation of the AgentCheckerUtil class with a particular
# agent ID will make 2*num_flows + 2 API calls. Recommended to test in an
# agent which contains only two small flows.

@pytest.mark.unit
def test_instantiate_agent_checker_util(creds, agent_id):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    assert isinstance(scrapi_checker, agent_checker_util.AgentCheckerUtil)
    assert scrapi_checker.creds_path == creds

@pytest.mark.unit
def test_find_all_reachable_pages(creds, agent_id):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    df = scrapi_checker.find_all_reachable_pages()
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {
        "flow_name",
        "page_name"}
    logging.info("All reachable pages:\n%s", df.to_string())

@pytest.mark.unit
def test_find_all_unreachable_pages(creds, agent_id):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    df = scrapi_checker.find_all_unreachable_pages()
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {
        "flow_name",
        "page_name"}
    logging.info("All unreachable pages:\n%s", df.to_string())

@pytest.mark.unit
def test_find_all_reachable_intents(creds, agent_id):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    df = scrapi_checker.find_all_reachable_intents()
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {
        "intent",
        "flows"}
    logging.info("All reachable intents:\n%s", df.to_string())

@pytest.mark.unit
def test_find_all_unreachable_intents(creds, agent_id):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    intents = scrapi_checker.find_all_unreachable_intents()
    assert isinstance(intents, list)
    logging.info(f"All unreachable intents: {str(intents)}")

@pytest.mark.unit
def test_find_reachable_intents(creds, agent_id, flow_name):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    intents = scrapi_checker.find_reachable_intents(flow_name)
    assert isinstance(intents, list)
    logging.info(f"Reachable intents for flow {flow_name}: {str(intents)}")

@pytest.mark.unit
def test_find_reachable_pages(creds, agent_id, flow_name, page_name):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    page_names = scrapi_checker.find_reachable_pages(flow_name=flow_name,
                                                     from_page=page_name,
                                                     intent_route_limit=None)
    assert isinstance(page_names, list)
    logging.info(f"Reachable pages for flow {flow_name} starting from \
        {page_name}: {str(page_names)}")

@pytest.mark.unit
def test_find_one_turn_reachable_pages(creds, agent_id, flow_name, page_name):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    page_names = scrapi_checker.find_reachable_pages(flow_name=flow_name,
                                                     from_page=page_name,
                                                     intent_route_limit=1)
    assert isinstance(page_names, list)
    logging.info(f"Reachable pages for flow {flow_name} starting from \
        {page_name} in one turn: {str(page_names)}")

@pytest.mark.unit
def test_find_unreachable_pages(creds, agent_id, flow_name):
    scrapi_checker = agent_checker_util.AgentCheckerUtil(creds_path=creds,
                                                         agent_id=agent_id)
    page_names = scrapi_checker.find_unreachable_pages(flow_name=flow_name)
    assert isinstance(page_names, list)
    logging.info(f"Unreachable pages for flow {flow_name}: {str(page_names)}")
