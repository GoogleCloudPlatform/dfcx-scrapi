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
import time
from datetime import datetime
# from typing import List, Dict

import pytest
import google.cloud.dialogflowcx_v3beta1.types as types
import sys

path_to_module = "/home/greenford/dfcx-scrapi/src/dfcx_scrapi/tools"
sys.path.append(path_to_module)
import search_util

class SearchUtilTest:

    DEV = True
    today_time = datetime.now().strftime("%d%m%Y_%H%M%S")
    AGENT_NAME = None
    CREDS_PATH = 'Edit me'
    AGENT_ID = 'Edit me'
    scrapi_search = None

    def test_instantiate_SearchUtil(self):
        self.scrapi_search = search_util.SearchUtil(creds_path=self.CREDS_PATH)

        assert isinstance(self.scrapi_search, search_util.SearchUtil)
        assert self.scrapi_search.creds_path == self.CREDS_PATH

    def test_get_agent_fulfillments(self):
        df = self.scrapi_search.get_agent_fulfillment_message_df(self.AGENT_ID)
        cols = set(df.columns)
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

if __name__ == "__main__":
    t = SearchUtilTest()
    t.test_instantiate_SearchUtil()
    t.test_get_agent_fulfillments()

