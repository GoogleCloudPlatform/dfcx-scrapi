"""Unit Tests for Search Util Class"""
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

import pytest
from src.dfcx_scrapi.tools import search_util

@pytest.mark.unit
def test_instantiate_search_util(creds):
    scrapi_search = search_util.SearchUtil(creds_path=creds)

    assert isinstance(scrapi_search, search_util.SearchUtil)
    assert scrapi_search.creds_path == creds

@pytest.mark.unit
def test_get_agent_fulfillments(creds, agent_id):
    scrapi_search = search_util.SearchUtil(creds_path=creds)
    df = scrapi_search.get_agent_fulfillment_message_df(agent_id)
    assert set(df.columns) == {
            'flow_name',
            'page_name',
            'parameter_name',
            'event',
            'route_group_name',
            'intent',
            'condition',
            'response_message',
            'conditional_cases',
            'response_type'}
