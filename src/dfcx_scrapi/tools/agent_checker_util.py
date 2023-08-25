"""A set of Utility methods to check resources stats on DFCX Agents."""

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

from __future__ import annotations

import logging
from typing import Dict, List
import pandas as pd

from google.cloud.dialogflowcx_v3beta1 import types
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.agent_extract import agents

# Type aliases
DFCXFlow = types.flow.Flow
DFCXPage = types.page.Page
DFCXRoute = types.page.TransitionRoute

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class AgentCheckerUtil(scrapi_base.ScrapiBase):
    """Utility class for checking DFCX Agents."""

    def __init__(
        self,
        agent_id: str,
        gcs_bucket_uri: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id
        self.extract = agents.Agents(agent_id)
        self.data = self.extract.process_agent(agent_id, gcs_bucket_uri)
        self.special_pages = [
            "End Session",
            "End Flow",
            "Start Page",
            "Current Page",
            "Previous Page",
        ]
        self.active_intents_df = pd.DataFrame()

    # def find_reachable_pages(
    #     self,
    #     flow_name: str,
    #     from_page: str = "Start",
    #     intent_route_limit: Optional[int] = None,
    #     include_groups: bool = True,
    #     include_start_page_routes: bool = True,
    #     include_meta: bool = False,
    #     verbose: bool = False,
    # ) -> List[str]:
    #     """Finds all pages which are reachable by transition routes,
    #     starting from a given page in a given flow. Either flow_id or
    #     flow_name must be used.

    #     Args:
    #       flow_name: The display name of the flow.
    #       from_page: (Optional) The page to start from. If left blank, it will
    #         start on the Start Page of the given flow.
    #       intent_route_limit: (Optional) Default None. The maximum number of
    #         intent routes to take. This can be used to answer questions like
    #         "which pages can I reach within N turns, starting at this page?"
    #       include_groups: (Optional) If true, intents from transition route
    #         groups will be included, but only if they are actually referenced
    #         on each given page in the traversal.
    #       include_start_page_routes: (Optional) Default true. If true, intent
    #         routes on the start page are always considered in scope. This is
    #         how DFCX normally behaves.
    #       include_meta: (Optional) Default False. If true, includes special
    #         transition targets like End Session, End Flow, etc. as if they
    #         are actual pages.
    #       verbose: (Optional) If true, prints debug information about
    #         route traversal.

    #     Returns:
    #       The list of reachable pages in this flow
    #     """
    #     flow_id = self._flows_map_rev.get(flow_name, None)
    #     if not flow_id:
    #         raise KeyError(f"Flow not found: {flow_name}")

    #     # Start at the start page...
    #     reachable = [from_page]
    #     conversation_path = [from_page]
    #     # Technically this could be [0] or [1], or very rarely more than 1,
    #     # depending on the routes that lead to current page...
    #     min_intent_counts = [25]
    #     presets = {}
    #     page_data = self._get_page(
    #         flow_name=flow_name,
    #         page_name=from_page
    #     )
    #     params = {
    #         "flow_id": flow_id,
    #         "flow_name": flow_name,
    #         "reachable": reachable,
    #         "conversation_path": conversation_path,
    #         "min_intent_counts": min_intent_counts,
    #         "presets": presets,
    #         "intent_route_limit": intent_route_limit,
    #         "intent_route_count": 0,
    #         "include_groups": include_groups,
    #         "include_start_page_routes": include_start_page_routes,
    #         "limit_intent_to_initial": False,
    #         # This can't be stored here unless I want to add a lot of complex
    #         # conditions to change it to False and back depending on the level
    #         # of recursion
    #         #"is_initial": True,
    #         "include_meta": include_meta,
    #         "verbose": verbose
    #     }
    #     self._find_reachable_pages_rec(page_data, params, is_initial=True)
    #     return reachable

    def active_intents_to_dataframe(self) -> pd.DataFrame:
        """Gets all intents referenced in the agent, across all flows,
        and produces a dataframe listing which flows reference each intent.

        Returns:
            A dataframe with columns
            intent - the intent display name
            flows - a list of flow display names that use this intent
        """
        df = pd.DataFrame({"intent": [], "flow": []})
        for flow in self.data.active_intents:
            for intent in self.data.active_intents[flow]:
                temp = pd.DataFrame({"intent": [intent], "flow": [flow]})
                df = pd.concat([df, temp])

        self.active_intents_df = df.reset_index(drop=True)

        return self.active_intents_df

    def get_unused_intents(self) -> List:
        """Get all unused Intents across the agent."""
        if self.active_intents_df.empty:
            self.active_intents_df = self.active_intents_to_dataframe()
        active_intents_set = set(self.active_intents_df.intent.to_list())
        all_intents_set = set(self.data.intents_map.keys())

        return list(all_intents_set.difference(active_intents_set))

    def get_unreachable_intents(self) -> List:
        """Get all unreachable Intents across the agent.

        An Intent is unreachable if it resides on a page that is also
        unreachable.
        """
        # Get Page / Intent mapping
        # Find all unreachable pages
        #
